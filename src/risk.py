"""Deterministic derivation of reviewer-facing bucket and risk score.

The research agent never assigns the final bucket or decides whether its own
row needs verification; both are computed here from the claimed fields.
"""

from __future__ import annotations

from schemas import (
    GATED,
    SELF_SERVE,
    AccessClass,
    ApiBreadth,
    AppResult,
    Confidence,
    McpClass,
    TechnicalVerdict,
)


def final_bucket(r: AppResult) -> str:
    match r.technical_verdict:
        case TechnicalVerdict.BUILDABLE_NOW:
            if r.access in SELF_SERVE:
                return "READY — SELF-SERVE"
            if r.access in GATED:
                return "READY — GATED"
            return "READY — ACCESS UNKNOWN"
        case TechnicalVerdict.PARTIALLY_BUILDABLE:
            return "PARTIAL"
        case TechnicalVerdict.NOT_BUILDABLE:
            return "NOT BUILDABLE"
        case TechnicalVerdict.UNKNOWN:
            return "UNKNOWN"
        case _:
            raise AssertionError(f"unhandled verdict: {r.technical_verdict}")


def risk_assessment(r: AppResult) -> tuple[int, list[str]]:
    """Higher score == more likely to be wrong == verify first."""
    score = 0
    flags: list[str] = []

    def add(points: int, flag: str) -> None:
        nonlocal score
        score += points
        flags.append(flag)

    if McpClass.OFFICIAL_VENDOR in r.mcp_status:
        add(4, "official_vendor_mcp_claim")
    if r.technical_verdict == TechnicalVerdict.NOT_BUILDABLE:
        add(4, "not_buildable_claim")
    if r.api_breadth == ApiBreadth.NONE:
        add(3, "negative_api_existence_claim")
    if r.confidence == Confidence.LOW:
        add(3, "low_researcher_confidence")
    if r.access in {AccessClass.PARTNER_GATED, AccessClass.CONTACT_SALES,
                    AccessClass.PRODUCTION_APPROVAL, AccessClass.INVITE_ONLY}:
        add(2, "hard_commercial_gate_claim")
    if r.confidence == Confidence.MEDIUM:
        add(1, "medium_researcher_confidence")
    if r.access == AccessClass.UNKNOWN or r.technical_verdict == TechnicalVerdict.UNKNOWN:
        add(2, "unknown_core_field")
    if len(r.evidence) < 2:
        add(2, "thin_evidence")

    return score, flags


VERIFY_THRESHOLD = 3  # score >= 3 -> independent verification pass
