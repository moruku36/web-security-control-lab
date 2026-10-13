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

The [research and improvement roadmap](docs/SURVEY_ROADMAP.md) ([日本語](docs/SURVEY_ROADMAP.ja.md)) separates the implemented baseline from proposed changes and defines measurable learning objectives: predict, observe, explain the cause, repair, reverify, and explain the remaining limits. Zero findings for the six local checks is not evidence of production security. The proposed changes and educational effectiveness have not yet been validated.

The [Japanese guide](README.ja.md) retains the complete original setup instructions, configuration, examples, project status, and limitations. Supporting documents keep their existing language.
