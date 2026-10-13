"""Scanner output formatting and reporting."""

import json
from typing import Dict, List

from scanner.models import Finding, ScanReport, Severity


def compute_summary(findings: List[Finding]) -> Dict[str, int]:
    """Calculate summary counts by severity level."""
    summary = {
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    for f in findings:
        if f.severity == Severity.HIGH:
            summary["high"] += 1
        elif f.severity == Severity.MEDIUM:
            summary["medium"] += 1
        elif f.severity == Severity.LOW:
            summary["low"] += 1
    return summary


def format_text_report(report: ScanReport) -> str:
    """Format report into human-readable console text."""
    lines = ["Web Security Control Lab"]
    lines.append(f"Target: {report.target} (mode reported by target: {report.mode or 'unknown'})")
    lines.append(
        "Scope: six local educational checks only; not a production or compliance assessment."
    )
    for f in report.findings:
        lines.append(f"[{f.severity.value}] {f.lab_id} {f.title}")
        lines.append(f"  {f.description}")

    if report.checks:
        lines.append("")
        lines.append("Checks")
        for c in report.checks:
            lines.append(f"  {c.lab_id} {c.status.value} {c.reason_code}")

    lines.append("")
    lines.append("Summary")
    lines.append(f"  HIGH: {report.summary['high']}")
    lines.append(f"  MEDIUM: {report.summary['medium']}")
    lines.append(f"  LOW: {report.summary['low']}")

    if report.checks:
        status = report.status_summary
        lines.append("Status")
        lines.append(f"  PASS: {status['pass']}")
        lines.append(f"  FAIL: {status['fail']}")
        lines.append(f"  ERROR: {status['error']}")
        if report.has_errors:
            lines.append(
                "Inspection incomplete: ERROR is not a pass, and zero findings do not mean "
                "the controls are safe. Exit status 3."
            )
        else:
            lines.append(
                "Inspection complete. Observed weaknesses are reported as FAIL; exit status 0."
            )

    return "\n".join(lines)


def format_json_report(report: ScanReport) -> str:
    """Format report into machine-readable JSON."""
    return json.dumps(report.to_dict(), indent=2)
