# RFC 0009 — Token-Exchange Broker + OIDC Federation

- **Status:** Implemented (spike)
- **Area:** `POST /oauth/token`, `app/auth/providers.py`, `app/auth/jwt_issuer.py`, `agents.allowed_scopes`
- **Depends on:** RFC 0001-0008 (verification produces the actor_token)
- **Constraint:** Clerk's existing auth path is untouched.

---

## 1. Why

Until now `/verify` issued a JWT no downstream system consumes. The value of
behavioral verification is only realized when it **gates real authorization**.
This RFC turns the project into an RFC 8693 **token-exchange broker**: it takes
the human's IdP identity plus the agent's verification result and mints a
**scoped, short-lived, audience-bound** downstream token a relying party
(GitHub, Snowflake, an MCP server) can accept. That puts behavioral attestation
in the critical path of every agent action.

This is also where IdP integration belongs: federation happens at the broker
(validating the human's `subject_token`), not as "another login button."

## 2. Clerk-preserving design

Clerk remains the default and is **not modified**. A new provider registry
(`app/auth/providers.py`) validates the broker's `subject_token`:

- `ClerkProvider` reuses the existing `_decode_clerk_token` **read-only**.
- `OIDCProvider` validates any standards OIDC IdP (Okta / Entra / Auth0 / Google)
  against its JWKS, configured via `OIDC_PROVIDERS_JSON` — added *alongside*
  Clerk, never replacing it.

`get_current_human` and `clerk.py` are unchanged; existing auth flows are
unaffected.

## 3. The exchange (RFC 8693)

`POST /oauth/token` (form-encoded, `grant_type=...:token-exchange`):

| Param | Meaning |
|-------|---------|
| `subject_token` | the human's IdP token (who is responsible) |
| `subject_token_provider` | which registered provider validates it (`clerk` default) |
| `actor_token` | our verification JWT (proof the agent passed behavioral checks) |
| `audience` | the downstream resource the token is for |
| `scope` | requested scopes (space-separated) |

Server logic:
1. Validate `subject_token` via the provider registry → human subject.
2. Validate `actor_token` against our own JWKS → `sub` (owner) + `act.sub` (agent).
   It exists only because the agent passed `/verify` or `/verify/active`.
3. **Ownership:** `subject.sub` must equal the actor's `sub`, and the agent's
   stored owner must match — the human presenting must own the verified agent.
4. **Least privilege:** requested scopes must be a subset of the agent's
   `allowed_scopes` (set via `POST /agents/{id}/scopes`).
5. Mint a delegated token: `sub`=human, `act.sub`=agent, `aud`, `scope`, short
   `exp` (`DOWNSTREAM_TOKEN_EXPIRY_SECONDS`, default 300s).

Returns the RFC 8693 response (`access_token`, `issued_token_type`,
`token_type`, `expires_in`, `scope`).

## 4. Demonstrated

Live: exchange succeeds → `sub=demo_user_001, act.sub=<agent>,
aud=https://api.github.com, scope=repo:read, exp=300s`; a disallowed scope →
400 `invalid_scope`; a different human presenting the agent → 403
`invalid_grant`. Tests in `tests/test_token_exchange.py` (8) cover the registry
(Clerk + mocked OIDC) and the broker flow + rejections. Full suite: 199 passed.

## 5. Limitations & next steps

- **Cross-provider account linking.** The happy path matches the human across
  `subject_token` and `actor_token` by identifier; an external OIDC human owning
  a Clerk-registered agent needs an account-linking step (an additive OIDC
  registration path alongside Clerk — does not modify Clerk).
- **DPoP / sender-constraint** the downstream token so it can't be replayed by a
  relying party.
- **mTLS / resource indicators** per RFC 8707 for fine-grained audience binding.
- This naturally feeds RFC-future **CAEP**: a revoked/anomalous behavioral
  result should emit a Shared-Signals event that downstream consumers honor.
