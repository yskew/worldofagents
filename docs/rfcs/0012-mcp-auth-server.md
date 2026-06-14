# RFC 0012 — MCP / A2A Reference Authorization Server

- **Status:** Implemented (spike)
- **Area:** `app/services/mcp.py`, `app/api/mcp.py`, `agents.tool_allowlist`, MCP UI
- **Base:** branched off `main` (independent PR).

---

## 1. Why

The thesis notes ~2,000 MCP servers with **zero authentication**. That is not a
market with an incumbent to integrate with — it is a greenfield to *own*. This
RFC adds a reference MCP authorization layer: an MCP server / proxy gates every
tool call on (a) a valid behavioral-attestation token issued by us and (b) a
per-agent tool allowlist. Behavioral identity becomes the gate on what an agent
is allowed to *do*, not just who it is.

## 2. Design

- **`services/mcp.authorize(token, tool, db)`** — the guard. Verifies the bearer
  token against our JWKS (RS256, issuer-checked), extracts the agent (`act.sub`)
  and human (`sub`), confirms the agent exists and is not revoked, and checks the
  tool is in the agent's allowlist. Returns a `Decision` (allow + principal, or a
  deny with status/reason). A real MCP server calls this before dispatch.
- **`agents.tool_allowlist`** (JSONB, nullable; migration `f1a2b3c4d5e6`) — the
  tools an agent may call; set via authed `POST /agents/{id}/tools`.
- **Endpoints:**
  - `GET /mcp/tools` — the reference tool catalog.
  - `POST /mcp/call` — `Authorization: Bearer <attestation token>` + `{tool,
    arguments}`; guarded; executes a reference stub on allow, else 401/403/404.
- **UI:** an `Mcp` console — pick a tool, paste an attestation token, call, and
  see the allow/deny decision (`McpResult`).

## 3. Authorization outcomes

| Condition | Result |
|-----------|--------|
| Valid token + tool in allowlist | 200, executed (echoes args; principal returned) |
| Tool not in allowlist | 403 `tool_not_authorized` |
| Unknown tool | 404 |
| Missing / malformed / bad-signature token | 401 |
| Agent revoked or not found | 403 `agent_revoked` |

## 4. Demonstrated

Live: list tools; allowlist `search,edit_file`; obtain an attestation token from
`/verify`; `edit_file` → executed; `deploy` (not allowlisted) → 403; no token →
401; after revoke → 403. SETs/tokens verify against the existing JWKS.

## 5. Testing (API + UI)

- **API:** `tests/test_mcp.py` (8) — catalog, allow, allowlist deny, unknown
  tool, missing/invalid token, revoked agent, unknown-agent token. Full backend
  suite **124 passed**.
- **UI:** Vitest `McpResult.test.tsx` (3) + `api.test.ts` (2) = **5 passed**;
  `tsc -b` + `vite build` + eslint clean. (Re-establishes the Vitest harness.)

## 6. Limitations & next steps

- Reference tool execution is a stub; a production proxy dispatches to real MCP
  tools after the guard.
- Tool→scope mapping: on merge with the RFC 0009 broker, the allowlist can be
  derived from the delegated token's scopes instead of a separate column.
- Full MCP transport (JSON-RPC over stdio/SSE) and A2A handshake are follow-ups;
  this implements the authorization decision, which is the novel part.
- Built on the baseline (V1) engine; composes with V2 on merge.
