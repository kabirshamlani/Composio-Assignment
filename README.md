# Agent Toolkit Research — 100 Apps, Evidence-First

Take-home for **Composio · AI Product Ops Intern**. An agent pipeline researched the
assignment's 100-app list against official documentation — auth, credential access, API
surface, MCP availability, buildability — with field-level evidence, an independent
verification loop, and deterministic metrics. The deliverable is one self-contained
HTML case study: **`web/index.html`** (no CDNs, no external fonts, works offline).

> **This README is the only documentation file, by design.** It covers: what was
> built, why each decision was made, what was compared, how the run actually
> happened, how accuracy was verified, how to reproduce it, and how to explain
> the whole thing in an interview (§11) plus a requirement-by-requirement map to
> the assignment brief (§12).

---

## 1. Headline results (all computed by `src/metrics.py`, never by a model)

| Result | Count |
|---|---:|
| Apps researched | **100** (10 categories × 10 apps) |
| READY — SELF-SERVE (buildable today, self-serve credentials) | **76** |
| READY — GATED (technically ready, commercially gated) | **15** |
| PARTIAL (narrow / read-only / enterprise-only APIs) | **7** |
| NOT BUILDABLE (Sherlock, Mermaid CLI — local OSS CLIs, not hosted APIs) | **2** |

Key patterns (full prose on the HTML page, each number traceable to `data/exports/metrics.json`):

- **Auth:** OAuth2 authorization-code is primary for 47/100; API keys for 32/100.
  Counting all supported methods, 73 apps support some OAuth2 flow and 84 accept a key/token.
- **Access:** 79/100 are self-serve. Gating concentrates in **Fintech (6/10 gated —
  sandbox instant, production reviewed)**, **Marketing/Ads (5/10 — approval and partner
  programs)** and the **AI/Research tier (3/10 — enterprise licenses behind consumer
  brands like NotebookLM and Otter)**. Developer-infra and Productivity are 10/10 self-serve.
- **MCP:** 81/100 apps now ship an **official vendor MCP server** (2026 reality — each claim
  carries an ownership citation). Composio already has toolkits for 54/100.
- **Blockers:** production approval (9), partner/sales gates (9), paid-plan requirements (7),
  enterprise licenses (2). The #1 blocker is paperwork, not technology.

## 2. Verification results (how we know the findings are trustworthy)

Three loops, run in order, all artifacts in `data/exports/`:

1. **Deterministic validation** (`src/validate_results.py`) over all 100 rows: Pydantic
   schema, identity match against the input list, taxonomy enums, and the evidence
   policy (every non-unknown core claim — auth/access/api/mcp — needs ≥1 evidence URL).
   First pass: 100/100 schema-valid, 12 rows had evidence gaps → routed to audit.
2. **Independent adversarial re-research** of a **46-app audit set** (46% of the dataset):
   every high-risk row (risk ≥ 5), **2 seeded-random rows per category (seed 20260817,
   reproducible via `src/make_audit_sample.py`)**, every evidence-gap row, plus extra rows
   pulled in during risk recalibration. Seven verifier agents that did not write the drafts
   re-checked **368 field-level claims**:
   - **330/368 (89.7%) fully supported** on first pass;
   - **27 partially supported** (value right, evidence thin — verifier supplied the URL);
   - **10 contradicted → corrected with replacement evidence** (see `corrections.jsonl`);
   - **1 insufficient**. After corrections: **367/368 (99.7%) supported**.
3. **Citation liveness check** (`scripts/verify_links.py`) of all **485 evidence URLs**:
   464 reachable, 21 bot-blocked (403/429, or 400 on `developers.facebook.com`, which
   was manually confirmed alive via browser fetch), **0 dead** after a repair pass.

### Honest misses (the interesting failures, shown on the page too)

