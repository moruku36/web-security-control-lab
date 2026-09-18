# Security Policy

## Educational Purpose and Scope

`web-security-control-lab` is an intentionally vulnerable educational environment designed **strictly for local security training, certification study, and DevSecOps learning**.

### Permitted Targets & Use
- Only local testing targets (`localhost`, `127.0.0.1`, `::1`, or isolated local Docker networks) are supported and permitted.
- The built-in scanner is strictly hardcoded and constrained to refuse any non-local, public, or remote IP/hostname (Fail-Closed design).

### Strictly Prohibited
- Deploying this application to any public Internet-facing environment or shared server without isolation.
- Utilizing any lab components or scanning scripts against third-party systems, networks, or endpoints without explicit written authorization.
- Modifying the scanner to target external networks or adding exploit/weaponized payloads.

### Reporting Vulnerabilities in Lab Code
If you find an unintentional vulnerability outside the designated educational lab weaknesses (LAB-01 through LAB-06), please open a security advisory or contact the repository maintainers directly.
Do NOT submit real credentials, tokens, or sensitive user data to this repository.
