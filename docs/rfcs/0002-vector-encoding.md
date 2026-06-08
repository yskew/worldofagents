# RFC 0002 — Principled Signature Vector Encoding

- **Status:** Draft (for discussion before implementation)
- **Area:** Behavioral signature engine (`app/services/signature_engine.py::features_to_vector`)
- **Affects:** `agents.signature_vector` (stored data), `/verify`, `/compare`, registration, refine, seed
- **Depends on:** RFC 0001 (independent, but shares the flag-gated rollout pattern)

---

## 1. Problem statement

`features_to_vector` packs the 7-category feature dict into the 256-dim
`signature_vector` that drives the **cosine** metric (30% of the score, the
single largest weight). Three defects make that embedding weaker than it looks:

1. **~72 of 256 dimensions are dead.** Indices `100–149` and `234–255` are never
   written. The "256-dim" vector is really ~184 meaningful dims with gaps.
2. **Magic-number normalization.** Stats are divided by hardcoded constants
   (`mean/1000`, `variance/1e6`, `timing/100`, …). Values outside the assumed
   range saturate or vanish; the scale is arbitrary and undocumented.
3. **Positional fragility — the real bug.** `_fill_sorted_values` sorts histogram
   values *by magnitude* and drops them into slots 0..N. So a coding agent
   (`read_file: 0.4, search: 0.3, …`) and a devops agent
   (`deploy: 0.4, monitor: 0.3, …`) land their values in the **same positions**.
   The cosine metric ends up comparing the *shape* of the distribution, not
   *which tools* are used. Two completely different agents with similar-shaped
   histograms look similar in vector space.

Defect 3 is the important one: it means 30% of the score is partly blind to tool
identity. The JSD metric (25%) does compare tool identity, which masks the
problem, but the cosine contribution is degraded.

## 2. Goals & non-goals

**Goals**
- Encode tool/transition identity into **stable positions** (same tool → same
  dimension across all agents), so cosine compares like-for-like.
- Replace magic divisors with **bounded, documented transforms**.
- Use the full dimensionality (no dead slots).
- Preserve every invariant: vector L2-normalized, score ∈ [0,1], symmetry,
  identical → 1.0, impersonation fails.
- Ship without breaking existing stored data or live verification.

**Non-goals**
- Changing the vector dimension (stays 256 → no DDL change to `Vector(256)`,
  no pgvector index rebuild). A dimension change is a separate, heavier RFC.
- Changing the 7 extracted features themselves (that is `extract_features`,
  untouched here — we only change how the dict becomes a vector).
- Learned/trained embeddings.

## 3. The core fix: feature hashing (the hashing trick)

Map each tool name and transition deterministically to a bucket via a stable
hash, and accumulate its value there. Same tool name → same bucket for every
agent, so cosine compares matching tools.

```
bucket(name) = stable_hash(name) % SIZE         # within the band's slot range
vec[band_start + bucket] += value               # collisions sum (rare, tolerable)
```

- **Stable hash:** a fixed algorithm independent of the Python process
  (`hashlib.blake2b(name, digest_size=8)` → int). NOT Python's builtin `hash()`,
  which is salted per-process and would make vectors non-reproducible across
  restarts — a correctness trap given vectors are persisted.
- **Sign hashing** (Weinberger et al.) to make collisions cancel rather than
  always add bias: `vec[bucket] += sign(name) * value`.

Proposed 256-dim band layout (all slots used, documented constants):

| Band | Dims | Contents | Encoding |
|------|------|----------|----------|
| Tool histogram | 0–95 (96) | per-tool frequency | hashed by tool name |
| Bigram transitions | 96–175 (80) | `src→dst` probability | hashed by `"src>dst"` |
| Trigram transitions | 176–223 (48) | `a|b→c` probability | hashed by `"a|b>c"` |
| Response-length stats | 224–231 (8) | mean, var, skew, count | bounded transform |
| Vocabulary stats | 232–239 (8) | ttr, unique, total | bounded transform |
| Timing stats | 240–247 (8) | mean/std/max interval | bounded transform |
| Structural | 248–255 (8) | len, types, ratios | already in [0,1] |

**Bounded transforms** replace magic divisors. For unbounded positive
quantities (lengths, counts, intervals) use `x / (x + k)` (a soft, monotonic
squash into [0,1) with a documented knee `k` per quantity), or `log1p`
normalized. Ratios already in [0,1] pass through. Final vector L2-normalized as
today.

## 4. The hard part: stored data & backward compatibility

`signature_vector` is **persisted** at registration/refine. Changing the
encoding makes old vectors incomparable with newly-encoded trajectories. This is
the central risk and the whole reason this is a separate RFC from 0001.

**Key insight:** the vector is a *derived cache* of the `signature` JSONB, which
is the encoding-independent source of truth. Any vector can be recomputed from
its JSONB at any time. The existing code already relies on this — `verify.py:33`
recomputes the stored vector from JSONB when `signature_vector IS NULL`.

