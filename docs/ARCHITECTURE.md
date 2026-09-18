# Architecture Overview

`web-security-control-lab` is structured into three decoupled layers:
1. **Target Web Application (`app/`)**: FastAPI-based local educational web service with configurable state (`VULNERABLE` / `HARDENED`).
2. **Security Control Scanner (`scanner/`)**: Python CLI tool enforcing a strict localhost-only safety boundary (Fail-Closed).
3. **Governance & Verification Layer (`factory/` and `ai-engineering-factory`)**: Declarative machine-readable task manifests and reproducible test/lint gates.

## System Interaction Diagram

```mermaid
flowchart TD
    subgraph Browser / User / Automated Test
        Client["Browser / pytest / curl"]
    end

    subgraph "Web Security Control Lab App (:8000)"
        App["FastAPI Core Engine"]
        Auth["Session & Auth Module"]
        DB[("SQLite Fixtures")]
        Headers["Defensive Headers Middleware"]
        Diagnostic["Diagnostic & Error Endpoint"]

        App --> Auth
        App --> DB
        App --> Headers
        App --> Diagnostic
    end

    subgraph "Security Scanner CLI"
        TargetVal{"Target Safety Validator<br/>(localhost only)"}
        ScanEngine["Checks Engine (LAB-01..06)"]
        Reporter["Reporter (Text / JSON)"]

        TargetVal -->|Allowed| ScanEngine
        TargetVal -->|Disallowed| Refuse["Fail-Closed Refusal (exit code 2)"]
        ScanEngine --> Reporter
    end

    subgraph "AI Engineering Factory (moruku36/ai-engineering-factory)"
        Manifest["factory/tasks/wscl-*.yaml"]
        Verifier["Independent Verifier (ruff, pytest, scanner)"]
        Bundle["Evidence Bundle & Digest"]

        Manifest --> Verifier --> Bundle
    end

    Client -->|HTTP Requests| App
    ScanEngine -->|Local HTTP Audits| App
```

## Security Boundary & Fail-Closed Guardrail
The scanner (`scanner/target.py`) explicitly permits only:
- `http://localhost:<port>`
- `http://127.0.0.1:<port>`
- `http://[::1]:<port>`
- `http://web-security-control-lab-app:<port>`

Any public IP, remote host, or domain outside this set causes immediate termination without issuing any network requests.
