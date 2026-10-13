"""Data models for scanner findings, inspection outcomes and reports."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

SCHEMA_VERSION = "2.0"

LAB_IDS = ("LAB-01", "LAB-02", "LAB-03", "LAB-04", "LAB-05", "LAB-06")
MODES = ("VULNERABLE", "HARDENED")

MAX_EVIDENCE_ITEMS = 16
MAX_STRING_LENGTH = 128

OBSERVATION_ACTORS = ("anonymous", "user", "admin", "user_old_token")
OBSERVATION_ENDPOINTS = (
    "/health",
    "/login",
    "/api/profile",
    "/admin",
    "/logout",
    "/api/diagnostic",
    "/audit-logs",
)
OBSERVATION_REDIRECTS = ("/login", "/profile")

_TARGET_PATTERN = re.compile(r"^https?://[^/@?#\s]+$")
_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class CheckStatus(str, Enum):
    """PASS: control condition met. FAIL: weakness observed. ERROR: inspection incomplete."""

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


class ReasonCode:
    """Central stable reason codes reused by checks, rendering, docs and tests."""

    CONTROL_SATISFIED = "CONTROL_SATISFIED"
    HEALTH_PRECONDITION_FAILED = "HEALTH_PRECONDITION_FAILED"
    MODE_MISMATCH = "MODE_MISMATCH"
    LOGIN_PRECONDITION_FAILED = "LOGIN_PRECONDITION_FAILED"
    UNEXPECTED_RESPONSE = "UNEXPECTED_RESPONSE"
    NETWORK_ERROR = "NETWORK_ERROR"
    COOKIE_ATTRIBUTE_MISSING = "COOKIE_ATTRIBUTE_MISSING"
    HEADER_MISSING = "HEADER_MISSING"
    DIAGNOSTIC_EXPOSURE = "DIAGNOSTIC_EXPOSURE"
    AUTH_FAILURE_NOT_LOGGED = "AUTH_FAILURE_NOT_LOGGED"
    ANON_ADMIN_ACCESS = "ANON_ADMIN_ACCESS"
    USER_ADMIN_ACCESS = "USER_ADMIN_ACCESS"
    SESSION_RETAINED = "SESSION_RETAINED"


# Fixed message templates: check messages never contain response or exception text.
REASON_MESSAGES: Dict[str, str] = {
    ReasonCode.CONTROL_SATISFIED: "Control condition satisfied",
    ReasonCode.HEALTH_PRECONDITION_FAILED: "Health prerequisite could not be established",
    ReasonCode.MODE_MISMATCH: "Reported mode differs from the expected mode",
    ReasonCode.LOGIN_PRECONDITION_FAILED: "Synthetic login prerequisite could not be established",
    ReasonCode.UNEXPECTED_RESPONSE: "Unexpected response was received",
    ReasonCode.NETWORK_ERROR: "Request failed before a response could be inspected",
    ReasonCode.COOKIE_ATTRIBUTE_MISSING: "Session cookie attribute is missing",
    ReasonCode.HEADER_MISSING: "Defensive response header is missing",
    ReasonCode.DIAGNOSTIC_EXPOSURE: "Diagnostic response exposes internal details",
    ReasonCode.AUTH_FAILURE_NOT_LOGGED: "Failed login was not recorded",
    ReasonCode.ANON_ADMIN_ACCESS: "Anonymous request can access the admin page",
    ReasonCode.USER_ADMIN_ACCESS: "Non-admin user can access the admin page",
    ReasonCode.SESSION_RETAINED: "Session token remains valid after logout",
}
REASON_CODES = tuple(REASON_MESSAGES)


@dataclass
class Finding:
    lab_id: str
    title: str
    severity: Severity
    description: str
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lab_id": self.lab_id,
            "title": self.title,
            "severity": self.severity.value,
            "description": self.description,
            "details": self.details,
        }


def validate_observation(obs: Any) -> None:
    """Allowlist validation of a single sanitized observation record."""
    if not isinstance(obs, dict):
        raise ValueError("observation must be an object")
    required = {"actor", "endpoint", "status"}
    keys = set(obs)
    if not required <= keys or not keys <= required | {"redirect"}:
        raise ValueError("observation has missing or unknown keys")
    if obs["actor"] not in OBSERVATION_ACTORS:
        raise ValueError("observation actor is not allowlisted")
    if obs["endpoint"] not in OBSERVATION_ENDPOINTS:
        raise ValueError("observation endpoint is not allowlisted")
    status = obs["status"]
    if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
        raise ValueError("observation status must be an integer from 100 to 599")
    if "redirect" in obs and obs["redirect"] not in OBSERVATION_REDIRECTS:
        raise ValueError("observation redirect is not allowlisted")


def validate_evidence(evidence: Any) -> None:
    """Allowlist validation of check evidence; unknown keys and free text are rejected."""
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")
    required = {"observations", "incomplete", "reasons"}
    keys = set(evidence)
    if not required <= keys or not keys <= required | {"verified", "mode"}:
        raise ValueError("evidence has missing or unknown keys")

    observations = evidence["observations"]
    if not isinstance(observations, list) or len(observations) > MAX_EVIDENCE_ITEMS:
        raise ValueError("observations must be a list of at most 16 records")
    for obs in observations:
        validate_observation(obs)

    if not isinstance(evidence["incomplete"], bool):
        raise ValueError("incomplete must be a boolean")
    if "verified" in evidence and not isinstance(evidence["verified"], bool):
        raise ValueError("verified must be a boolean")
    if "mode" in evidence and evidence["mode"] not in (*MODES, None):
        raise ValueError("mode must be VULNERABLE, HARDENED or null")

    reasons = evidence["reasons"]
    if not isinstance(reasons, list) or len(reasons) > MAX_EVIDENCE_ITEMS:
        raise ValueError("reasons must be a list of at most 16 reason codes")
    for reason in reasons:
        if not isinstance(reason, str) or len(reason) > MAX_STRING_LENGTH:
            raise ValueError("reason must be a short string")
        if reason not in REASON_CODES:
            raise ValueError("reason is not a known reason code")


@dataclass
class CheckResult:
    lab_id: str
    status: CheckStatus
    reason_code: str
    evidence: Dict[str, Any]
    message: str = ""

    def __post_init__(self) -> None:
        if not self.message:
            self.message = REASON_MESSAGES.get(self.reason_code, "")
        self.validate()

    def validate(self) -> None:
        if self.lab_id not in LAB_IDS:
            raise ValueError("unknown lab id")
        if not isinstance(self.status, CheckStatus):
            raise ValueError("status must be a CheckStatus")
        if self.reason_code not in REASON_CODES:
            raise ValueError("unknown reason code")
        if self.message != REASON_MESSAGES[self.reason_code]:
            raise ValueError("message must be the fixed template for the reason code")
        validate_evidence(self.evidence)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lab_id": self.lab_id,
            "status": self.status.value,
            "reason_code": self.reason_code,
            "message": self.message,
            "evidence": self.evidence,
        }


def utc_timestamp(clock: Optional[Callable[[], datetime]] = None) -> str:
    now = clock() if clock else datetime.now(timezone.utc)
    return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_status_summary(checks: List[CheckResult]) -> Dict[str, int]:
    summary = {"pass": 0, "fail": 0, "error": 0}
    for check in checks:
        summary[check.status.value.lower()] += 1
    return summary


@dataclass
class ScanReport:
    target: str
    findings: List[Finding]
    summary: Dict[str, int]
    mode: Optional[str] = None
    generated_at: str = field(default_factory=utc_timestamp)
    checks: List[CheckResult] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    @property
    def status_summary(self) -> Dict[str, int]:
        return compute_status_summary(self.checks)

    @property
    def has_errors(self) -> bool:
        return any(c.status == CheckStatus.ERROR for c in self.checks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "target": self.target,
            "mode": self.mode,
            "generated_at": self.generated_at,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "checks": [c.to_dict() for c in self.checks],
            "status_summary": self.status_summary,
        }


class InspectionError(Exception):
    """Raised by the legacy run_all_checks wrapper when inspection was incomplete.

    The sanitized full report is attached; the message is a fixed string.
    """

    def __init__(self, report: ScanReport) -> None:
        super().__init__("Inspection incomplete: at least one check reported ERROR")
        self.report = report


def build_error_report(
    target: str,
    reason_code: str = ReasonCode.HEALTH_PRECONDITION_FAILED,
    mode: Optional[str] = None,
    clock: Optional[Callable[[], datetime]] = None,
    observations: Optional[List[Dict[str, Any]]] = None,
) -> ScanReport:
    """Build a report with six ERROR checks and no findings (never an empty success)."""
    checks = [
        CheckResult(
            lab_id=lab_id,
            status=CheckStatus.ERROR,
            reason_code=reason_code,
            evidence={
                "observations": [dict(o) for o in (observations or [])],
                "incomplete": True,
                "reasons": [],
                "mode": mode,
            },
        )
        for lab_id in LAB_IDS
    ]
    return ScanReport(
        target=target,
        findings=[],
        summary={"high": 0, "medium": 0, "low": 0},
        mode=mode,
        generated_at=utc_timestamp(clock),
        checks=checks,
    )


def validate_report(data: Any) -> None:
    """Strict allowlist validation of a schema 2.0 report dict. Raises ValueError."""
    if not isinstance(data, dict):
        raise ValueError("report must be an object")
    expected_keys = {
        "schema_version",
        "target",
        "mode",
        "generated_at",
        "findings",
        "summary",
        "checks",
        "status_summary",
    }
    if set(data) != expected_keys:
        raise ValueError("report has missing or unknown keys")
    if data["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported schema_version")
    target = data["target"]
    if not isinstance(target, str) or len(target) > MAX_STRING_LENGTH:
        raise ValueError("target must be a short string")
    if not _TARGET_PATTERN.match(target):
        raise ValueError("target must be scheme://host[:port] only")
    if data["mode"] not in (*MODES, None):
        raise ValueError("mode must be VULNERABLE, HARDENED or null")
    generated_at = data["generated_at"]
    if not isinstance(generated_at, str) or not _TIMESTAMP_PATTERN.match(generated_at):
        raise ValueError("generated_at must be UTC ISO 8601")

    severities = {s.value for s in Severity}
    finding_keys = {"lab_id", "title", "severity", "description", "details"}
    findings = data["findings"]
    if not isinstance(findings, list):
        raise ValueError("findings must be a list")
    seen = set()
    for f in findings:
        if not isinstance(f, dict) or set(f) != finding_keys:
            raise ValueError("finding has missing or unknown keys")
        if f["lab_id"] not in LAB_IDS or f["lab_id"] in seen:
            raise ValueError("finding lab id is unknown or duplicated")
        seen.add(f["lab_id"])
        if f["severity"] not in severities:
            raise ValueError("finding severity is unknown")
        for key in ("title", "description", "details"):
            if not isinstance(f[key], str):
                raise ValueError("finding text fields must be strings")

    summary = data["summary"]
    if not isinstance(summary, dict) or set(summary) != {"high", "medium", "low"}:
        raise ValueError("summary must have exactly high/medium/low")
    for sev in ("high", "medium", "low"):
        if summary[sev] != sum(1 for f in findings if f["severity"] == sev.upper()):
            raise ValueError("summary does not match findings")

    checks = data["checks"]
    if not isinstance(checks, list) or [
        c.get("lab_id") if isinstance(c, dict) else None for c in checks
    ] != list(LAB_IDS):
        raise ValueError("checks must contain the six labs in order")
    counts = {"pass": 0, "fail": 0, "error": 0}
    check_keys = {"lab_id", "status", "reason_code", "message", "evidence"}
    for c in checks:
        if set(c) != check_keys:
            raise ValueError("check has missing or unknown keys")
        CheckResult(
            lab_id=c["lab_id"],
            status=CheckStatus(c["status"]),
            reason_code=c["reason_code"],
            message=c["message"],
            evidence=c["evidence"],
        )
        counts[c["status"].lower()] += 1
    if data["status_summary"] != counts:
        raise ValueError("status_summary does not match checks")
