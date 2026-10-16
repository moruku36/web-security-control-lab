# LAB-01 worked solution

[English](LAB01.md) | [日本語](LAB01.ja.md)

Read this after completing the [worksheet](../worksheets/LAB01.md) yourself. The solution contains the answers.

The matrix below is the expectation defined by the scanner contract and its unit tests, which use a simulated lab, plus the application source. This document does not record a live run. Real results for a given run are in that run's retained CI evidence and your own local scan.

## Expected matrix (W2, W3, W6)

| Actor requesting `/admin` | VULNERABLE | HARDENED |
| --- | --- | --- |
| Anonymous | 303 to `/login` | 303 to `/login` |
| `alice` (role `user`) | 200 with the admin page | 403 |
| `admin` (role `admin`) | 200 with the admin page | 200 with the admin page |
| `alice`'s old token after logout | `/api/profile` 401; `/admin` 303 to `/login` | same |

Scanner verdicts use the security condition, not the mode. A user reaching the admin page, or an anonymous request reaching it, is FAIL (`USER_ADMIN_ACCESS`, `ANON_ADMIN_ACCESS`). A logged-out token that still authenticates is FAIL (`SESSION_RETAINED`). Any response outside the table is ERROR, not a pass. In VULNERABLE mode LAB-01 is expected to be FAIL with `USER_ADMIN_ACCESS`; in HARDENED mode it is expected to be PASS.

## Cause and repair (W4, W5)

Authentication answers "who is this?" and authorization answers "may they do this?". In VULNERABLE mode the `/admin` handler in `app/main.py` finds the signed-in user but never compares the role, so any authenticated user passes.

Repair B is the correct choice: decide on the server, per request, and deny by default. The existing HARDENED guard is the minimal form:

```python
if user.get("role") != "admin":
    raise HTTPException(status_code=403, detail="Access denied: Administrator role required.")
```

It sits after the "is anyone signed in?" check, which still redirects anonymous requests to `/login`. A (hiding a link), C (browser JavaScript) and D (network address) leave the URL reachable or move the decision to something the requester controls, so they do not enforce the policy. Admin use keeps working because the guard only rejects roles other than `admin`.

## Old-token check (W6)

`GET /logout` clears the cookie and deletes the server-side session record in both modes (`clear_session_cookie` in `app/auth.py` calls `delete_session_record` in `app/db.py`). A replayed token no longer matches a session, so `/api/profile` returns 401 and `/admin` redirects to `/login`. The scanner logs out only a token whose identity it verified, then replays it in a separate client.

## Limitations (W7)

- The check covers the three roles on one route plus logout replay. It does not cover other routes or object-level ownership.
- Zero findings, or six PASS, means only that these local checks found nothing in this exercise. It is not production safety, and the HARDENED mode is still educational: fixed plaintext passwords, `Secure=False` cookies, no session expiry, GET logout and an unauthenticated `/audit-logs` endpoint remain.
- The scanner is an HTTP client, not a browser, and logout via GET has its own CSRF limitations.
- The old-token check covers `alice`'s token; admin-token replay is not tested.
- Completing this exercise does not show independent coding ability, and no educational effect is claimed.

## Transfer: `/reports/{id}` (W8)

Expected checks: require authentication; load the report; compare its owner with the requester (or an explicit sharing rule) before returning it; deny by default with a response that does not reveal whether another user's id exists; apply the same rule to every method on the route. A test matrix: anonymous, owner, a different user, an admin if admins are meant to read all reports, a nonexistent id, and a logged-out token. A remaining gap: such tests cover only the ids and roles you chose.

## Rubric examples

Use these as a guide for self-scoring (0, 1 or 2 per axis), not as a threshold.

- R-POLICY: a 2 states that only `admin` may reach `/admin`, anonymous users go to login, and admins must still succeed.
- R-MECHANISM: a 2 names the missing server-side role decision in the `/admin` handler and rejects A, C and D with reasons.
- R-VERIFICATION: a 2 cites statuses for all four W2 actors in the hardened result, including the allowed admin and the logged-out token.
- R-LIMITATIONS: a 2 names a concrete limit (for example object-level permissions) and applies the policy to `/reports/{id}`.
