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
    for f in report.findings:
        lines.append(f"[{f.severity.value}] {f.lab_id} {f.title}")
        lines.append(f"  {f.description}")

    lines.append("")
    lines.append("Summary")
    lines.append(f"  HIGH: {report.summary['high']}")
    lines.append(f"  MEDIUM: {report.summary['medium']}")
    lines.append(f"  LOW: {report.summary['low']}")

    return "\n".join(lines)


def format_json_report(report: ScanReport) -> str:
    """Format report into machine-readable JSON."""
    return json.dumps(report.to_dict(), indent=2)
