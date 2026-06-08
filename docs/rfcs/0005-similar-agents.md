# RFC 0005 — "Find Similar Agents" (pgvector ANN)

- **Status:** Implemented
- **Area:** `POST /similar`, `agents.signature_vector` HNSW index
- **Depends on:** RFC 0002 (stable vector encoding makes ANN meaningful)

---

## 1. Why

The product stored a 256-dim `signature_vector` and a pgvector column but never
used them for search — every comparison was pairwise. Before RFC 0002 an ANN
index would have been near-useless anyway, because the legacy encoding placed
values by magnitude, so nearest-neighbour in that space did not mean
behaviourally similar. With stable per-tool positions (RFC 0002), embedding
search is now meaningful, so we expose it: *"which registered agents behave most
like this trajectory?"*

## 2. Design

`POST /similar` (public, like `/compare`):
```
{ "trajectory": [...], "limit": 5 }
->
{ "results": [ {agent_id, name, owner_display_name, score, vector_similarity} ],
  "stale_excluded": 0 }
```

Two-stage retrieval:
1. **ANN candidate fetch** — pgvector cosine distance (`<=>`) over active agents,
   accelerated by an **HNSW** index (`vector_cosine_ops`). Pulls `4×limit`
   candidates (capped 50).
2. **Ensemble re-rank** — each candidate is rescored with the full
   `compare_signatures` (all four metrics), and results are sorted by that
   `overall_score`. The raw ANN cosine is returned as `vector_similarity` for
   transparency.

This gives ANN speed with ensemble-quality ranking.

## 3. Encoding correctness

ANN only works when all vectors share one encoding. The query is encoded live
(current encoding); the scan filters to `signature_version = active`, so
mixed-encoding rows can't pollute results. Agents not yet re-embedded are counted
in `stale_excluded` (run `scripts/reembed.py` to include them) — surfaced, not
silently dropped. Candidate vectors are recomputed from the JSONB signature
before re-rank, consistent with the RFC 0002 self-consistency rule.

## 4. Index choice

**HNSW** over IVFFlat: no training step (works on empty/small tables), supports
incremental inserts, better recall at low latency. Exact KNN still works without
the index; it only accelerates the scan. Migration is `CREATE INDEX IF NOT
EXISTS ... USING hnsw`.

## 5. Tests

`tests/test_similar_api.py`: a coding-like query ranks the coding agent first,
results are score-sorted, `limit` is respected, empty DB returns `[]`, and an
empty trajectory is rejected (422).

## 6. Future work

- Filter/scope by owner or tag.
- Expose `stale_excluded` remediation in an admin view.
- Tune HNSW `ef_search` for larger fleets; revisit dimension (RFC 0002 §7).
