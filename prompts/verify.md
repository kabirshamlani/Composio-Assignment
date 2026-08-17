# Independent verifier prompt (one batch of apps, one isolated agent per batch)

You are an independent adversarial verifier. You did NOT create the drafts you
are checking, and you must not trust them. For each assigned app you will
re-check the claims against the live official documentation and produce a
verification record.

## Procedure per app

1. Read the draft at `data/first_pass/apps/<id>.json`.
2. Independently open the official docs (do your OWN searches; do not just
   confirm the draft's evidence URLs, though you should also open at least one
   of them to confirm it exists and says what the note claims).
3. For each of these fields decide a verdict:
   `primary_auth`, `auth_methods`, `access`, `api_breadth`, `api_protocols`,
   `mcp_status`, `technical_verdict`, `primary_blocker`.
   Verdicts: `SUPPORTED, PARTIALLY_SUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE, STALE_OR_AMBIGUOUS`.
4. If CONTRADICTED or clearly wrong, provide `corrected_value` AND a
   `replacement_evidence` URL. No correction without replacement evidence.

## Traps to check for

- sandbox signup recorded as production self-serve (fintech, ad platforms);
- login-gated docs or bot walls recorded as partner/commercial gating;
- community MCP servers recorded as official vendor MCPs (verify repo ownership);
- write support claimed where docs only show read endpoints;
- old/deprecated API versions cited as current;
- the wrong product with a similar name.

## Output

Write ONE file `data/verification/<id as 3 digits>.json`:

```json
{
  "app_id": 33,
  "name": "LinkedIn Ads",
  "field_reviews": [
    {"field": "access", "draft_value": "self_serve_free", "verdict": "CONTRADICTED",
     "reason": "Marketing API requires applying to the LinkedIn Marketing API program",
     "corrected_value": "partner_gated",
     "replacement_evidence": "https://learn.microsoft.com/en-us/linkedin/marketing/quick-start"}
  ],
  "overall": "corrected",   // one of: verified | corrected | inconclusive
  "checked_at": "2026-08-17",
  "notes": "short summary of what you re-checked"
}
```

Every field you checked must appear in `field_reviews`, including SUPPORTED
ones. Valid JSON, no markdown fences.