| App | Field | First pass | Corrected | Why it was wrong |
|---|---|---|---|---|
| Help Scout | mcp_status | `none_found` (vendor MCP) | `official_vendor_mcp` | Vendor MCP is documented in the *help center*, not the developer portal the researcher searched |
| Clay | api_breadth / verdict | `narrow` / `partially_buildable` | `medium` / `buildable_now` | Stale: Clay shipped a public API with OpenAPI spec after the sources the researcher found |
| fanbasis | mcp_status | `none_found` | `official_vendor_mcp` | The cited docs site itself had an "AI Agent / MCP Connector" section the researcher missed |
| Brex | mcp_status | `official_composio_toolkit` only | + `official_vendor_mcp` | Brex hosts an official MCP at `api.brex.com/mcp`, documented on a page the researcher didn't reach |
| Grain | mcp_status | `none_found` | `official_vendor_mcp` | Official Grain MCP (`api.grain.com/_/mcp`) lives in vendor docs the researcher skimmed past |
| SendGrid | evidence URL | `live.docs.dev.twilio.com/...` | real docs URL | **Hallucinated-looking URL** — the claim was right but the citation domain didn't exist; caught by the link checker |
| SE Ranking | MCP evidence | 404'd GitHub repo | `seranking.com/mcp.html` | Wrong citation for a real fact — the official MCP exists, the cited repo didn't |

**Failure taxonomy that emerged:** (a) *docs-location blind spots* — the most common
contradiction by far: official vendor MCPs announced in help centers, blogs, or release
notes rather than the developer portal the researcher searched (Help Scout, fanbasis,
Brex, Grain); (b) *staleness* — the product shipped after the sources the researcher
read (Clay); (c) *right-fact-wrong-citation* — caught mechanically by the link checker
(SendGrid, SE Ranking). All three now have a loop that catches them.

## 3. Input integrity

`src/validate_input.py` is a hard gate before anything runs: it checks the count
(100/100), ID continuity (1–100, no gaps or duplicates), name uniqueness, and writes
`data/input_manifest.json` with the input file's SHA-256 — so every downstream artifact
is traceable to one exact input. Policy encoded in the gate: if rows were ever missing
or malformed, the pipeline reports the gap and refuses to let anything invent rows.

## 4. Architecture: deterministic control plane, agent intelligence plane

```
data/apps.yaml (verbatim transcription, hashed)
      │
      ▼
Stage 0  src/validate_input.py      → hard gate, input_manifest.json (count, hash)
      │
      ▼
Stage 1  13 research agents          → one isolated batch of 6–8 apps each, live web
         (prompts/research.md)         research of official docs, strict JSON per app
      │                                → data/first_pass/apps/*.json
      ▼
Stage 2  src/validate_results.py    → schema + evidence policy + identity checks
         src/risk.py                 → risk score & reviewer bucket derived IN CODE
      │
      ▼
Stage 3  src/make_audit_sample.py   → seeded stratified + risk-targeted audit sample
         7 verifier agents           → adversarial re-research, field-by-field verdicts
         (prompts/verify.md)         → data/verification/*.json (46 records)
      │
      ▼
Stage 4  scripts/verify_links.py    → HTTP liveness of every evidence URL
         evidence-repair agent       → fixes dead citations, re-verifies the claims
      │
      ▼
Stage 5  src/apply_corrections.py   → correction ledger (previous value preserved),
                                       apps.final.json
      │
      ▼
Stage 6  src/metrics.py             → every count/percentage/cluster, metrics.json
      │
      ▼
Stage 7  src/render.py + web/template.html
                                     → single self-contained HTML; narrative prose can
                                       only reference numbers via {metric.key}
                                       placeholders resolved from metrics.json
```

**Design rules enforced in code, not by prompt hygiene:**

- **One app per isolated context.** No research agent sees another app's findings, so an
  error can't propagate across rows.
- **Models claim facts; code assigns grades.** The reviewer bucket (READY/PARTIAL/NOT
  BUILDABLE), risk scores, and every statistic are computed in Python from claimed fields.
- **Evidence or unknown.** A non-unknown core claim without a citation fails validation.
  `unknown` is a first-class value, preserved and counted.
- **Two separate axes.** Technical buildability ≠ commercial access. "READY — GATED"
  (e.g. LinkedIn Ads) is a partnerships queue item, not an engineering failure.
- **Corrections are additive.** `corrections.jsonl` keeps previous value, reason,
  replacement evidence, and who changed it. Nothing is silently overwritten.

## 5. Decisions and comparisons (what was considered, what was chosen, why)

