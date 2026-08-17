"""Stage 9: deterministic metrics and clusters.

Every number shown on the HTML page comes from this file's output
(data/exports/metrics.json). No model computes or restates counts.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "data" / "exports"

SELF_SERVE = {"self_serve_free", "self_serve_trial", "self_serve_paid", "no_credentials_required"}
GATED = {"sandbox_self_serve_production_gated", "admin_gated", "enterprise_gated",
         "production_approval", "partner_gated", "contact_sales", "invite_only"}


def compute(apps: list[dict]) -> dict:
    n = len(apps)
    by_cat = defaultdict(list)
    for a in apps:
        by_cat[a["category"]].append(a)

    def dist(key, items=None):
        return dict(Counter(a[key] for a in (items if items is not None else apps)).most_common())

    all_auth = Counter(m for a in apps for m in a["auth_methods"])
    mcp = Counter(m for a in apps for m in a["mcp_status"])
    blockers = Counter(a["primary_blocker"] for a in apps if a.get("primary_blocker"))

    category_bucket = {c: dict(Counter(a["final_bucket"] for a in items))
                       for c, items in sorted(by_cat.items())}
    category_access = {}
    for c, items in sorted(by_cat.items()):
        ss = sum(1 for a in items if a["access"] in SELF_SERVE)
        g = sum(1 for a in items if a["access"] in GATED)
        category_access[c] = {"self_serve": ss, "gated": g,
                              "unknown": len(items) - ss - g, "total": len(items)}

    clusters = {
        "build_now": sorted(a["app_id"] for a in apps
                            if a["final_bucket"] == "READY — SELF-SERVE"),
        "outreach_needed": sorted(a["app_id"] for a in apps
                                  if a["final_bucket"] == "READY — GATED"),
        "partial": sorted(a["app_id"] for a in apps if a["final_bucket"] == "PARTIAL"),
        "investigate": sorted(a["app_id"] for a in apps
                              if a["final_bucket"] in ("NOT BUILDABLE", "UNKNOWN", "READY — ACCESS UNKNOWN")),
    }

    oauth_apps = sum(1 for a in apps
                     if any(m.startswith("oauth2") for m in a["auth_methods"]))
    key_apps = sum(1 for a in apps
                   if any(m in ("api_key", "personal_access_token", "bearer_token")
                          for m in a["auth_methods"]))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_apps": n,
        "expected_apps": 100,
        "final_bucket": dist("final_bucket"),
        "primary_auth": dist("primary_auth"),
        "all_auth_methods": dict(all_auth.most_common()),
        "apps_supporting_any_oauth2": oauth_apps,
        "apps_supporting_key_or_token": key_apps,
        "access": dist("access"),
        "access_grouped": {
            "self_serve": sum(1 for a in apps if a["access"] in SELF_SERVE),
            "gated": sum(1 for a in apps if a["access"] in GATED),
            "unknown": sum(1 for a in apps if a["access"] not in SELF_SERVE | GATED),
        },
        "api_breadth": dist("api_breadth"),
        "technical_verdict": dist("technical_verdict"),
        "mcp_status": dict(mcp.most_common()),
        "confidence": dist("confidence"),
        "blockers": dict(blockers.most_common()),
        "webhooks": {"yes": sum(1 for a in apps if a.get("supports_webhooks") is True),
                     "no": sum(1 for a in apps if a.get("supports_webhooks") is False),
                     "unknown": sum(1 for a in apps if a.get("supports_webhooks") is None)},
        "category_bucket": category_bucket,
        "category_access": category_access,
        "clusters": clusters,
        "cluster_sizes": {k: len(v) for k, v in clusters.items()},
        "verification": {
            "verified_rows": sum(1 for a in apps if a["verification_status"] != "first_pass"),
            "corrected_rows": sum(1 for a in apps if a["verification_status"] == "corrected"),
        },
    }


def main() -> int:
    src = EXPORTS / "apps.final.json"
    if not src.exists():
        src = EXPORTS / "apps.first_pass.json"
    apps = json.loads(src.read_text())
    metrics = compute(apps)
    metrics["source_file"] = src.name
    (EXPORTS / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"metrics computed from {src.name} over {metrics['total_apps']} apps")
    print(json.dumps(metrics["final_bucket"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
