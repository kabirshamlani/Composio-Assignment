"""Standalone runnable research agent (for reviewers with an Anthropic key).

This reproduces what the Cursor research subagents did in the submitted run:
one isolated agent per app, live web search against official docs, strict JSON
output validated by src/schemas.py.

Usage:
    ANTHROPIC_API_KEY=... python3 src/standalone_agent.py --ids 21,56,58

Note: the submitted dataset was produced by Cursor agent orchestration (see
README, 'How the run actually happened') because the local model gateway
token was expired at run time. This script is the equivalent standalone path.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from anthropic import Anthropic

from schemas import AppResult

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "first_pass" / "apps"
MODEL = os.environ.get("RESEARCH_MODEL", "claude-sonnet-4-5")


def research_one(client: Anthropic, app: dict, prompt_template: str) -> AppResult:
    task = (
        f"{prompt_template}\n\n---\nYour assigned app:\n"
        f"id={app['id']} | name={app['name']} | category={app['category']} | hint={app['hint']}\n"
        "Research it now using web search. Then output ONLY the JSON object "
        "(no fences, no commentary) matching the output file format."
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
        messages=[{"role": "user", "content": task}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    start, end = text.find("{"), text.rfind("}")
    result = AppResult.model_validate_json(text[start:end + 1])
    result.researcher = MODEL
    result.retrieved_at = datetime.now(timezone.utc).isoformat()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", required=True, help="comma-separated app ids, e.g. 21,56,58")
    args = parser.parse_args()
    ids = {int(x) for x in args.ids.split(",")}

    apps = yaml.safe_load((ROOT / "data" / "apps.yaml").read_text())["apps"]
    prompt_template = (ROOT / "prompts" / "research.md").read_text()
    client = Anthropic()  # requires ANTHROPIC_API_KEY
    OUT.mkdir(parents=True, exist_ok=True)

    failures = 0
    for app in apps:
        if app["id"] not in ids:
            continue
        print(f"researching {app['id']:>3} {app['name']} ...", flush=True)
        try:
            result = research_one(client, app, prompt_template)
        except Exception as exc:  # noqa: BLE001 - report per-app, keep queue alive
            print(f"  FAILED: {exc}", file=sys.stderr)
            failures += 1
            continue
        path = OUT / f"{app['id']:03d}.json"
        path.write_text(result.model_dump_json(indent=1))
        print(f"  wrote {path.relative_to(ROOT)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
