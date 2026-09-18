"""Data models for scanner findings and reports."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


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


@dataclass
class ScanReport:
    target: str
    findings: List[Finding]
    summary: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
        }
