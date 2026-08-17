"""Stage 5: deterministic validation of research-agent output.

Checks every per-app JSON in data/first_pass/apps/ against the schema and the
evidence policy, derives final_bucket + risk, and writes a combined
data/exports/apps.first_pass.json plus a verification queue.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from risk import VERIFY_THRESHOLD, final_bucket, risk_assessment
from schemas import AppResult

ROOT = Path(__file__).resolve().parent.parent
APPS_DIR = ROOT / "data" / "first_pass" / "apps"
EXPORTS = ROOT / "data" / "exports"

CORE_CLAIM_FIELDS = ["auth", "access", "api", "mcp"]


def validate_one(path: Path, expected: dict) -> tuple[AppResult | None, list[str]]:
    problems: list[str] = []
    try:
        r = AppResult.model_validate_json(path.read_text())
    except ValidationError as e:
        return None, [f"schema violation: {e}"]

    if r.app_id != expected["id"] or r.name != expected["name"]:
        problems.append(f"identity mismatch: expected {expected['id']}/{expected['name']}")
    if r.category != expected["category"]:
        problems.append(f"category mismatch: {r.category!r}")

    # Evidence policy: every core non-unknown claim area needs >=1 evidence URL.
    covered = {c for ev in r.evidence for c in ev.claims}
    for field in CORE_CLAIM_FIELDS:
        value_is_unknown = (
            (field == "auth" and r.primary_auth == "unknown")
            or (field == "access" and r.access == "unknown")
            or (field == "api" and r.api_breadth == "unknown")
            or (field == "mcp" and r.mcp_status == ["unknown"])
        )
        if not value_is_unknown and field not in covered:
            problems.append(f"non-unknown claim '{field}' has no evidence URL")

    for ev in r.evidence:
        if not ev.url.startswith("http"):
            problems.append(f"bad evidence URL: {ev.url}")

    return r, problems


def main() -> int:
    apps_index = {a["id"]: a for a in yaml.safe_load((ROOT / "data" / "apps.yaml").read_text())["apps"]}
    results, all_problems, queue = [], {}, []

    missing = [i for i in apps_index if not (APPS_DIR / f"{i:03d}.json").exists()]
    for path in sorted(APPS_DIR.glob("*.json")):
        expected = apps_index.get(int(path.stem))
        if expected is None:
            all_problems[path.name] = ["file does not match any input app id"]
            continue
        r, problems = validate_one(path, expected)
        if problems:
            all_problems[path.name] = problems
        if r is None:
            continue
        r.final_bucket = final_bucket(r)
        r.risk_score, r.risk_flags = risk_assessment(r)
        if r.risk_score >= VERIFY_THRESHOLD:
            queue.append({"app_id": r.app_id, "name": r.name,
                          "risk_score": r.risk_score, "flags": r.risk_flags})
        results.append(r)

    EXPORTS.mkdir(parents=True, exist_ok=True)
    (EXPORTS / "apps.first_pass.json").write_text(
        json.dumps([r.model_dump(mode="json") for r in sorted(results, key=lambda x: x.app_id)], indent=1))
    (EXPORTS / "verification_queue.json").write_text(json.dumps(
        sorted(queue, key=lambda q: -q["risk_score"]), indent=2))

    print(f"validated: {len(results)}/{len(apps_index)} apps")
    print(f"missing files: {missing or 'none'}")
    print(f"verification queue (risk >= {VERIFY_THRESHOLD}): {len(queue)} apps")
    if all_problems:
        print(f"\nPROBLEMS ({len(all_problems)} files):")
        for name, probs in sorted(all_problems.items()):
            for p in probs:
                print(f"  {name}: {p[:300]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
