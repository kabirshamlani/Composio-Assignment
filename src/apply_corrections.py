"""Stage 7/8: apply verifier corrections and build the final dataset.

Reads data/verification/*.json, applies CONTRADICTED-field corrections to the
first-pass rows (recording every change in data/exports/corrections.jsonl),
recomputes buckets, and writes data/exports/apps.final.json.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from risk import final_bucket, risk_assessment
from schemas import AppResult

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "data" / "exports"
VERIF = ROOT / "data" / "verification"

CORRECTABLE = {"primary_auth", "auth_methods", "access", "api_breadth",
               "api_protocols", "mcp_status", "technical_verdict", "primary_blocker"}


def main() -> int:
    apps = {a["app_id"]: a for a in json.loads((EXPORTS / "apps.first_pass.json").read_text())}
    ledger, stats = [], {"verified": 0, "corrected": 0, "inconclusive": 0,
                         "fields_reviewed": 0, "fields_supported": 0,
                         "fields_contradicted": 0, "fields_partial": 0, "fields_other": 0}

    for path in sorted(VERIF.glob("*.json")):
        rec = json.loads(path.read_text())
        app = apps.get(rec["app_id"])
        if app is None:
            print(f"WARN: verification for unknown app {rec['app_id']}", file=sys.stderr)
            continue
        stats[rec["overall"]] = stats.get(rec["overall"], 0) + 1
        app["verification_status"] = "verified"
        for fr in rec["field_reviews"]:
            stats["fields_reviewed"] += 1
            v = fr["verdict"]
            if v == "SUPPORTED":
                stats["fields_supported"] += 1
            elif v == "CONTRADICTED":
                stats["fields_contradicted"] += 1
            elif v == "PARTIALLY_SUPPORTED":
                stats["fields_partial"] += 1
            else:
                stats["fields_other"] += 1
            if v == "PARTIALLY_SUPPORTED" and fr.get("replacement_evidence"):
                # Value was right but under-evidenced or note-level imprecise:
                # attach the verifier's URL (and its clarification via the note).
                app["evidence"].append({
                    "claims": [fr["field"].split("_")[0] if fr["field"] != "technical_verdict" else "verdict"],
                    "url": fr["replacement_evidence"],
                    "note": f"verifier-supplied evidence: {fr['reason'][:200]}",
                })
            # primary_blocker is nullable, so a correction TO null is legitimate
            # (e.g. a blocker removed because the vendor shipped a public API).
            has_correction = (fr.get("corrected_value") is not None
                              or (fr["field"] == "primary_blocker" and "corrected_value" in fr))
            if v == "CONTRADICTED" and has_correction:
                field = fr["field"]
                if field not in CORRECTABLE:
                    continue
                if not fr.get("replacement_evidence"):
                    print(f"REJECTED correction without evidence: app {rec['app_id']} {field}",
                          file=sys.stderr)
                    continue
                ledger.append({
                    "app_id": rec["app_id"], "name": rec["name"], "field": field,
                    "previous_value": app[field], "new_value": fr["corrected_value"],
                    "reason": fr["reason"], "replacement_evidence": fr["replacement_evidence"],
                    "changed_by": "verifier", "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                app[field] = fr["corrected_value"]
                app["verification_status"] = "corrected"
                app["evidence"].append({
                    "claims": [field.split("_")[0] if field != "technical_verdict" else "verdict"],
                    "url": fr["replacement_evidence"],
                    "note": f"verifier correction: {fr['reason'][:200]}",
                })

    # Normalize a cross-row invariant: a row claiming an official vendor MCP
    # exposes MCP as a protocol. Researchers applied this inconsistently
    # (70/81 rows did, 11 didn't); the value is derivable, so code owns it.
    normalized = 0
    for app in apps.values():
        if ("official_vendor_mcp" in (app.get("mcp_status") or [])
                and "mcp" not in (app.get("api_protocols") or [])):
            app["api_protocols"] = (app.get("api_protocols") or []) + ["mcp"]
            normalized += 1

    # Recompute derived fields on all rows (corrected or not).
    finals = []
    for app in apps.values():
        r = AppResult.model_validate(app)
        r.final_bucket = final_bucket(r)
        r.risk_score, r.risk_flags = risk_assessment(r)
        finals.append(r.model_dump(mode="json"))

    finals.sort(key=lambda a: a["app_id"])
    (EXPORTS / "apps.final.json").write_text(json.dumps(finals, indent=1))
    with (EXPORTS / "corrections.jsonl").open("w") as f:
        for row in ledger:
            f.write(json.dumps(row) + "\n")
    (EXPORTS / "verification_stats.json").write_text(json.dumps(stats, indent=2))

    print(f"apps verified: {stats['verified'] + stats['corrected']}"
          f" (corrected: {stats['corrected']})")
    print(f"fields reviewed: {stats['fields_reviewed']}, supported: {stats['fields_supported']},"
          f" contradicted: {stats['fields_contradicted']}, partial: {stats['fields_partial']}")
    print(f"corrections applied: {len(ledger)}")
    print(f"protocol invariant normalized (vendor MCP -> protocols include mcp): {normalized}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