| Decision | Options compared | Choice + reason |
|---|---|---|
| Orchestration | (a) free-form agent swarm; (b) one giant prompt over 100 apps; (c) deterministic queue + isolated agent jobs | **(c)** — apps are independent but correctness depends on provenance and clean retries; an LLM must never own job state or compute totals. (b) was rejected because cross-app context causes leakage and truncation; (a) because it's unauditable. |
| Research execution | (a) standalone Python + Anthropic web-search tool; (b) IDE-agent orchestration (parallel subagents with live web tools) | **(b) for this run** — the local Anthropic gateway token was expired (401) at run time, verified by direct API test. (a) ships in the repo as `src/standalone_agent.py` for reviewers with keys; same prompt, same schema. |
| Verifier independence | (a) same model re-reflecting; (b) different provider; (c) different isolated context + adversarial prompt + own searches | **(c)** — (b) was the plan but unavailable without a second provider key; (a) is worthless (correlated errors). Honest limitation: context-level, not provider-level, independence — stated on the page. The verifiers still contradicted 10 claims and repaired 27, so the loop demonstrably wasn't a rubber stamp. |
| Verification scope | (a) re-check all 100; (b) fixed 10% random; (c) stratified 2-per-category + all high-risk + all evidence-gap rows, seeded | **(c), 46 apps / 368 claims** — (a) doubles cost for low marginal information on low-risk rows; (b) misses exactly the rows most likely to be wrong. The seed (20260817) is recorded and the per-category RNG is keyed on (seed, category), so the sample is reproducible and stable. |
| Risk weights | keep original weights (official-vendor-MCP claim = +4 "suspicious") vs recalibrate | **Recalibrated scope, kept weights visible** — the first-pass queue hit 82/100 apps because official vendor MCPs are genuinely common in 2026, not rare. A human re-scoped verification to the stratified audit rather than blindly re-checking 82. Documented as a human-in-the-loop moment. |
| Dead links | treat every non-2xx as a dead citation vs classify | **Classify** — `developers.facebook.com` returns 400 to non-browser clients (confirmed alive via browser fetch); 403/429 is bot protection. Only true 404s/bad domains counted as dead, and each triggered claim re-verification, not just URL swapping. |
| Ambiguous rows | guess the famous product vs follow the hint | **Follow the hint, state the interpretation** — "YouTube Transcript" is transcriptapi.com (per the hint), not YouTube's own API; "NotebookLM" is the Google Cloud Enterprise offering; "Mermaid CLI" is the OSS CLI, evaluated as such. Each row records which product it covers. |
| HTML | (a) framework + CDN charts; (b) single file, inline CSS/JS, embedded JSON | **(b)** — a reviewer may open the file offline; CDN failures would break the page. Charts are plain DOM bars; the full dataset is embedded (340 KB total). |
| Docs | multiple markdown files (runbook style) vs one README | **One README** (explicit owner preference). Prompt files (`prompts/`, `.claude/agents/`) are functional inputs, not documentation. |

## 6. How the run actually happened (full honesty)

- The **research fleet** was 13 parallel Cursor subagents (6–8 apps each) with live web
  search/fetch, each writing schema-validated JSON per app. The **verification fleet** was
  7 independent subagents + 1 evidence-repair subagent. The orchestrator (this repo's
  Python) did input validation, evidence policy, risk, sampling, corrections, metrics,
  rendering, and link checking.
- The **standalone agent** (`src/standalone_agent.py`, Anthropic API + web-search tool)
  could not run because the available gateway token was expired (401 on a direct
  `/v1/messages` test). It is included and documented for reproduction with a valid key.
- **Where humans were needed** (also on the page): re-scoping verification when the risk
  queue blew up to 82/100; adjudicating bot-blocked vs dead URLs (browser-confirming a
  Facebook docs page and a Pipedream MCP page); taxonomy edge rulings (Sherlock and
  Mermaid CLI = `local_cli_only`, not "no API exists"; sandbox ≠ production for
  fintech/ads); pinning ambiguous rows to the product the hint meant; and enforcing that
  evidence-gap rows go to independent audit instead of being self-patched.
- **Claude Code readiness:** `.claude/agents/researcher.md` and `.claude/agents/verifier.md`
  are drop-in subagent definitions; `prompts/research.md` and `prompts/verify.md` are the
  canonical prompts. The same pipeline can be driven by Claude Code using these files.
- **Composio in the loop:** every app's `mcp_status` includes whether an official
  **Composio toolkit** already exists (checked against `docs.composio.dev` toolkit pages) —
  54/100 do. A production version of this pipeline would execute research through
  Composio's SDK (e.g. a web-search + fetch toolset) so tool calls themselves are
  observable; that integration point is isolated in the agent-runner boundary.

## 7. Repository layout

