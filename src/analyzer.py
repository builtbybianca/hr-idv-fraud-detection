"""
HR IDV Fraud Detection - EXIF Metadata Analyzer
Flags identity document images showing signals of digital manipulation.

Signals, not verdicts: output is a human-review flag report, never a rejection.
Reads metadata only -- never the document's contents -- a deliberate
privacy-preserving choice.

Usage:
    python src/analyzer.py
"""

from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS

# Metadata fingerprints commonly left by editing software
EDITOR_SIGNATURES = [
    "photoshop", "gimp", "canva", "pixlr", "affinity",
    "lightroom", "snapseed", "facetune", "picsart",
]

# EXIF fields a genuine camera/phone capture normally includes
EXPECTED_CAMERA_FIELDS = {"Make", "Model", "DateTimeOriginal"}


def extract_exif(image_path: Path) -> dict:
    """Pull EXIF metadata from an image into a readable dict."""
    exif_data = {}
    with Image.open(image_path) as img:
        raw = img.getexif()
        for tag_id, value in raw.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            exif_data[tag_name] = str(value)
    return exif_data


def check_editor_traces(exif: dict) -> list[str]:
    """Flag if metadata names known editing software."""
    flags = []
    software = exif.get("Software", "").lower()
    for sig in EDITOR_SIGNATURES:
        if sig in software:
            flags.append(
                f"EDITOR TRACE: 'Software' field names editing tool ({exif['Software']})"
            )
    return flags


def check_timestamps(exif: dict) -> list[str]:
    """Flag timestamp patterns inconsistent with a single genuine capture."""
    flags = []
    original = exif.get("DateTimeOriginal")
    modified = exif.get("DateTime")
    if original and modified and original != modified:
        flags.append(
            f"TIMESTAMP MISMATCH: capture time ({original}) differs from "
            f"modification time ({modified}) - image altered after capture"
        )
    return flags


def check_missing_metadata(exif: dict) -> list[str]:
    """Flag stripped EXIF where camera data would be expected."""
    missing = EXPECTED_CAMERA_FIELDS - set(exif.keys())
    if missing == EXPECTED_CAMERA_FIELDS:
        return [
            "STRIPPED METADATA: no camera fields present - "
            "consistent with screenshot, export, or deliberate metadata removal"
        ]
    return []


def analyze_document(image_path: Path) -> dict:
    """Run all checks on one document and return a flag report."""
    exif = extract_exif(image_path)
    flags = (
        check_editor_traces(exif)
        + check_timestamps(exif)
        + check_missing_metadata(exif)
    )
    # Simple transparent scoring: each flag adds risk; capped at 100
    risk_score = min(len(flags) * 35, 100)
    return {
        "document": image_path.name,
        "risk_score": risk_score,
        "flags": flags,
        "recommendation": "HUMAN REVIEW" if flags else "No metadata flags",
    }


def main():
    docs_dir = Path("data/documents")
    if not docs_dir.exists():
        print("Setup needed: create data/documents/ and add test images.")
        return

    print(f"IDV Metadata Analysis - {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 60)

    for image_path in sorted(docs_dir.iterdir()):
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        report = analyze_document(image_path)
        print(f"\nDocument: {report['document']}")
        print(f"Risk score: {report['risk_score']}/100")
        for flag in report["flags"]:
            print(f"  - {flag}")
        print(f"Recommendation: {report['recommendation']}")

    print("\n" + "=" * 60)
    print("Reminder: flags are signals for human review, never verdicts.")


if __name__ == "__main__":
    main()
