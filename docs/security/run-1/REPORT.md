# Security audit, run 1 (2026-11-25)

Scope: this repository (FastAPI backend + React UI), a local single-teacher app on 127.0.0.1. Method: source review plus local, non-destructive harnesses run against our own code. No external systems were probed. Single run, done inline without parallel sub-agents, so coverage is partial; another run is recommended.

## Findings (all fixed in this change, with regression tests in `tests/test_security.py`)

| # | Severity | Finding | Confirmed by | Fix |
|---|---|---|---|---|
| 1 | **HIGH** (remote code execution on browsers without Local Network Access protection) | **DNS rebinding + PowerShell injection.** The server accepted any `Host` header, so an attacker's web page rebound to 127.0.0.1 could call the whole API same-origin: read unredacted student identity crops and IDs, and `POST /api/batches/{id}/scan {"device":"wia","target":...}`. The WIA device ID was spliced into a PowerShell script after only `'` was stripped. PowerShell also treats curly quotes (U+2019) as string delimiters, so the ID broke out of the string. | A foreign `Host` returned 200; the payload `x’; Write-Output INJECTED; ’` executed (`INJECTED` printed) | Host allowlist (`TrustedHostMiddleware`: localhost, 127.0.0.1, ::1, plus `SCANNER_ALLOWED_HOSTS`); WIA inputs passed as environment variables, never as script text |
| 2 | **MEDIUM** | **CSRF: any website could replace the answer key or syllabus.** `text_or_file` parsed JSON whatever the content type, so a cross-site `text/plain` POST (a "simple" request, no preflight) overwrote the key and silently changed every grade. Multipart uploads and pause/finish could be driven the same way. | Cross-site `text/plain` POST changed the key from B to A | Writes are refused when `Origin` does not match `Host` or when `Sec-Fetch-Site: cross-site`; the JSON branch requires `application/json` (else 415) |

## Hardening notes (not exploitable after the fixes above)
- eSCL `check`/`scan` fetch a teacher-supplied address (SSRF shape). Only the local user can reach it now. Could be limited to private and link-local ranges.
- No upload size or pixel limits (PIL bomb guard only); a local-only denial-of-service.
- SANE device names starting with `-` are now rejected.
- eSCL over https skips certificate checks (printers use self-signed certificates); LAN only, and only scan settings are sent.
- The identity crop in Review shows the handwritten name even when "Show student names" is off (local display is allowed by SPEC 10).

## What is solid
Parameterized SQL everywhere (f-string fragments are constants or model field names). SPA file serving is confined to `frontend/dist`. Stored file names come from a sequence number. One redaction choke point feeds every cloud payload (G7: 0 identity pixels, 0 names).