```
├── README.md                      ← this file (only doc file)
├── requirements.txt
├── prompts/
│   ├── research.md                ← canonical research-agent prompt (rules + schema)
│   └── verify.md                  ← canonical adversarial-verifier prompt
├── .claude/agents/                ← ready-to-use Claude Code subagent definitions
│   ├── researcher.md
│   └── verifier.md
├── src/
│   ├── schemas.py                 ← Pydantic taxonomies & AppResult schema
│   ├── validate_input.py          ← Stage 0 gate (count, continuity, SHA-256)
│   ├── validate_results.py        ← schema + evidence-policy validator
│   ├── risk.py                    ← bucket derivation + risk scoring (code-owned)
│   ├── make_audit_sample.py       ← seeded stratified + risk-targeted sampler
│   ├── apply_corrections.py       ← correction ledger + final dataset
│   ├── metrics.py                 ← ALL numbers on the page
│   ├── render.py                  ← template + data → web/index.html
│   └── standalone_agent.py        ← runnable one-app research agent (needs API key)
├── scripts/
│   └── verify_links.py            ← evidence-URL liveness checker
├── data/
│   ├── apps.yaml                  ← verbatim 100-app input list
│   ├── input_manifest.json        ← input hash + integrity record
│   ├── first_pass/apps/*.json     ← 100 per-app research files (agent output)
│   ├── verification/*.json        ← 46 field-by-field verification records
│   └── exports/
│       ├── apps.final.json        ← verified dataset (with corrections applied)
│       ├── apps.first_pass.json   ← pre-correction dataset (kept for diffing)
│       ├── metrics.json           ← every number on the page
│       ├── corrections.jsonl      ← the honest-misses ledger
│       ├── verification_stats.json / verification_queue.json
│       ├── audit_sample.json      ← who was audited and why (seed recorded)
│       ├── link_check.json        ← URL liveness results
│       └── narrative.json         ← page prose ({metric.key} placeholders only)
└── web/
    ├── template.html              ← single-file UI (inline CSS/JS, no CDNs)
    └── index.html                 ← THE DELIVERABLE (open directly in a browser)
```

## 8. How to run

```bash
pip install -r requirements.txt

# Stage 0 — input gate (validates the 100-app list, prints the manifest)
python3 src/validate_input.py

# Research: either drive the agents (Cursor / Claude Code with .claude/agents/*),
# or run the standalone agent on chosen apps with a valid key:
ANTHROPIC_API_KEY=... python3 src/standalone_agent.py --ids 21,56,60

# Pipeline (deterministic, idempotent — safe to re-run):
python3 src/validate_results.py        # schema + evidence policy + risk
python3 src/make_audit_sample.py       # seeded audit sample
#   ...run verifier agents over the sample (prompts/verify.md)...
python3 src/apply_corrections.py       # ledger + apps.final.json
python3 scripts/verify_links.py        # citation liveness
python3 src/metrics.py                 # metrics.json
python3 src/render.py                  # web/index.html

# View
python3 -m http.server 8000 --directory web   # or just open web/index.html
```

## 9. Known limitations

1. **Model-family independence** between extractor and verifier was not achievable at
   run time (single available provider); independence is at the context/prompt level.
