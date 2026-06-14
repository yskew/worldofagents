# Test Report — RFC 0012 MCP / A2A Authorization Server

**Branch:** `raghul-mcp` (independent, off `main`)
**Scope:** MCP authorization guard, `/mcp/tools` + `/mcp/call`, per-agent tool allowlist, MCP console UI.

## Result: PASS — all checks green

### Backend (API)
| Check | Result |
|-------|--------|
| `tests/test_mcp.py` | **8 passed** |
| Full backend suite | **124 passed**, 1 pre-existing warning |
| ruff (mcp + touched modules) | clean |
| Live E2E | catalog; allowlisted tool executes; un-allowlisted → 403; no token → 401; revoked agent → 403 |

### Frontend (UI)
| Check | Result |
|-------|--------|
| Vitest — `McpResult.test.tsx` (3) + `api.test.ts` (2) | **5 passed** |
| `tsc -b` typecheck | clean |
| `vite build` | built (benign three.js chunk-size note) |
| eslint (new/changed) | clean |

### Hygiene
- Migration `f1a2b3c4d5e6` (`tool_allowlist`) — additive, nullable; applied on container start.
- `node_modules`/`dist` gitignored; `package-lock.json` updated for vitest deps.
- Branched off `main` per request.

## Known caveats
- Reference tool execution is a stub (guard is the real deliverable).
- Full MCP transport (JSON-RPC over stdio/SSE) is a follow-up.
- Full-app browser E2E not run (Clerk key needed to mount); component + client + build cover the UI.
