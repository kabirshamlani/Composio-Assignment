"""Stage 8 prep: reproducible stratified + risk-targeted audit sample.

Selection = (all apps with risk_score >= HIGH_RISK)
          + (2 seeded-random apps per category)
          + (all apps that failed the deterministic evidence-policy check).
Seed is recorded so the sample is reproducible.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "data" / "exports"

SEED = 20260817
HIGH_RISK = 5
PER_CATEGORY = 2


def main() -> int:
    apps = json.loads((EXPORTS / "apps.first_pass.json").read_text())
    evidence_gap_ids = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else []

    selected: dict[int, list[str]] = {}

    def add(app_id: int, reason: str) -> None:
        selected.setdefault(app_id, []).append(reason)

    for a in apps:
        if a["risk_score"] >= HIGH_RISK:
            add(a["app_id"], f"high_risk(score={a['risk_score']})")
    for app_id in evidence_gap_ids:
        add(app_id, "evidence_policy_gap")

    # Per-category RNG keyed on (seed, category) so each category's draw is
    # independent and reproducible regardless of how other categories change.
    by_cat: dict[str, list[dict]] = {}
    for a in apps:
        by_cat.setdefault(a["category"], []).append(a)
    for cat in sorted(by_cat):
        rng = random.Random(f"{SEED}:{cat}")
        pool = sorted(by_cat[cat], key=lambda x: x["app_id"])
        for a in rng.sample(pool, min(PER_CATEGORY, len(pool))):
            add(a["app_id"], f"stratified_random({cat})")

    sample = {
        "seed": SEED,
        "high_risk_threshold": HIGH_RISK,
        "per_category": PER_CATEGORY,
        "selected": [{"app_id": i, "name": next(a["name"] for a in apps if a["app_id"] == i),
                      "reasons": r} for i, r in sorted(selected.items())],
        "sample_size": len(selected),
        "population": len(apps),
    }
    (EXPORTS / "audit_sample.json").write_text(json.dumps(sample, indent=2))
    print(f"sample: {len(selected)}/{len(apps)} apps")
    for row in sample["selected"]:
        print(f"  {row['app_id']:>3} {row['name']:<28} {'; '.join(row['reasons'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