2. **Point-in-time snapshot** (2026-08-17). Several corrections were staleness-related
   (Clay's public API; Brex, Grain, Help Scout vendor MCPs); these facts drift. A
   production version needs re-crawl + change detection.
3. **54 low-risk rows** passed deterministic validation and link checks but not the
   adversarial re-research. Sampling implies ~90% first-pass field accuracy there, so a
   handful of residual field errors likely remain outside the audited 46.
4. **Bot-blocked domains** (21 URLs, mostly Meta): claims rest on browser-verified
   fetches and search-indexed content rather than plain-HTTP snapshots.
5. **Ambiguity resolved by hint:** a few rows name a brand, not a product
   ("YouTube Transcript", "NotebookLM", "higgsfield"); the studied product follows the
   assignment's hint and is stated on the row, but a different interpretation would
   change those rows' verdicts.
6. Raw page snapshots (HTML archives of every source) were cut for time; evidence is
   URL + quoted note + liveness check instead of stored copies.

## 10. Deploying the page

`web/index.html` is fully static and self-contained — GitHub Pages, Netlify Drop, or
Vercel all work as-is. Before deploying: put the repo URL into the `footer` field of
`data/exports/narrative.json` and re-run `python3 src/render.py`.

---

## 11. How to explain this project (interview walkthrough)

This section is the story of the approach, in the order you'd tell it. Every claim in
it is backed by an artifact in the repo you can open live in the interview.

### The 2-minute pitch

> "The task looks like 'research 100 apps', but the real problem is **trust at scale**:
> a language model can produce 100 plausible rows in one shot, and some of them will be
> confidently wrong. So I didn't build a form-filler — I built a small **evidence
> pipeline**. Agents are only allowed to *claim facts with citations*; deterministic
> Python owns everything that must not be creative: validation, risk scoring, sampling,
> the correction ledger, every statistic, and the final page. Then a second fleet of
> agents that never saw the drafts adversarially re-researched a 46-app sample and a
> link checker fetched all 485 citations. First-pass accuracy was 89.7% at field level;
> the loops caught 10 real errors and lifted it to 99.7% — and I can show you exactly
> which claims were wrong, why, and what evidence fixed them."

### The approach, step by step (and *why* each step exists)

1. **Pin the input before anything runs.** `validate_input.py` checks 100 IDs,
   continuity, duplicates, and hashes the file into `input_manifest.json`.
   *Why:* if the input is ambiguous, every downstream number is unfalsifiable. Ops
   thinking: gate at the cheapest point.
2. **Define the schema before the research.** `schemas.py` (Pydantic) fixes taxonomies:
   auth methods, access classes (with `sandbox_self_serve_production_gated` as its own
   value!), MCP status (vendor ≠ community ≠ Composio toolkit), verdicts, blockers.
   *Why:* patterns across 100 apps only exist if all 100 rows speak the same language.
   The interesting distinctions (sandbox vs production, vendor vs community MCP) were
   designed in, not discovered later.
3. **Research with isolated agents, not one big prompt.** 13 parallel agents, 6–8 apps
   each, one app per context, official docs only, strict JSON out, every non-unknown
   claim cited, `unknown` allowed. *Why:* isolation stops error propagation; "unknown
   is valid" removes the incentive to guess; citations make every cell auditable.
4. **Let code, not models, do the judging.** Risk scores and the reviewer bucket
   (READY / GATED / PARTIAL / NOT BUILDABLE) are computed in `risk.py` from claimed
   fields. *Why:* models flatter their own work; code applies one rule to all rows.
5. **Verify like an adversary.** A seeded, stratified sample (every high-risk row +
   2 random per category + every evidence-gap row = 46 apps) went to 7 verifier agents
   with an explicitly adversarial prompt and a trap list (sandbox-as-production,
   community-MCP-as-official, stale versions...). Contradictions require replacement
   evidence. *Why:* re-checking everything doubles cost for little information;
   random-only sampling misses exactly the rows most likely wrong.
6. **Check the citations themselves.** `verify_links.py` fetched all 485 URLs; the one
   hallucinated-looking domain (SendGrid) and one dead repo (SE Ranking) were caught
   this way and repaired with claim re-verification, not just URL swaps.
7. **Correct additively, never silently.** `apply_corrections.py` writes a ledger with
   previous value → new value → reason → replacement evidence, then recomputes buckets.
8. **Compute the story, then render it.** `metrics.py` produces every number;
   the page's prose contains `{metric.key}` placeholders that `render.py` resolves —
   the narrative literally cannot state a number that wasn't computed.

### What the numbers say (the "insight over raw table" part)

- **The bottleneck is paperwork, not APIs.** 91/100 are technically ready; only 2 are
  truly not buildable (both local CLIs). The gated 15 are a literal partnerships queue.
- **Gating follows category economics:** fintech gates production (6/10), ad platforms
  gate access to spend (5/10), and the AI tier hides enterprise licenses behind consumer
  brands (NotebookLM, Otter). Dev-infra and productivity are 100% self-serve.
- **OAuth2 wins (47/100 primary), keys are the fast path (84 accept key/token)** —
  so a toolkit platform's real moat is OAuth onboarding UX plus token refresh.
- **81/100 have official vendor MCPs in 2026** — the biggest surprise, and the single
  most error-prone claim (4 of the 10 contradictions were missed vendor MCPs announced
  outside developer portals). That's an ops lesson: know where each fact class lives.

### Likely probe questions, with honest answers

- **"How do you know the 54 un-audited rows are right?"** I don't, individually — the
  audit measures them statistically: ~90% of field claims were clean on first pass, and
  the audited set was deliberately biased toward the *hardest* rows, so the residual
  set is easier than the audited one. Scaling this up, the fix is rotating audits, not
  bigger first passes.
- **"Your verifier is the same model family — isn't that circular?"** Partly, and it's
  stated on the page. Independence here is context + prompt + own searches, not
  provider. It still found 10 contradictions and 27 thin citations, so it wasn't a
  rubber stamp. With a second provider key, `standalone_agent.py`'s routing makes
  cross-provider verification a config change.
- **"Why one HTML file instead of an app?"** The reviewer's environment is unknown;
  a single file with embedded data can't break. All interactivity (search, filters,
  expandable evidence per row) is inline JS over embedded JSON.
