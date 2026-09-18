"""Unit tests for scanner reporting and data models."""

import json

from scanner.models import Finding, ScanReport, Severity
from scanner.reporter import compute_summary, format_json_report, format_text_report


def test_severity_and_summary_calculation():
    findings = [
        Finding(
            lab_id="LAB-01",
            title="Broken Access Control",
            severity=Severity.HIGH,
            description="High finding",
        ),
        Finding(
            lab_id="LAB-02",
            title="Session Cookie",
            severity=Severity.MEDIUM,
            description="Medium finding 1",
        ),
        Finding(
            lab_id="LAB-03",
            title="Session Cookie",
            severity=Severity.MEDIUM,
            description="Medium finding 2",
        ),
        Finding(
            lab_id="LAB-05",
            title="Information Disclosure",
            severity=Severity.LOW,
            description="Low finding",
        ),
    ]

    summary = compute_summary(findings)
    assert summary["high"] == 1
    assert summary["medium"] == 2
    assert summary["low"] == 1


def test_json_and_text_formatting():
    findings = [
        Finding(
            lab_id="LAB-01",
            title="Broken Access Control",
            severity=Severity.HIGH,
            description="/admin is accessible by a non-admin user",
        )
    ]
    summary = compute_summary(findings)
    report = ScanReport(target="http://127.0.0.1:8000", findings=findings, summary=summary)

    text_output = format_text_report(report)
    assert "[HIGH] LAB-01 Broken Access Control" in text_output
    assert "HIGH: 1" in text_output

    json_output = format_json_report(report)
    parsed = json.loads(json_output)
    assert parsed["target"] == "http://127.0.0.1:8000"
    assert parsed["summary"]["high"] == 1
    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["lab_id"] == "LAB-01"
