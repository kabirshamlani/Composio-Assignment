"""Canonical schemas for the evidence-first app research pipeline.

Design rules (see README):
- unknown is a valid value and is distinct from false/none;
- every non-unknown factual claim must carry at least one evidence URL;
- technical buildability and commercial access gating are separate axes;
- the reviewer-facing bucket is DERIVED in code (risk.py), never asserted by a model.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AuthScheme(str, Enum):
    OAUTH2_AUTH_CODE = "oauth2_authorization_code"
    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_credentials"
    OAUTH2_DEVICE_CODE = "oauth2_device_code"
    API_KEY = "api_key"
    PERSONAL_ACCESS_TOKEN = "personal_access_token"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    JWT = "jwt"
    SERVICE_ACCOUNT = "service_account"
    HMAC_SIGNATURE = "hmac_signature"
    SESSION_COOKIE = "session_cookie"
    NO_AUTH = "none"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class AccessClass(str, Enum):
    SELF_SERVE_FREE = "self_serve_free"
    SELF_SERVE_TRIAL = "self_serve_trial"
    SELF_SERVE_PAID = "self_serve_paid"
    SANDBOX_SELF_SERVE_PROD_GATED = "sandbox_self_serve_production_gated"
    ADMIN_GATED = "admin_gated"
    ENTERPRISE_GATED = "enterprise_gated"
    PRODUCTION_APPROVAL = "production_approval"
    PARTNER_GATED = "partner_gated"
    CONTACT_SALES = "contact_sales"
    INVITE_ONLY = "invite_only"
    NO_CREDENTIALS_REQUIRED = "no_credentials_required"
    UNKNOWN = "unknown"

SELF_SERVE = {
    AccessClass.SELF_SERVE_FREE,
    AccessClass.SELF_SERVE_TRIAL,
    AccessClass.SELF_SERVE_PAID,
    AccessClass.NO_CREDENTIALS_REQUIRED,
}
GATED = {
    AccessClass.SANDBOX_SELF_SERVE_PROD_GATED,
    AccessClass.ADMIN_GATED,
    AccessClass.ENTERPRISE_GATED,
    AccessClass.PRODUCTION_APPROVAL,
    AccessClass.PARTNER_GATED,
    AccessClass.CONTACT_SALES,
    AccessClass.INVITE_ONLY,
}


class ApiBreadth(str, Enum):
    BROAD = "broad"
    MEDIUM = "medium"
    NARROW = "narrow"
    NONE = "none"
    UNKNOWN = "unknown"


class McpClass(str, Enum):
    OFFICIAL_VENDOR = "official_vendor_mcp"
    OFFICIAL_COMPOSIO_TOOLKIT = "official_composio_toolkit"
    OFFICIAL_PARTNER = "official_platform_or_partner_mcp"
    COMMUNITY = "reputable_community_mcp"
    NONE_FOUND = "none_found"
    UNKNOWN = "unknown"


class TechnicalVerdict(str, Enum):
    BUILDABLE_NOW = "buildable_now"
    PARTIALLY_BUILDABLE = "partially_buildable"
    NOT_BUILDABLE = "not_buildable"
    UNKNOWN = "unknown"


class Evidence(BaseModel):
    """One evidence link tied to one or more claim fields."""

    claims: list[str] = Field(min_length=1, description="field names this URL supports")
    url: str
    note: str = Field(description="short quote/paraphrase of what the page shows")


class AppResult(BaseModel):
    app_id: int
    name: str
    category: str
    official_domain: str
    description: str
    auth_methods: list[AuthScheme] = Field(min_length=1)
    primary_auth: AuthScheme
    access: AccessClass
    access_notes: str = ""
    api_protocols: list[str] = Field(default_factory=list)  # rest | graphql | websocket | grpc | sdk_only | mcp | none
    api_breadth: ApiBreadth
    supports_webhooks: bool | None = None  # None == unknown
    mcp_status: list[McpClass] = Field(min_length=1)
    mcp_notes: str = ""
    technical_verdict: TechnicalVerdict
    primary_blocker: str | None = None
    confidence: Confidence
    uncertainty_notes: str = ""
    evidence: list[Evidence] = Field(default_factory=list)

    # Filled by the pipeline, not by the research agent:
    final_bucket: str | None = None
    risk_score: int | None = None
    risk_flags: list[str] = Field(default_factory=list)
    verification_status: str = "first_pass"  # first_pass | verified | corrected
    researcher: str = ""
    retrieved_at: str = ""
