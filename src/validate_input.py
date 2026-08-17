"""Stage 0: validate the input app list and write the input manifest.

Checks count, ID continuity, name uniqueness, and records the input file's
SHA-256 so every downstream artifact is traceable to an exact input. If rows
were ever missing, the validator reports the gap instead of letting anything
downstream invent them.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
APPS = ROOT / "data" / "apps.yaml"
MANIFEST = ROOT / "data" / "input_manifest.json"


def main() -> int:
    raw = APPS.read_bytes()
    doc = yaml.safe_load(raw)
    apps = doc["apps"]
    expected = doc["expected_count"]

    ids = [a["id"] for a in apps]
    names = [a["name"].strip().lower() for a in apps]
    errors: list[str] = []
    if len(set(ids)) != len(ids):
        errors.append("duplicate app IDs")
    if ids != list(range(1, len(ids) + 1)):
        errors.append("IDs are not continuous from 1")
    if len(set(names)) != len(names):
        errors.append("duplicate app names")

    missing = list(range(len(ids) + 1, expected + 1))
    manifest = {
        "source": "DOCS/AI Product Ops Intern - The take-home assignment.md (verbatim transcription)",
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "expected_count": expected,
        "actual_count": len(ids),
        "missing_ids": missing,
        "status": "INPUT_INCOMPLETE" if missing else "OK",
        "policy": "missing IDs are never invented; any gap is reported, not reconstructed",
        "structural_errors": errors,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    if errors:
        return 2
    if missing:
        print(f"\nWARNING: input lists {len(ids)} apps but claims {expected}. "
              f"Proceeding with the {len(ids)} listed apps; gaps are reported, not filled.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
