# LAB-01 worksheet: authentication versus authorization

[English](LAB01.md) | [日本語](LAB01.ja.md)

Local, synthetic exercise. Use only the lab application on your own machine and the fixture accounts `alice` / `user` and `admin` / `admin`. This worksheet gives no answers; the separate [solution](../solutions/LAB01.md) is for after you have written your own. Completing it is a formative practice, not a validated certificate of ability, and it is not independent coding proficiency.

Keep this worksheet and your answers as a local learning record. Do not attach it to scan artifacts, and do not paste cookie values, session tokens or real identities anywhere.

## W1. Scope and setup

Start the application on `127.0.0.1` (see the [lab guide](../LAB_GUIDE.md)). Open `/health` and write down the reported `mode`. Confirm the target is only a local address.

## W2. Predict before you run

Fill in the expected result of requesting `/admin` for each actor in each mode, before any observation. Use the status code (and where it goes, if it redirects).

| Actor requesting `/admin` | VULNERABLE (your prediction) | HARDENED (your prediction) |
| --- | --- | --- |
| Anonymous | | |
| `alice` (role `user`) | | |
| `admin` (role `admin`) | | |
| `alice` reusing her session token after logging out | | |

## W3. Observe

Run the scanner against the VULNERABLE application and read only the LAB-01 check:

```bash
security-lab scan http://127.0.0.1:8000 --format json --expected-mode VULNERABLE
```

Copy the sanitized `observations` (actor, endpoint, status, redirect) for LAB-01. Record the check status and `reason_code`. Note whether your W2 predictions matched, and where they did not.

## W4. Explain the cause

1. In your own words, what is the difference between authentication and authorization?
2. Which request proved who the user was, and which decision was missing?
3. Name the file and function where the role decision belongs.

## W5. Choose a repair and justify it

Pick one approach and explain why, including why legitimate admin use keeps working.

- A. Hide the admin link from non-admin users in the page.
- B. Check the signed-in user's role on the server before serving the admin page, and deny otherwise.
- C. Check the role in browser JavaScript.
- D. Restrict the admin page by the requester's network address.

## W6. Reverify

Repeat the actors from W2 against the repaired or HARDENED application. Record denied cases, the allowed admin case, and the logged-out token case. Explain why a logged-out token must fail.

## W7. Limits

State at least one thing this check does not establish. Consider: other routes, object-level permissions, what zero findings means, and what the HTTP client cannot show.

## W8. Transfer (paper only)

A new, invented route `GET /reports/{id}` returns a report that belongs to one user. Without writing or running code, list the checks the server must make, what a test matrix would contain, and one thing your test would still not cover.

## Optional hints

Use them in order and only when stuck. Record the highest hint level you used.

- [H1] Identity is not permission.
- [H2] Inspect the admin handler.
- [H3] Verify anonymous, user and admin, and check legitimate use too.

Highest hint level used: ____

## Formative rubric

Score each axis 0 (absent or incorrect), 1 (partly supported) or 2 (correct and backed by your recorded evidence). There is no pass threshold. Hint level and completion time are tracked separately, and technical scan results are not learning scores.

| ID | Axis | Question | Evidence criterion |
| --- | --- | --- | --- |
| R-POLICY | Policy | Which actors should be allowed, and why? | W2 matrix states permitted and denied actors with reasons, including legitimate admin use |
| R-MECHANISM | Mechanism | What was the cause, and why does your repair address it? | W4/W5 name the missing decision and where it belongs |
| R-VERIFICATION | Verification | How did you show denial and legitimate success? | W3/W6 cite sanitized statuses for anonymous, user, admin and logged-out token |
| R-LIMITATIONS | Limitations | What does this not show? | W7/W8 state a remaining limitation and apply the policy to the paper scenario |