Rollout strategy (flag-gated, same discipline as RFC 0001):

1. Add `VECTOR_ENCODING_V2` flag (default `False`) and `agents.signature_version`
   (nullable smallint; NULL/1 = legacy, 2 = hashed).
2. Implement `features_to_vector_v2`; `features_to_vector` dispatches on the flag.
3. **Self-consistency guarantee at compare time.** In `/verify` and `/compare`,
   derive *both* vectors from their feature dicts with the *current* encoding,
   rather than trusting a possibly-stale stored vector. The incoming trajectory
   is already encoded live; we recompute the stored side from `signature` JSONB
   too. Cost: one extra `features_to_vector` call (~microseconds, no I/O). This
   makes comparison correct regardless of what is persisted — old or new — and
   removes the mixed-encoding failure mode entirely.
4. **Backfill** for search/consistency: `scripts/reembed.py` recomputes
   `signature_vector` from `signature` for every agent and stamps
   `signature_version`. Idempotent; safe to re-run; logs counts.
5. Registration/refine write V2 vectors when the flag is on.

Because step 3 always compares JSONB-derived vectors under one encoding, flipping
the flag cannot corrupt live verification even before the backfill runs. The
backfill is then a cleanup that aligns persisted data with the active encoding.

### Compatibility summary

| Concern | Handling |
|---------|----------|
| Stored vectors (old encoding) | Recomputed from JSONB at compare time; backfilled by script |
| `signature` JSONB | Untouched — source of truth, encoding-independent |
| DB column `Vector(256)` | Unchanged (dim stays 256); no index rebuild |
| API response shape | Unchanged (cosine is still a single sub-score) |
| Flag off | `features_to_vector` byte-identical to today |
| Seed data | Reseed or run reembed; both produce V2 vectors when flag on |

## 5. Testing plan

1. **Characterization (flag off):** the existing `test_signature_engine.py` and
   the RFC 0001 snapshot must pass unchanged — V1 encoding is preserved.
2. **Determinism:** `features_to_vector_v2(f)` is identical across processes
   (guards against accidental use of salted `hash()`). Run in a subprocess and
   compare bytes.
3. **Stable positions:** two trajectories sharing a tool produce nonzero overlap
   in the *same* dimension; the cosine of "same tools, reordered values" is high
   where V1 would have been misled. Add a targeted regression for the
   coding-vs-devops shape-collision case from §1.
4. **Invariants (both encodings):** L2 norm == 1.0 (or 0 vector), score ∈ [0,1],
   symmetry, identical → 1.0.
5. **Discrimination (success metric, §6):** V2 cosine separates same- vs
   different-agent better than V1 on the eval set; no regression on full
   trajectories.
6. **Self-consistency:** an agent stored with a V1 vector still verifies
   correctly after the flag flips (proves the compare-time recompute path).
7. **Backfill:** `reembed.py` on a seeded DB updates all rows, is idempotent, and
   post-backfill scores match live-recompute scores.
8. Coverage maintained ≥ 86%.

## 6. Success metrics

Reuse the labeled eval set from RFC 0001 §7 (same- vs different-agent pairs).
Measured on the **cosine sub-score specifically** (the thing this RFC changes):

| Metric | Target |
|--------|--------|
| Cosine ROC-AUC (same vs different) | ↑ vs V1 |
| Shape-collision false-similarity (coding vs devops cosine) | ↓ materially (this is the bug) |
| Overall score AUC | ↑ or unchanged; no regression on full trajectories |
| Vector dimension utilization | 100% of 256 dims reachable (was ~72% dead) |

Hard gate: no regression in overall-score discrimination on full trajectories;
measurable drop in shape-collision false similarity.

## 7. Future enhancements unlocked

- Honest **pgvector ANN search** over `signature_vector` (find similar agents),
  now that positions are semantically stable and dims are fully used.
- Tunable `SIZE`/`k` knobs become candidates for the learned-weights work.
- Optional dimension increase (512/768) once a real ANN workload justifies the
  index cost — a clean follow-on since the band layout is parameterized.

## 8. Implementation checklist (only after this RFC is accepted)

- [ ] `VECTOR_ENCODING_V2` flag in `app/config.py` (default `False`).
- [ ] `agents.signature_version` column + migration (nullable smallint).
- [ ] `features_to_vector_v2` (hashed bands, bounded transforms, blake2b hash).
- [ ] `features_to_vector` dispatches on flag; V1 path untouched.
- [ ] `/verify` + `/compare`: recompute stored vector from JSONB for
      self-consistency.
- [ ] `scripts/reembed.py` backfill (idempotent, logged).
- [ ] Tests per §5; eval comparison per §6 recorded in the PR.
- [ ] Flip default to `True` + run backfill — deferred follow-up after validation.
