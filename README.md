# World of Agents

**The missing identity layer for AI agents.**

Every AI agent acting in the world today does so with either no identity at all, or a stolen one. World of Agents is an open platform that lets any agent prove which human owns it, verify its behavioral identity, and act on behalf of its owner with full attribution.

![World of Agents](promo/demo.gif)

---

## What it does

- **Register** agents with a behavioral signature extracted from their trajectory
- **Verify** agent identity using cryptographic keys + behavioral comparison
- **Compare** two agent trajectories to measure behavioral similarity
- **Issue delegated JWTs** with `act.sub` claims (RFC 8693 pattern) — the agent acts as the human, with attribution
- **Serve a public JWKS** endpoint so downstream systems can verify tokens

## How it works

```
Human registers agent → submits trajectory → system extracts 7 behavioral features
                                            → generates bcrypt key (shown once)
                                            → stores signature + 256-dim pgvector embedding

Agent verifies identity → presents key + trajectory → crypto check (bcrypt)
                                                    → behavioral check (4-metric ensemble)
                                                    → if both pass → RS256 JWT issued
                                                       sub = human, act.sub = agent
```

### Behavioral Signature Engine

Seven feature categories extracted from agent trajectories:

| Feature | What it captures |
|---------|-----------------|
| Tool call histogram | Which tools, how often |
| Bigram transitions | Sequential tool-call probabilities |
| Trigram transitions | Three-step sequence patterns |
| Response length stats | Message verbosity profile |
| Vocabulary stats | Lexical diversity, token distribution |
| Timing stats | Inter-action intervals |
| Structural features | Sequence shape, error rates |

Comparison uses a weighted ensemble: **Jensen-Shannon divergence (25%)** + **Cosine similarity (30%)** + **Markov analysis (25%)** + **Statistical comparison (20%)** → single 0.0–1.0 score.

## Tech stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (Python) |
| Database | PostgreSQL 17 + pgvector |
| Auth | Clerk |
| JWT | RS256 via PyJWT + cryptography |
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| 3D | Three.js |
| Deploy | Docker Compose / Railway |

## Quick start

```bash
# clone
git clone https://github.com/yskew/worldofagents.git
cd worldofagents

# configure
cp .env.example .env

# start
docker compose up --build -d

# run migrations
docker compose exec api alembic upgrade head

# seed demo data
docker compose exec api python scripts/seed.py

# run tests
docker compose exec api pytest tests/ -v
```

**Services:**

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Mailpit | http://localhost:8025 |

## API endpoints

### Authenticated (Clerk session)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/agents/register` | Register agent, get one-time key |
| GET | `/agents` | List your agents |
| GET | `/agents/{id}` | Agent details |
| DELETE | `/agents/{id}` | Revoke agent |
| POST | `/agents/{id}/refine` | Improve behavioral signature |
| POST | `/agents/{id}/rotate-key` | Rotate agent key |

### Open (no auth required)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/verify` | Verify agent identity, get JWT |
| POST | `/compare` | Compare two trajectories |
| GET | `/agents/{id}/public` | Public profile + stats |
| GET | `/.well-known/jwks.json` | JWKS for JWT verification |
| GET | `/health` | Health check |

## Tests

116 tests across 9 suites, 86% code coverage.

```
tests/test_agent_keys.py        — Key generation and verification
tests/test_agents_api.py        — Agent CRUD endpoints
tests/test_auth.py              — Clerk auth + human sync
tests/test_compare_api.py       — Trajectory comparison
tests/test_health.py            — Health endpoints
tests/test_integration.py       — End-to-end flows
tests/test_jwks.py              — JWKS + JWT verification
tests/test_models.py            — Database models
tests/test_signature_engine.py  — Behavioral feature extraction + comparison
tests/test_user_flows.py        — Full user journey tests (54 tests)
tests/test_verify_api.py        — Verification endpoint
```

## Project structure

```
worldofagents/
├── app/                    # FastAPI backend
│   ├── api/                # Route handlers
│   ├── auth/               # Clerk + agent key + JWT issuer
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic request/response models
│   ├── services/           # Business logic + signature engine
│   └── utils/              # Crypto helpers
├── frontend/               # React + Vite + Three.js
│   └── src/
│       ├── components/     # Shell, nav, pixel animations, 3D globe
│       ├── pages/          # Dashboard, Agents, Verify, Compare, Docs
│       ├── hooks/          # Scroll scene engine
│       └── lib/            # API client
├── tests/                  # pytest test suites
├── scripts/                # DB seed, RSA key generation
├── alembic/                # Database migrations
├── promo/                  # Promotional assets
├── Dockerfile              # API container
├── docker-compose.yml      # Full stack orchestration
├── railway.json            # Railway deployment config
└── THESIS.md               # Full research thesis
```

## Deployment

See [RAILWAY_ENV_VARS.md](RAILWAY_ENV_VARS.md) for Railway deployment instructions with copy-pastable environment variables.

## Research

This is a research MVP exploring agent identity verification through behavioral signatures. See [THESIS.md](THESIS.md) for the full thesis covering:

- The agent identity problem and why it matters now
- Four-layer identity model (two missing layers we build)
- Behavioral signature engine design and academic backing
- Security threat model (honest about cryptographic vs probabilistic)
- Competitive landscape (IETF, ZeroID, AIP, Entra, Google Vertex)
- Roadmap (World ID, OIDC federation, MCP integration, IETF submission)

## License

Research project — license TBD.
