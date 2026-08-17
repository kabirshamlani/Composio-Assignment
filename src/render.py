"""Stage 10: render the single self-contained HTML case study.

All data is embedded as JSON computed by metrics.py / apply_corrections.py.
The page has zero external dependencies (no CDN, no fonts, no frameworks).
The narrative text lives in data/exports/narrative.json and may only
reference numbers via {metric.path} placeholders resolved HERE from
metrics.json — prose can never carry a number the pipeline didn't compute.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "data" / "exports"
OUT = ROOT / "web" / "index.html"


def resolve_placeholders(text: str, metrics: dict) -> str:
    def lookup(match: re.Match) -> str:
        node = metrics
        for part in match.group(1).split("."):
            node = node[part]
        return str(node)
    return re.sub(r"\{([a-z0-9_.\- —A-Z]+)\}", lookup, text)


def main() -> int:
    apps = json.loads((EXPORTS / "apps.final.json").read_text())
    metrics = json.loads((EXPORTS / "metrics.json").read_text())
    corrections = [json.loads(line) for line in
                   (EXPORTS / "corrections.jsonl").read_text().splitlines() if line.strip()]
    vstats = json.loads((EXPORTS / "verification_stats.json").read_text())
    manifest = json.loads((ROOT / "data" / "input_manifest.json").read_text())
    narrative = json.loads((EXPORTS / "narrative.json").read_text())
    # ensure_ascii=False keeps em-dashes literal so bucket-key placeholders match
    narrative = json.loads(resolve_placeholders(json.dumps(narrative, ensure_ascii=False), metrics))

    template = (ROOT / "web" / "template.html").read_text()
    html = template.replace("/*__DATA__*/", json.dumps({
        "apps": apps, "metrics": metrics, "corrections": corrections,
        "vstats": vstats, "manifest": manifest, "narrative": narrative,
    }, ensure_ascii=False))
    OUT.write_text(html)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