- **"What would you do differently with more time?"** Store page snapshots for every
  citation (evidence that survives site changes), add a second provider for true
  independence, wire research through Composio's SDK so tool calls are observable,
  and add change-detection re-crawls — these are also listed as limitations.
- **"Where did the agent actually fail?"** Show `corrections.jsonl` live: Help Scout /
  Brex / Grain / fanbasis missed vendor MCPs hiding outside dev portals; Clay was stale;
  SendGrid had a fabricated-looking citation for a true fact. Each failure produced a
  loop that now catches its class.

### One-line takeaways per artifact (for showing the repo live)

| Artifact | The point it proves |
|---|---|
| `data/input_manifest.json` | The input was pinned and hashed before anything ran |
| `data/first_pass/apps/017.json` (any) | Raw agent output: strict JSON, citations per claim |
| `data/exports/verification_queue.json` | Risk scoring is code — you can read the flags |
| `data/exports/audit_sample.json` | Who was audited and *why*, seed recorded |
| `data/verification/060.json` | A verifier catching a real error (Clay), field by field |
| `data/exports/corrections.jsonl` | Nothing corrected silently — previous value kept |
| `data/exports/link_check.json` | All 485 citations fetched, classification honest |
| `data/exports/metrics.json` | Every number on the page, computed |
| `web/index.html` | The deliverable — open it offline, everything works |

## 12. Assignment requirements → where they're satisfied

| Requirement (from the brief) | Where |
|---|---|
| Per app: category + one-liner | `apps.final.json` fields `category`, `one_liner`; table on the page |
| Per app: auth methods (OAuth2 / key / basic / token / other) | `primary_auth` + `auth_methods`; AUTH pattern card; auth filter on the table |
| Per app: self-serve vs gated (free/trial vs paid/admin/partner) | `access` taxonomy (7 values incl. sandbox-vs-production); ACCESS pattern card |
| Per app: API surface (REST/GraphQL, breadth, existing MCP) | `api_protocols`, `api_breadth`, `mcp_status`; MCP pattern card |
| Per app: buildability verdict + main blocker | `technical_verdict` + `primary_blocker` + code-derived `final_bucket` |
| Per app: evidence (docs URL behind each answer) | `evidence[]` with per-claim URLs + notes; expandable on every table row; liveness-checked |
| **Find the patterns** (auth dominance, self-serve vs gated by category, top blocker, easy wins vs outreach) | Five pattern cards at the top of the page; clusters section (build-now 76 / outreach 15 / partial 7 / investigate 2) |
| **Do it with an agent, not by hand** + what it does, where a human was needed | Agent section on the page (flow + agent-does + human-needed); §4–§6 here |
| **Verify accuracy**: sample the 100, cross-check against real docs, report right/wrong | 46-app / 368-claim adversarial audit; hits and misses shown on the page; §2 here |
| **Real verification loops** + accuracy moving from lower first pass to higher | Three loops (validators → adversarial audit → link checking); 89.7% → 99.7% with numerators/denominators shown |
| **Single self-explanatory HTML page** (findings, patterns up top, agent, proof, verification) | `web/index.html` — headline + patterns first, skimmable filterable table, agent, proof (runnable trigger), verification, method |
| **Proof: the app you built, live link or runnable trigger** | "Proof" section on the page: exact commands to run the research agent end to end; full artifact list; `standalone_agent.py` in the repo |
| Honesty: wrong answers and defeats stated on the page | Honest-misses table + limitations on the page; UNKNOWN preserved; gated = a finding, not a failure |
| No paid accounts needed | All research from public docs; gated apps recorded as gated with evidence |
| Repo + short README on how to run the research agent | This README §8; repo layout §7 |
| Composio SDK/MCP "in the spirit of the role" | Composio toolkit coverage checked for all 100 (54 exist); SDK integration point isolated and documented (§6); full Composio-SDK execution listed as next step |

**Submission checklist:** ① deploy `web/index.html` (see §10) and note the live URL;
② push this repo and put the repo URL in the page footer (`narrative.json` → re-render);
③ submit both links.
