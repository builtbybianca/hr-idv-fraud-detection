# Architecture & Design Decisions

This document explains *why* the IDV fraud-detection pipeline is built the way it is.
The code shows what it does; this shows the thinking behind it — the tradeoffs weighed,
the alternatives rejected, and where the system goes next. It's written the way I'd hand
a design off to a colleague or defend it in a review.

## Context

HR onboarding in a remote-first company receives identity documents digitally. Between
"document received" and "document accepted," most HR teams have no technical screening
layer at all — acceptance rests on a human glancing at an image. Meanwhile, convincing
document manipulation has gotten cheap and fast.

The goal was a first-pass triage layer: cheap, fast, explainable, and safe enough that
Legal and the DPO would sign off on running it against real onboarding documents.

## The decision: EXIF metadata heuristics as a triage layer

The pipeline extracts EXIF metadata from each submitted image and runs a small set of
transparent heuristic checks (editing-software traces, timestamp inconsistencies,
stripped-metadata patterns). Each check that fires raises a risk score and writes a
plain-language flag. Flagged documents route to human review.

This was chosen deliberately over more sophisticated approaches, for reasons below.

## Alternatives considered

**A machine-learning image-forensics classifier.**
Stronger in theory — a trained model can catch manipulation that leaves no metadata
trace. Rejected for v1 because: (a) it needs a labelled training set of genuine vs.
manipulated identity documents, which we could not assemble without collecting and
storing exactly the sensitive data we wanted to avoid holding; (b) a model's output is
hard to explain to a reviewer or a regulator, which conflicts with the "explainable
flags" requirement; (c) it's far more effort to ship and maintain than the problem
justified for a first triage layer. It belongs on the roadmap, not in v1.

**A commercial IDV vendor (Onfido, Jumio, Persona, etc.).**
The right answer at scale, and genuinely better than anything built in-house. Rejected
for v1 as a build-vs-buy timing call: procurement, security review, and budget for a
vendor is a multi-month process, and the point of this project was to prove the problem
was real and worth solving *before* asking for that spend. This pipeline is the evidence
that justifies the vendor conversation, not a permanent replacement for it.

**OCR + content cross-checking.**
Reads the document's actual contents to check internal consistency. Rejected on privacy
grounds: it requires processing the personal information printed on the document, which
dramatically raises the data-protection stakes. The metadata approach reads the
*envelope*, not the *contents* — a deliberate privacy-preserving choice.

## Why metadata heuristics, knowing their weakness

I want to be direct about the main limitation, because any reviewer will already know it:
**EXIF metadata is trivially spoofable and routinely stripped for legitimate reasons.**
A motivated bad actor can forge clean metadata, and an honest applicant who screenshots
or exports a photo will trip the "stripped metadata" check with nothing wrong.

That's exactly why the system is designed as a *triage layer that produces signals, not
verdicts*. It never rejects a document or a person. It raises a flag and a reason for a
human to look closer. Under that framing the weakness is acceptable: a cheap check that
catches the careless and the casual, surfaces a reason every time, and adds a screening
step where there was none — while never being trusted as proof of anything on its own.
Designing to the limitation honestly is the point, not designing around it.

## Key design principles, and what enforces them

| Principle | How it's enforced in the design |
|-----------|--------------------------------|
| Signals, not verdicts | No code path rejects a document; output is always a flag + reason routed to a human |
| Privacy-first | Reads metadata only; never OCRs or stores document contents; images stay on the operator's machine (gitignored) |
| Explainable | Every flag names the check that fired and what it found, so a reviewer evaluates the signal rather than trusting a score |
| Transparent scoring | Risk score is a simple, inspectable function of how many checks fired — no opaque weighting |

## Limitations (stated plainly)

- Evadable by anyone who forges or sanitizes metadata before submitting.
- False positives on legitimate screenshots, exports, and privacy-stripped images.
- Catches manipulation that touches metadata; blind to pixel-level edits that don't.
- Heuristics are hand-tuned, not learned, so they don't adapt to new manipulation patterns.

## Roadmap — where this goes next

1. **Audit logging.** Record every flag and the human's resolution. This both creates a
   defensible paper trail and becomes the labelled dataset a future ML layer would need.
2. **Error-Level Analysis (ELA).** Add a pixel-level check for inconsistent compression
   artifacts — catches a class of edits metadata misses, still explainable.
3. **ML forensics layer.** Once enough labelled resolutions exist, add a trained
   classifier *as an additional signal*, never as an auto-reject — keeping the
   human-in-the-loop and explainability constraints intact.
4. **Vendor integration path.** Document the interface so a commercial IDV provider can
   slot in behind the same human-review queue when scale justifies the spend.

## What I'd tell a reviewer in one line

This isn't trying to be a fraud oracle. It's a cheap, honest, explainable first filter
that adds a screening step where HR had none — designed from the start to be safe enough
to run against real documents and to grow into something stronger without ever removing
the human from the decision.
