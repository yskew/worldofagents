# RFC 0007 — Production Hardening

- **Status:** Implemented
- **Area:** `app/main.py`, `app/auth/jwt_issuer.py`, `app/auth/clerk.py`, `app/ratelimit.py`, `app/config.py`

---

## 1. Why

`ANALYSIS.md` flagged several production-readiness gaps that are independent of
the scoring work. This RFC closes the four highest-impact ones. They are gated by
a single new `ENVIRONMENT` setting (`development` default, `production` to
harden), so local development is unchanged.

## 2. Fixes

### F — JWT keys fail loud (`jwt_issuer.py`)
Previously, if `RSA_*_PEM` were missing or failed to parse, the issuer silently
generated a fresh keypair on every startup — invalidating all previously issued
tokens and breaking JWKS verification. Now:
- Keys provided but unparseable → **raise** (never silently regenerate).
- No keys + `production` → **raise** (keys are required).
- No keys + `development` → ephemeral keypair **with a warning log**.

### G — Dev-auth bypass gated (`clerk.py`)
The demo-user fallback (and unsigned-token decode path) were reachable whenever
Clerk looked unconfigured — a risk if shipped. Now:
- `_is_dev_mode()` returns False in production regardless of Clerk config, so the
  demo user is never issued in production.
- If a token is presented but no JWKS client is available, production **rejects
  it (401)** instead of decoding without signature verification.

### H — Rate limiting (`ratelimit.py`)
The compute-heavy open endpoints (`/verify`, `/compare`, `/similar`) had no
limit. Added a per-IP sliding-window limiter as a FastAPI dependency
(`RATE_LIMIT_ENABLED`, `RATE_LIMIT_PER_MINUTE`, default 60/min). In-memory and
per-process — fine for a single instance; a multi-instance deployment should back
it with a shared store (Redis). Returns 429 with `Retry-After`.

### I — CORS (`main.py`)
`allow_origins=["*"]` with `allow_credentials=True` is a spec violation and a
real vulnerability. Now origins come from `ALLOWED_ORIGINS` (allow-list), and
credentials are only enabled when origins are explicit (not `*`).

## 3. Config added

| Setting | Default | Purpose |
|---------|---------|---------|
| `ENVIRONMENT` | `development` | gates F/G hardening |
| `ALLOWED_ORIGINS` | `localhost:5173,localhost:8000` | CORS allow-list |
| `RATE_LIMIT_ENABLED` | `true` | toggle the limiter |
| `RATE_LIMIT_PER_MINUTE` | `60` | per-IP budget |

## 4. Tests

`tests/test_hardening.py` (11): JWT raises in production / generates in dev /
rejects bad keys; dev-mode off in production; unsigned decode blocked in
production; no demo user in production (`/agents` → 401); CORS origin parsing;
rate limit returns 429 past the budget and is unlimited when disabled.

The suite disables the limiter globally (one line in `conftest.py`) since many
tests share one client IP; the hardening test re-enables it locally. Full suite:
181 passed.

## 5. Notes / future

- The in-memory limiter is per-process; move to Redis for horizontal scaling.
- Consider per-route limits (verify vs compare) and authenticated-user keys.
- A production deploy must set `ENVIRONMENT=production`, real `RSA_*_PEM`,
  `CLERK_JWKS_URL`, and an explicit `ALLOWED_ORIGINS`.
