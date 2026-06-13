# RFC 0011 — Shared Signals / CAEP Risk Emitter

- **Status:** Implemented (spike)
- **Area:** `app/services/ssf.py`, `app/api/ssf.py`, verify + revoke hooks, Signals UI
- **Base:** branched off `main` (independent PR).

---

## 1. Why

The contrarian framing of the integration story: don't join the IdP login stack
as another button — become the **agent-behavior risk signal the IdP stack
subscribes to**. OpenID's **Shared Signals Framework (SSF)** + **CAEP**
(Continuous Access Evaluation) is the standard for exactly this: a transmitter
emits **Security Event Tokens (SETs)** that receivers (Okta, Entra, Google)
consume to re-evaluate access in real time.

When an agent's behavioral check fails or an agent is revoked, that is a risk
event the whole ecosystem should be able to act on. This RFC makes the project a
standards-compliant SSF/CAEP **transmitter**.

## 2. What was built

- **`services/ssf.py`** — builds signed SETs (RFC 8417) via the JWT issuer,
  maintains a delivery queue, supports poll (RFC 8936) and best-effort push to
  webhook receivers. Two event types:
  - `…/caep/event-type/session-revoked` (standard CAEP) on agent revocation,
  - `https://worldofagents.dev/caep/event-type/behavioral-anomaly` (namespaced,
    since no standard CAEP type fits agent behavioral drift) on a failed check.
  Subjects use RFC 9493 identifiers (email or opaque).
- **`jwt_issuer.issue_set`** — signs SETs with `typ: secevent+jwt`.
- **Endpoints:**
  - `GET /.well-known/ssf-configuration` — transmitter metadata (issuer,
    jwks_uri, delivery methods, supported events).
  - `POST /ssf/poll` — RFC 8936 poll delivery with acknowledgement.
- **Hooks:** `/verify` emits a behavioral-anomaly SET on failure (not on pass);
  agent revocation emits session-revoked.
- **UI:** a `Signals` page (poll + ack) rendering decoded risk events via
  `SignalsFeed`; client-side SET decode in `api.ts`.

## 3. Demonstrated

Live: `ssf-configuration` advertises both events; a divergent `/verify` →
queued `behavioral-anomaly` SET; revoke → `session-revoked` SET; ack drains the
queue. Receivers verify SET signatures against the existing JWKS.

## 4. Testing (API + UI)

- **API:** `tests/test_ssf.py` (9) — SET signing/decoding, CAEP event shape +
  RFC 9493 subjects, poll/ack, disabled no-op, config endpoint, and the
  verify-fail / verify-pass / revoke hooks. Full backend suite **125 passed**.
- **UI:** Vitest — `SignalsFeed.test.tsx` (2) + `api.test.ts` (2, decode + poll)
  = **4 passed**; `tsc -b` + `vite build` + eslint clean. (Re-establishes the
  Vitest harness on this branch.)

## 5. Limitations & next steps

- **In-memory queue** (per-process). Multi-instance needs a shared store (Redis).
- **Stream management API** (RFC 8935 SSF stream config/verification endpoints,
  receiver registration) is stubbed via static config; full stream lifecycle is
  a follow-up.
- **Richer signals** once continuous mid-session attestation lands: emit on live
  drift, not only at discrete `/verify` calls — that is the natural next item.
- Built on the baseline (V1) engine; on merge it composes with the V2 engine for
  higher-quality risk scoring.
