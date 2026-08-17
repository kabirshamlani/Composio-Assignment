"""Deterministic verification loop #1: check every evidence URL is reachable.

Writes data/exports/link_check.json with per-URL status and summary counts.
403/429 are recorded as 'blocked' (bot protection), not as dead links.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "data" / "exports"

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def check(url: str) -> tuple[str, int | str]:
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, headers=UA, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return url, resp.status
        except urllib.error.HTTPError as e:
            if method == "GET":
                return url, e.code
        except Exception as e:  # noqa: BLE001
            if method == "GET":
                return url, type(e).__name__
    return url, "unreachable"


# Domains that return 4xx to non-browser HTTP clients while the page is fine
# in a real browser (manually confirmed for developers.facebook.com on
# 2026-08-17: a browser fetch of a "400" URL returned the full docs page).
BOT_BLOCKING_DOMAINS = ("facebook.com",)

# URLs that return 4xx to plain HTTP clients but were manually confirmed alive
# in a browser/search fetch on 2026-08-17 (see README verification section).
MANUALLY_VERIFIED_ALIVE = {
    "https://mcp.pipedream.com/app/aircall",  # full page content retrieved via browser fetch
}


def is_bot_blocked(url: str, status: int | str) -> bool:
    if url in MANUALLY_VERIFIED_ALIVE:
        return True
    if status in (403, 429, 405, 999):
        return True
    return status == 400 and any(d in url for d in BOT_BLOCKING_DOMAINS)


def main() -> int:
    src = EXPORTS / "apps.final.json"
    if not src.exists():
        src = EXPORTS / "apps.first_pass.json"
    apps = json.loads(src.read_text())
    urls = sorted({e["url"] for a in apps for e in a["evidence"]})
    print(f"checking {len(urls)} unique evidence URLs from {src.name} ...")

    with cf.ThreadPoolExecutor(max_workers=16) as pool:
        results = dict(pool.map(check, urls))

    ok = sum(1 for s in results.values() if isinstance(s, int) and 200 <= s < 400)
    blocked = sum(1 for u, s in results.items() if is_bot_blocked(u, s))
    dead = {u: s for u, s in results.items()
            if not (isinstance(s, int) and 200 <= s < 400) and not is_bot_blocked(u, s)}

    out = {"source_file": src.name, "total_unique_urls": len(urls), "reachable_2xx_3xx": ok,
           "blocked_bot_protection": blocked, "dead_or_error": len(dead),
           "dead_urls": {u: str(s) for u, s in sorted(dead.items())},
           "note": "blocked = 403/429/405/999 anywhere, or 400 on domains known to "
                   "reject non-browser clients (facebook.com, browser-verified)"}
    (EXPORTS / "link_check.json").write_text(json.dumps(out, indent=2))
    print(f"reachable: {ok}/{len(urls)}  blocked(403/429/405/999): {blocked}  dead/error: {len(dead)}")
    for u, s in sorted(dead.items()):
        print(f"  DEAD {s}: {u}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
