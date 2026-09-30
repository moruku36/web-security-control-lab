# Web Security Control Lab

[English](README.md) | [日本語](README.ja.md)

A localhost-only educational lab for observing vulnerable web behavior, detecting security issues, explaining causes, applying remediation, and verifying the hardened result.

## Learning cycle

Observe the vulnerable application, run the scanner, explain each finding, remediate the control, and rescan the hardened result. The FastAPI application and SQLite test data provide an intentionally small environment for learning authentication, authorization, and web-configuration controls.

The scanner validates its localhost-only boundary. Use `docker-compose.yml`, the application source, scanner source, and `docs/` together with the Japanese run guide. This repository is intended for local education and verification.


## Contents

- [SECURITY.md](SECURITY.md)
- [app/](app)
- [docs/](docs)
- [factory/](factory)
- [scanner/](scanner)
- [tests/](tests)

## Detailed documentation

The [Japanese guide](README.ja.md) retains the complete original setup instructions, configuration, examples, project status, and limitations. Supporting documents keep their existing language.
