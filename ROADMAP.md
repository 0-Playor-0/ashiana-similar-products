# Ashiana Similar-Products Engine — Build Roadmap

This document is written for Claude Code. Read the whole file before writing any code, then execute one phase at a time, stopping at every **CHECKPOINT** for user review.

---

## 0. Working rules for Claude Code

1. **Work in phase order.** At the end of each phase, run that phase's acceptance checks. Then summarize what you built and any deviations from this doc, and stop for user confirmation.
2. **Respect decision status.** Decisions in §3 are **LOCKED**: don't reopen them or propose alternatives. Decisions in §4 are **OPEN**: ask the user when you reach them, and don't guess.
3. **Stay in scope.** Don't build anything listed in §13 (out of scope), even if it's easy.
4. **Keep ranking logic in one place.** Ranking lives in `core/` (numpy only). Both the offline pipeline and the API import it. Never reimplement fusion in the notebook, the API, or the frontend.
5. **Keep the API free of heavy ML dependencies.** It must never import `torch`, `transformers`, or `sentence_transformers`. A test enforces this.
6. **Protect secrets.** Never commit them. `.env` is gitignored, and `.env.example` documents every variable.
7. **Never fabricate catalog data.** Missing fields stay `null`, and the similarity functions handle missing values.
8. **Log your decisions.** Record every non-trivial choice this doc doesn't dictate in `docs/DECISIONS.md` as a short entry: decision, reason, alternatives considered. Reviewers will read this file.
9. **Pin versions.** Pin every dependency version. Use Python 3.11 and Node 22 LTS or newer.
10. **Support both machines.** The dev machine is a MacBook Air: use the `mps` device for embedding when available, else CPU. Everything must also run on Colab.
11. **Commit small.** Use small commits with conventional messages, e.g. `feat(pipeline): add DINOv2 image encoder`.
12. **Verify third-party details.** Model IDs, provider endpoints, and config syntax named here may have changed. Check current docs before using them, and note any change in `DECISIONS.md`.

---

## 1. Project summary

**Goal.** Build a content-based "similar products" recommender for Ashiana, a handcrafted ethnic jewelry e-commerce brand whose collections include Antique, Kundan, Zircon, and Crystal. It's a cold-start setting: no clicks, purchases, or any other user behavior data. The catalog has roughly 30–100 SKUs.

**Definition of "similar."** Substitutes only: other pieces a shopper might buy *instead of* this one. Complementary items ("complete the look") are out of scope.

**Deliverables (public GitHub repo):**
1. An offline pipeline that builds a versioned artifact bundle from the catalog.
2. A Colab notebook covering design reasoning, signal analysis, and evaluation.
3. A FastAPI service on a free tier.
4. A React UI on a free tier, in front of the API. It shows a shopper-facing product page with similar pieces, plus an **inspector** panel that exposes the model's reasoning.
5. A README and a 2–3 minute demo video.

**Constraints.** Free-tier hosting only, roughly 10 working sessions, and it must be easy to demo.

---

## 2. System architecture

```
OFFLINE  (local or Colab; rerun whenever the catalog changes)

  data source ─► ingest ─► clean + normalize ─► data/catalog.jsonl (canonical schema, §6)
                                  │
        ┌─────────────────────────┼──────────────────────────────┐
        ▼                         ▼                              ▼
  IMAGE                      TEXT                           METADATA
  pick packshot              strip boilerplate              taxonomy + field
  pad to square (white)      LLM descriptor (cached)         similarity functions
  thumbnails                 template → sentence
        │                         │                              │
  DINOv2-small (CLS)         bge-small-en-v1.5                   │
        ▼                         ▼                              ▼
  S_image  (N×N cosine)      S_text  (N×N cosine)           S_meta  (N×N, 0..1)
        └────────────┬────────────┴──────────────────────────────┘
                     ▼
     core.fusion.offdiag_zscore → Z_image, Z_text, Z_meta
                     ▼
     artifacts/  (matrices + catalog + thumbs + manifest + eval report)  ── committed to git

ONLINE

  FastAPI (numpy only) loads artifacts/ at startup
     GET /products/{sku}/similar?w_image&w_text&w_meta…
        → core.fusion: weighted sum of Z rows → filters → top-k → reasons
                     ▲
                     │ JSON over HTTPS (CORS)
  React UI (static site): catalog grid · product page + inspector · under-the-hood page
```

**Key properties:**

- **No model runs at serve time.** The service is item-to-item only, and every embedding is computed offline.
- **Fusion weights are adjustable per request.** The bundle stores per-signal Z matrices rather than a pre-fused top-k. Fusion is one weighted sum over three N-length rows, which is microseconds at this scale. That's what powers the weight sliders in the UI.
- **The artifact bundle is the contract** between offline and online. `manifest.json` versions it, and every API response echoes that version.

---

## 3. LOCKED decisions

| Area | Decision | Notes |
|---|---|---|
| Task | Similar products (substitutes), item-to-item | No text search, no image upload, no complements |
| Approach | Frozen pretrained encoders + hand-designed metadata similarity + weighted late fusion | No training or fine-tuning |
| Image encoder | DINOv2 ViT-S/14, `facebook/dinov2-small` via `transformers` | Use `pooler_output` (the CLS token after layernorm), then L2-normalize. 384-d |
| Image preprocessing | Primary **packshot** only. Pad to square with white, then resize to 224×224 **without center crop** | Center crop cuts off dangling earrings and necklace ends |
| Text encoder | `BAAI/bge-small-en-v1.5` via `sentence-transformers`, `normalize_embeddings=True` | 384-d. No query instruction prefix (symmetric similarity) |
| Text input | Boilerplate-stripped description → LLM-extracted design attributes (JSON) → fixed template sentence | Runs offline and is cached. Excludes fields already scored by metadata (§8, Phase 2) |
| LLM | Free tier (Gemini or Groq) through an **OpenAI-compatible** endpoint using the `openai` SDK | Provider, base URL, and model come from env (§7). Temperature 0 |
| Metadata similarity | Gower-style weighted average of per-field similarities, renormalized over fields present on both items | Field definitions in Phase 3 |
| Score normalization | Global z-score per signal over **off-diagonal** entries | The diagonal (self = 1.0) would inflate the mean and std |
| Fusion | `score = w_image·Z_image + w_text·Z_text + w_meta·Z_meta`. Defaults 0.5 / 0.2 / 0.3, retuned in Phase 4 | Weights must be ≥ 0 and are normalized to sum to 1 |
| Category rule | **Hard filter** to the same product type by default. **Fallback:** if fewer than `k` same-type candidates exist, backfill from related types ranked by category similarity, then fused score | Backfilled items are flagged `fallback: true` |
| Always excluded | The query item itself, and items sharing its `parent_id` (when present) | |
| Tie-break | Score descending, then `sku` ascending | Guarantees deterministic output |
| Search | Exact, using precomputed matrices | No ANN library, no vector DB |
| API | FastAPI + Pydantic + numpy + uvicorn | No torch. Loads the bundle at startup and fails fast if it's missing or invalid |
| Frontend | React + Vite + TypeScript, TanStack Query, React Router | Separate deploy from the API |
| Hosting | Render Blueprint (`render.yaml`): API as a free web service, UI as a free static site | Free web services sleep when idle, so the UI must handle cold starts (Phase 6) |
| Notebook | Imports `pipeline/` and `core/`, uses committed artifacts and caches, runs top-to-bottom on Colab with no API key | |

---

## 4. OPEN decisions (ask the user when reached)

| ID | Phase | Question | Default if the user says "you pick" |
|---|---|---|---|
| D1 | 0 | **Data source:** a dataset provided by Ashiana, scraping their public site, or a public/synthetic fallback? | None. This must be answered |
| D2 | 0 | **Scope:** which product types are in the catalog? The site also sells home decor and hair accessories | Jewelry only |
| D3 | 1 | **Image rights:** OK to commit small thumbnails of Ashiana's product photos to a public repo? | Commit 400px thumbnails with an attribution note in the README. Keep full-size originals gitignored |
| D4 | 2 | **LLM provider and key:** Gemini or Groq? Which model? | Gemini Flash-class model |
| D5 | 3 | **Taxonomy:** product-type, collection, and material similarity tables | Propose values from the data; the user approves or edits them |
| D6 | 6 | **UI design plan:** color, type, and layout tokens | Propose per §10.4; the user approves before any UI code is written |

---

## 5. Repository layout

```
ashiana-similar-products/
├── README.md
├── ROADMAP.md                     # this file
├── docs/
│   ├── DECISIONS.md               # decision log (rule 8)
│   ├── LABELING_GUIDE.md          # relevance rubric (Phase 4)
│   └── architecture.svg           # exported diagram for README + UI
├── render.yaml
├── Makefile
├── .env.example
├── .github/workflows/ci.yml
├── config/
│   ├── settings.yaml              # all tunables (§7)
│   └── taxonomy.yaml              # types, collections, materials, synonyms, sim tables
├── data/
│   ├── raw/                       # source snapshots (gitignored if large or scraped)
│   ├── images/                    # full-size originals (gitignored)
│   ├── overrides/primary_image.json   # manual packshot overrides {sku: filename}
│   └── catalog.jsonl              # canonical, validated catalog (committed)
├── core/                          # numpy-only; imported by pipeline AND api
│   ├── __init__.py
│   ├── fusion.py                  # offdiag_zscore, fuse, topk, tie-break
│   ├── filters.py                 # self/parent exclusion, category filter + fallback, price ratio
│   ├── reasons.py                 # human-readable reasons from breakdown + metadata
│   └── bundle.py                  # load/validate artifact bundle, manifest schema
├── pipeline/
│   ├── schema.py                  # Pydantic Product model (§6)
│   ├── ingest/
│   │   ├── from_file.py           # D1 option A
│   │   └── scrape_site.py         # D1 option B (only if chosen)
│   ├── clean.py                   # normalization, synonym maps, keyword attribute extraction
│   ├── images.py                  # download, packshot selection, pad, thumbnails
│   ├── describe.py                # boilerplate strip + LLM descriptor + cache + grounding check
│   ├── encode_image.py
│   ├── encode_text.py
│   ├── metadata_sim.py
│   ├── build.py                   # CLI: runs everything → artifacts/
│   └── evaluate.py                # metrics, baselines, ablations, proxies → artifacts/eval/
├── artifacts/                     # committed; small
│   ├── manifest.json
│   ├── catalog.json               # display fields + normalized metadata per SKU
│   ├── matrices.npz               # ids, S_image, S_text, S_meta, Z_image, Z_text, Z_meta
│   ├── descriptors.json           # LLM cache: {hash: {input, output, model, prompt_version}}
│   ├── thumbs/                    # {sku}.webp, 400px
│   └── eval/
│       ├── report.json
│       ├── label_pool.json        # candidates to label (Phase 4)
│       └── figures/
├── labels/relevance_labels.json   # hand labels (committed)
├── notebooks/ashiana_similar_products.ipynb
├── api/
│   ├── requirements.txt           # fastapi, uvicorn[standard], numpy, pydantic, pyyaml
│   ├── app/{main.py, models.py, service.py, settings.py}
│   └── tests/
├── frontend/
│   ├── package.json, vite.config.ts, index.html
│   └── src/{main.tsx, api/, routes/, components/, styles/tokens.css}
├── requirements-pipeline.txt      # torch, transformers, sentence-transformers, pillow, pandas, openai, …
└── tests/                         # core unit tests + pipeline light tests
```

**Makefile targets:** `setup`, `data`, `build`, `eval`, `api` (runs uvicorn locally), `ui` (runs the Vite dev server), `test`, `lint`.

---

## 6. Canonical data schema

Every data source maps into this schema. Nothing downstream reads the raw source.

```python
class Product(BaseModel):
    sku: str                          # unique, stable
    parent_id: str | None = None      # groups variants of one design (if source has it)
    title: str
    description_raw: str | None = None
    product_type: str                 # normalized via taxonomy.yaml, e.g. "earrings", "necklace", "jewelry_set", "bangle_bracelet", "ring"
    collection: str | None = None     # normalized: "antique", "kundan", "zircon", "crystal", "charm", …
    materials: list[str] = []         # base metal / plating: "brass", "alloy", "silver", "gold_plated", "rose_gold_plated"
    stones: list[str] = []            # "kundan", "pearl", "zircon", "crystal", "meenakari", …
    colors: list[str] = []
    price_inr: float | None = None
    image_urls: list[str] = []
    primary_image: str | None = None  # local filename after Phase 1
    in_stock: bool | None = None
    source_url: str | None = None
    attr_provenance: dict[str, str] = {}   # e.g. {"stones": "source" | "keyword" | "llm"}
```

**Normalization rules** (in `clean.py`, with the tables in `taxonomy.yaml`):

- Lowercase everything, trim whitespace, and collapse duplicates.
- Apply synonym maps, e.g. `cz`/`american diamond`/`ad` → `zircon`, `oxidized` → `oxidised`, `jhumki` → `jhumka`.
- **Keyword attribute extraction.** When a structured field is empty, fill `materials`, `stones`, and `colors` by matching the taxonomy vocabulary against the title and description. Mark the provenance as `keyword`.
- Parse price strings like `₹1,299` into `1299.0`.
- **Validation report** (printed and saved to `artifacts/eval/data_report.json`): product counts per `product_type` and per `collection`, missingness per field, price min/median/max, and the list of product types with fewer than `k+1` items (these will trigger fallback).

---

## 7. Configuration

`config/settings.yaml`:

```yaml
catalog:
  include_product_types: [earrings, necklace, jewelry_set, bangle_bracelet, ring]   # D2
images:
  pad_color: [255, 255, 255]
  model_size: 224
  thumb_size: 400
  device: auto            # auto → mps | cuda | cpu
text:
  boilerplate_min_share: 0.2    # a sentence in ≥20% of products counts as boilerplate
llm:
  prompt_version: v1
  temperature: 0
  min_interval_s: 7.0           # stay under free-tier RPM; ~2.5 for Groq
  max_retries: 4
metadata:
  field_weights: {collection: 0.25, materials: 0.20, stones: 0.20, price: 0.20, colors: 0.10, product_type: 0.05}
  price_tau: 0.6931             # ln 2 → a 2× price ratio gives similarity e^-1 ≈ 0.37
fusion:
  default_weights: {image: 0.5, text: 0.2, meta: 0.3}
  k_default: 6
  k_max: 12
reasons:
  z_threshold: 1.0              # a signal counts as "strong" when z ≥ 1
```

`.env.example`:

```bash
# Offline pipeline only — never needed by the API or UI
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/   # or https://api.groq.com/openai/v1
LLM_API_KEY=
LLM_MODEL=                      # confirm the current free-tier model id with the provider (rule 12)

# API
ARTIFACTS_DIR=artifacts
FRONTEND_ORIGINS=http://localhost:5173

# Frontend (build time)
VITE_API_BASE_URL=http://localhost:8000
```

---

## 8. Phases

Rough schedule: sessions 1–10, plus buffer. Each phase ends with a CHECKPOINT.

### Phase 0: Setup and data acquisition (session 1)

**Tasks**

1. Scaffold the repo per §5. Set up the venv (uv or pip), ruff, a pytest skeleton, the Makefile, `.gitignore` (venv, `node_modules`, `.env`, `data/images/`, `__pycache__`), and CI running ruff, core + api tests, and the frontend build.
2. **Ask the user D1 (data source) and D2 (scope).**
   - **Option A (provided dataset):** write `ingest/from_file.py` to map the source columns into the schema. Print the column mapping for the user to confirm.
   - **Option B (scraping):** first read the site's `robots.txt` and terms, and report them to the user before scraping anything. Then:
     - Before writing HTML parsers, open DevTools-style network inspection (for example, Playwright network capture) to check whether the category pages are backed by a JSON API. The site's category URLs contain UUIDs, which suggests they might be.
     - Be polite: at most 1 request per second, an identifying User-Agent, only public product pages in in-scope categories.
     - Save raw responses to `data/raw/` with a snapshot date, and record that date in the manifest.
   - **Option C (fallback):** use a small public jewelry dataset. Document the source and license.
3. Run normalization and write `data/catalog.jsonl`, then produce the validation report.

**Acceptance criteria**

- `make data` produces a validated `catalog.jsonl` with at least 30 products.
- Every product has at least one image URL, a `product_type`, and a `title`.
- The validation report shows counts per type and collection, plus missingness.

**CHECKPOINT:** show the user the validation report and the proposed `product_type` / `collection` vocabularies.

### Phase 1: Image pipeline (session 2)

**Tasks**

1. **Ask D3 (image rights).**
2. Download every image to `data/images/{sku}/`.
3. **Packshot selection.** For each product, pick the image whose border pixels are most uniformly near-white: sample a 5% border strip and score the share of pixels with all RGB channels ≥ 235. Ties go to the first image. `data/overrides/primary_image.json` can override the choice. Save a contact sheet of the chosen primaries to `artifacts/eval/figures/packshots.png` for manual review.
4. **Preprocessing.** Convert to RGB, pad to square with the configured pad color, resize to 224×224 with no crop, and normalize with DINOv2's ImageNet mean/std. Configure the processor with center crop disabled, or apply the transforms manually.
5. **Thumbnails.** Save 400px WebP thumbnails to `artifacts/thumbs/{sku}.webp` using the same padding.
6. **Encoding.** Run DINOv2-small in batches under `torch.inference_mode()`, take `pooler_output`, L2-normalize, and save `E_image` (N×384).

**Acceptance criteria**

- `E_image.shape == (N, 384)` and every row norm is ≈ 1.
- **Augmentation sanity test:** for 10 random products, a horizontally flipped and 90%-cropped copy of the primary image retrieves the original at rank 1 in at least 9 of 10 cases.
- The contact sheet has been reviewed and any bad packshots overridden.

**CHECKPOINT:** show the packshot contact sheet and nearest-image-neighbor grids for 5 products.

### Phase 2: Text pipeline (session 3)

**Tasks**

1. **Ask D4 (LLM provider, key, and model).**
2. **Boilerplate stripping.** Split descriptions into sentences, normalize them (lowercase, collapse whitespace), and drop any sentence that appears in at least `boilerplate_min_share` of products. Log the removed sentences.
3. **LLM descriptor** (`describe.py`):
   - Client: `openai.OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)`, `temperature=0`, JSON output via `response_format={"type": "json_object"}` where supported. Otherwise, instruct JSON-only output and strip code fences before parsing.
   - Input: title + cleaned description (+ source tags, if any).
   - System prompt (version it as `prompt_version`):
     > You extract design attributes from a jewelry product listing. Use only information explicitly present in the input; do not infer or embellish. If a field has no support in the input, return an empty list. Return only a JSON object matching the schema.
   - Output schema, validated with Pydantic:
     ```json
     {
       "motifs": ["peacock", "lotus"],
       "style": ["temple", "traditional"],
       "finish": ["antique", "matte"],
       "occasion": ["wedding", "festive"],
       "design_features": ["jhumka drop", "layered", "adjustable"],
       "extracted": {"materials": [], "stones": [], "colors": []}
     }
     ```
   - **Grounding check:**
     - Each term in `extracted.*` must appear in the input text (after synonym mapping). Drop and log any term that doesn't.
     - Use extracted terms **only** to fill metadata fields that are still empty after keyword extraction, with provenance `llm`.
     - Log terms in the other fields that don't appear in the input, for review in the notebook, but don't drop them.
   - **Descriptor sentence** (deterministic template, empty parts omitted): `"Motifs: … Style: … Finish: … Occasion: … Features: …"`. Deliberately **exclude** product type, collection, materials, stones, colors, and price, because metadata already scores those and including them would double-count. If every field is empty, fall back to the cleaned title with taxonomy words stripped.
   - **Rate limiting and retries:** sleep `min_interval_s` between calls. Use exponential backoff on 429s and 5xx errors, up to `max_retries`. On a validation failure, retry once with the error message appended.
   - **Cache:** key each entry by `sha256(input_text + prompt_version + model)` and store it in `artifacts/descriptors.json`. The pipeline must fully rebuild from the cache with **no API key**.
4. **Encoding.** Encode the descriptors with bge-small and save `E_text` (N×384).

**Acceptance criteria**

- Every product has a descriptor.
- A second `make build` run makes zero LLM calls.
- A before/after table (raw description → descriptor) for 10 products is exported for the notebook.
- The grounding log has been reviewed.

**CHECKPOINT:** show the before/after table, the removed boilerplate, and the dropped ungrounded terms.

### Phase 3: Metadata similarity, fusion, recommendations (session 4)

**Tasks**

1. **Ask D5.** Propose `taxonomy.yaml` from the actual data, with placeholder values for the user to edit:
   ```yaml
   product_type_similarity:        # symmetric; unlisted pairs = 0; self = 1
     earrings|ear_cuff: 0.8
     necklace|jewelry_set: 0.6
     necklace|pendant: 0.8
   collection_similarity:
     antique|kundan: 0.5
     zircon|crystal: 0.6
   material_similarity:
     gold_plated|rose_gold_plated: 0.7
     gold_plated|silver: 0.2
   synonyms: {cz: zircon, "american diamond": zircon, oxidized: oxidised}
   ```
2. **Field similarities** (`metadata_sim.py`):
   - `product_type`, `collection`: table lookup.
   - `materials`: soft set similarity, `0.5·(mean_a max_b sim(a,b) + mean_b max_a sim(b,a))`, using the material table (exact match = 1).
   - `stones`, `colors`: Jaccard.
   - `price`: `exp(-|ln(p_a/p_b)| / price_tau)`.
   - **Missing values:** skip any field missing on either item and renormalize the weights over the fields present. If no fields are present, `S_meta = 0`.
3. **`core/fusion.py`:**
   ```python
   def offdiag_zscore(S):
       m = ~np.eye(len(S), dtype=bool)
       return (S - S[m].mean()) / (S[m].std() + 1e-8)

   def fuse_row(Z: dict[str, np.ndarray], q: int, w: dict[str, float]) -> np.ndarray:
       w = normalize(w)                          # ≥0, sum to 1, reject all-zero
       return sum(w[s] * Z[s][q] for s in w)
   ```
4. **`core/filters.py`:**
   - Exclude the query itself and its `parent_id` siblings.
   - Hard-filter to the same `product_type`. If fewer than `k` candidates remain, backfill from other types with `product_type_similarity > 0`, ordered by type similarity then fused score, and set `fallback=True`.
   - Optional `max_price_ratio` filter, and `in_stock` when that field exists.
5. **`core/reasons.py`:** turn the score breakdown and metadata overlaps into short strings, for example:
   - "Visually similar" (image z ≥ threshold)
   - "Similar design details" (text z ≥ threshold)
   - "Same collection: Kundan"
   - "Also features pearl"
   - "Similar price (₹1,450 vs ₹1,299)"
   - "From a related category" (fallback)

   Cap at 3 reasons, ordered by contribution.
6. **`build.py` bundle writer:** write `matrices.npz` (ids plus S and Z per signal), `catalog.json`, the thumbnails, and `manifest.json`:
   ```json
   {"bundle_version": "2026-09-12T10:00:00Z-<catalog_hash[:8]>", "catalog_hash": "...",
    "taxonomy_hash": "...", "n_items": 84, "git_commit": "...", "data_snapshot": "...",
    "models": {"image": "facebook/dinov2-small", "text": "BAAI/bge-small-en-v1.5",
               "llm": "<model>", "prompt_version": "v1"},
    "default_weights": {"image": 0.5, "text": 0.2, "meta": 0.3}}
   ```

**Acceptance criteria**

- `make build` rebuilds the bundle from scratch in a few minutes on the MacBook Air, with no API key needed.
- Core unit tests pass. They cover:
  - z-score excludes the diagonal
  - weight normalization and all-zero rejection
  - self and parent exclusion
  - fallback triggers exactly when same-type count < k
  - deterministic tie-break
  - a price-similarity symmetry property test
- A recommendations grid (query + top-6) is saved for every product.

**CHECKPOINT:** the user eyeballs the full-catalog grid, a PDF or HTML page of every query with its top-6. Note the obvious failures.

### Phase 4: Evaluation (sessions 5–6)

**Labeling**

1. Write `docs/LABELING_GUIDE.md`:
   - **2** = I'd happily show this as an alternative
   - **1** = acceptable
   - **0** = wrong or irrelevant
2. Choose 25 query SKUs, stratified by product type.
3. **Pooling:** for each query, take the union of the top-8 from image-only, text-only, meta-only, fused-default, and the two baselines. Write this pool to `artifacts/eval/label_pool.json`.
4. The labeling UI is a dev-only frontend route `/label` (enabled when `VITE_ENABLE_LABELING=true`). It shows the query and candidates in shuffled order with method names hidden, and keyboard shortcuts 0/1/2. It's fully client-side: a "Download labels" button saves `relevance_labels.json`, which the user commits. No API write endpoint.

**Metrics** (`evaluate.py`, written to `artifacts/eval/report.json` and `figures/`):

- **Ranking quality:** NDCG@5 and P@5 (relevance ≥ 1), with 95% bootstrap CIs over queries (1,000 resamples). With only 25 queries, the CIs are mandatory.
- **Methods compared:**
  - random-within-type (mean of 100 seeds)
  - same-type + nearest-price baseline
  - image-only, text-only, meta-only
  - fused (default weights)
  - fused (tuned weights)
- **Weight tuning:** grid search over the weight simplex in steps of 0.1. Report the leave-one-query-out NDCG so the tuned number isn't just overfit. Prefer a weight setting in a flat region of the score surface over the single best point. Write the chosen weights back as `default_weights`.
- **Proxies:**
  - **Held-out attribute agreement:** with metadata excluded (`w_meta=0`), what share of the top-5 matches the query's collection?
  - **Cross-signal agreement:** Jaccard@5 overlap between the image-only and text-only lists.
  - **Coverage:** the share of SKUs that appear in at least one top-5 list.
  - **Hubness:** the in-degree distribution over top-5 lists, its skewness, and the top-5 hubs.
  - **Diversity:** mean intra-list similarity.
  - **Price sanity:** median price ratio between query and recommendations.
  - **Robustness:** the image hit@1 under augmentation, from Phase 1.
- **Failure cases:** automatically surface the 5 queries with the lowest NDCG, for the notebook and the UI.

**Acceptance criteria**

- `report.json` contains every table above.
- If the fused model doesn't beat the same-type + nearest-price baseline, the report **says so plainly** and discusses why.

**CHECKPOINT:** review the ablation table and failure cases with the user.

### Phase 5: API (session 7)

Implement §9 exactly.

**Acceptance criteria**

- All endpoints are tested with `TestClient`.
- The test `import api.app.main` leaves `torch` absent from `sys.modules`.
- Process RSS stays under 250 MB after startup.
- The p95 latency of `/similar` locally is under 20 ms.
- `/docs` renders.

**CHECKPOINT.**

### Phase 6: Frontend (sessions 8–9)

1. **Ask D6.** Present the design plan per §10.4 and wait for approval before writing UI code.
2. Implement §10.

**Acceptance criteria**

- Works from 360px to desktop widths.
- Lighthouse accessibility ≥ 90.
- Loading, error, empty, and cold-start states exist for every data view.
- Weights live in the URL and are shareable.

**CHECKPOINT:** the user clicks through locally against the local API.

### Phase 7: Notebook (session 9, in parallel with the UI)

The notebook runs top-to-bottom on Colab: `git clone`, `pip install -r requirements-pipeline.txt`, then it uses the committed artifacts and LLM cache. An optional cell re-runs the LLM when `LLM_API_KEY` is present in Colab secrets.

**Sections:**

1. Problem, constraints, and what "similar" means here
2. Data overview: counts, price distribution, missingness, sample packshots
3. Preprocessing: pad-vs-crop before/after, removed boilerplate, LLM before/after table, grounding log
4. Signals: neighbor grids per signal, and histograms of raw cosine per signal showing *why* z-scoring is needed
5. Fusion: example recommendations, and weight sensitivity (how top-5 lists change as weights move)
6. Evaluation: labels, the metrics table with CIs, ablations, baselines, proxies, hubness
7. Failure cases and limitations: honest analysis
8. Scaling to 10k+ items (prose):
   - store top-k lists instead of N×N matrices
   - weighted cosine equals a dot product over concatenated √w-scaled vectors
   - ANN only around 100k+ items, and the filtered-search problem that comes with it
   - incremental indexing and stale neighbor lists
   - hybrid ranking once click data exists
9. How to reproduce

**Acceptance criteria:** "Run all" succeeds on a fresh Colab runtime with no secrets.

### Phase 8: Deployment (session 10)

`render.yaml` below is a sketch. Verify the current Blueprint syntax against Render's docs (rule 12).

```yaml
services:
  - type: web
    name: ashiana-recs-api
    runtime: python
    plan: free
    buildCommand: pip install -r api/requirements.txt
    startCommand: uvicorn api.app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: "3.11.9"
      - key: FRONTEND_ORIGINS
        sync: false
  - type: web
    name: ashiana-recs-ui
    runtime: static
    rootDir: frontend
    buildCommand: npm ci && npm run build
    staticPublishPath: dist
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
    envVars:
      - key: VITE_API_BASE_URL
        sync: false
```

**Notes**

- The API runs from the repo root so that `core/` is importable. `api/requirements.txt` must stay torch-free.
- The free web service sleeps after inactivity, and waking takes about a minute. The static site doesn't sleep. The UI's cold-start state (§10.3) covers this. Warm the API before recording the video.
- Vercel is an acceptable alternative host for the frontend. If you use it, log the switch in `DECISIONS.md`.

**Acceptance criteria**

- Both public URLs work.
- CORS is restricted to the UI origin.
- The README links both.

### Phase 9: README and demo video (session 10 + buffer)

**README outline:**

1. One-paragraph pitch and live links
2. An architecture diagram (`docs/architecture.svg`)
3. How it works: signals, fusion, category rule
4. The evaluation headline table
5. Design decisions: link `DECISIONS.md` and summarize the top five
6. Limitations and what changes at 10k+ items
7. Local setup (`make setup && make build && make api && make ui`)
8. Repo map
9. Data and image attribution

The video script is in §14.

---

## 9. API contract

Base URL comes from env. All responses are JSON. Every response includes the header `X-Bundle-Version`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | `{"status": "ok"}` (used by the Render health check and the UI wake-up ping) |
| GET | `/version` | Manifest subset: bundle version, models, default weights, n_items |
| GET | `/categories` | `[{product_type, count}]` and `[{collection, count}]` |
| GET | `/products` | `?product_type=&collection=` → `[ProductSummary]` |
| GET | `/products/{sku}` | `ProductDetail`: summary + descriptor + normalized metadata |
| GET | `/products/{sku}/similar` | Recommendations (below) |
| GET | `/eval/report` | Contents of `artifacts/eval/report.json` |
| GET | `/thumbs/{sku}.webp` | Static thumbnails via `StaticFiles`, with `Cache-Control: public, max-age=86400` |

**`GET /products/{sku}/similar` parameters:**

- `k` (int, 1..`k_max`, default `k_default`)
- `w_image`, `w_text`, `w_meta` (float ≥ 0; default = manifest default weights; normalized server-side; all-zero returns 422)
- `same_category` (bool, default `true`; `false` disables the hard filter)
- `max_price_ratio` (float > 1, optional)

**Response:**

```json
{
  "query_sku": "ASH-0042",
  "bundle_version": "…",
  "weights_used": {"image": 0.5, "text": 0.2, "meta": 0.3},
  "fallback_used": false,
  "items": [
    {
      "product": {"sku": "ASH-0017", "title": "…", "product_type": "earrings",
                  "collection": "kundan", "price_inr": 1299, "thumb_url": "/thumbs/ASH-0017.webp"},
      "score": 1.84,
      "breakdown": {
        "image": {"cosine": 0.81, "z": 2.1, "contribution": 1.05},
        "text":  {"cosine": 0.74, "z": 1.3, "contribution": 0.26},
        "meta":  {"similarity": 0.88, "z": 1.8, "contribution": 0.54}
      },
      "reasons": ["Visually similar", "Same collection: Kundan", "Similar price (₹1,299 vs ₹1,450)"],
      "fallback": false
    }
  ]
}
```

**Errors:** 404 for an unknown SKU, 422 for invalid parameters, with a clear `detail` message.

**Implementation notes:**

- Load the bundle once at startup (FastAPI lifespan) and validate array shapes against `n_items`.
- Wrap the similarity computation in `functools.lru_cache`, keyed by `(sku, rounded weights, k, filters)`.
- Set CORS from `FRONTEND_ORIGINS`.

---

## 10. Frontend specification

### 10.1 Stack

- React + Vite + TypeScript
- React Router
- TanStack Query (use `placeholderData: keepPreviousData` so lists don't flash while weights change)
- CSS Modules + `styles/tokens.css` (CSS custom properties). No UI kit.
- Charts on the under-the-hood page: Recharts
- Reorder animation: `motion` (Framer Motion) layout animations

### 10.2 Routes and views

**`/` Catalog**

- A grid of products: thumbnail, title, price.
- Filter chips for product type and collection, plus a client-side title filter.
- Clicking a product opens its product page.

**`/p/:sku` Product page.** This is the demo centerpiece, with two layers.

*Shopper layer:*
- A large image, title, price, and collection.
- A "Similar pieces" row of k=6 cards.
- A small "From a related category" badge on fallback items.

*Inspector layer* (a toggle or side panel, open by default in the demo):
- Three weight sliders (image / text / metadata) with a live normalized readout. Requests are debounced by 250 ms, and the weights are stored in URL params (`?wi=0.7&wt=0.1&wm=0.2`) so any state is shareable.
- A "Same category only" toggle and a price-ratio control.
- Per recommendation: a three-segment contribution bar showing the image/text/meta share of the score, reason chips, and raw cosine vs z on hover or focus.
- **When weights change, the cards animate to their new positions** (FLIP via `motion` layout). This is the one deliberate motion moment in the app. It answers the user's action and shows *what changed*. Respect `prefers-reduced-motion`.

**`/under-the-hood`**

- The architecture diagram
- Model and bundle versions from `/version`
- The evaluation table from `/eval/report` (methods × NDCG@5 / P@5 with CIs)
- A hubness chart
- A failure-case gallery
- Short methodology notes

**`/label`** (dev only, behind `VITE_ENABLE_LABELING`): the labeling tool described in Phase 4.

### 10.3 States

- **Cold start:** on app load, ping `/health`. If there's no response within 3 s, show a non-blocking banner: *"Starting the recommendation server. Free hosting sleeps when idle; this takes about a minute."* Retry with backoff, and remove the banner on success.
- **Errors:** say what happened and what to do, e.g. *"Couldn't load similar pieces. The server didn't respond. Retry."* Never a generic "Something went wrong."
- **Empty:** when filters match nothing, show *"No pieces match these filters"* plus a "Clear filters" action.
- **Loading:** use skeletons that match the card geometry, not spinners.

### 10.4 Design direction (propose for D6 first, then build)

**Subject.** Ashiana is a handcrafted ethnic jewelry brand, with collections like Antique, Kundan, Zircon, and Crystal.

**Audience.** Ashiana's team: a technical reviewer and the business owner.

**Primary job.** Make the recommendations feel like a real shop, while making the model's reasoning legible.

**Process.** Follow the two-pass method:
1. Propose a compact token system: 4–6 named hex colors, one or two deliberate typefaces with a type scale, a layout concept with ASCII wireframes of the catalog and product page, and 3 design principles.
2. Critique that plan against the brief, revise anything that reads generic, then present it for approval.

**Constraints**

- **Product photos are the hero.** The packshots are white-background images, so the palette and surfaces must frame them well.
- Draw visual character from the subject matter (craft, jewel tones, antique metal finishes), not from generic e-commerce templates.
- **Avoid the common generated-UI defaults:**
  - cream background + serif + terracotta accent
  - near-black + a single neon accent
  - identical rounded cards with soft grey shadows everywhere
  - all-caps eyebrow labels
  - "A · B · C" meta strings
  - "→" appended to every button
- **Spend boldness in one place:** make the inspector's contribution bars and reorder animation the memorable element, and keep everything else quiet.
- **Quality floor:** responsive, visible keyboard focus, alt text (the product title), sufficient contrast, reduced motion respected.
- Don't copy Ashiana's logo or site branding. This is an independent prototype. Name it plainly, e.g. "Similar pieces — a prototype for Ashiana."
- **Copy:** plain, sentence case, active voice, labels named from the user's perspective ("How much looks matter," not "w_image").

---

## 11. Testing and quality gates

- **Core** (`tests/core/`): the unit tests listed in Phase 3, plus a property test that rankings are unchanged when a constant is added to any Z matrix.
- **API** (`api/tests/`): endpoint contract tests, parameter validation, 404/422 paths, the no-torch import test, and a check that the bundle-version header is present.
- **Pipeline** (light tests only in CI): schema validation, normalization and synonym mapping, the boilerplate detector, the grounding check (feed a fake LLM output containing an ungrounded stone and assert it's dropped), and the price parser.
- **Frontend:** `tsc --noEmit`, `vite build`, and Vitest for weight normalization and URL-param round-tripping.
- **CI** (GitHub Actions): ruff + pytest (core, api, light pipeline) + frontend build. The heavy embedding steps don't run in CI; CI uses the committed artifacts.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Too few items per product type (top-k ≈ the whole category) | Show counts in the data report; the fallback rule; say this openly in the README and notebook |
| Sparse structured metadata (scraped titles and descriptions only) | Keyword extraction, then grounded LLM extraction with provenance, and missing-field renormalization in Gower similarity |
| LLM hallucination | Grounding check, temperature 0, a fixed template, before/after review at the Phase 2 checkpoint |
| LLM free-tier quota or model changes | Cache everything, keep the provider and model in env, throttle requests, rebuild without a key |
| Bad packshot choice (lifestyle photo picked) | Border-whiteness heuristic, contact-sheet review, manual overrides |
| Hubness (some items recommended everywhere) | Measure and report it; if severe, note centering-style corrections as future work in DECISIONS.md rather than adding complexity unprompted |
| Free API cold start during review | Cold-start banner, warm-up before the demo, a README note |
| Image rights in a public repo | D3; thumbnails only, with attribution |

---

## 13. Out of scope (do not build)

- Text-to-image or keyword semantic search
- Image-upload queries or any model running at serve time
- Complementary "complete the look" recommendations
- User accounts, carts, tracking, analytics
- Collaborative filtering or learned rankers
- ANN libraries or vector databases
- Fine-tuning any model
- A VLM-as-judge evaluation (mention it as future work in the README only)

---

## 14. Demo video script (2–3 minutes)

1. **(0:00–0:15) Problem.** Ashiana's catalog, no user data, so this is content-based cold start.
2. **(0:15–0:45) Architecture.** The diagram: offline bundle vs. online lookup, and why the API can run on a free tier with no torch.
3. **(0:45–1:45) Live demo.**
   - Open a kundan earring and point out the similar pieces with their reason chips.
   - Open the inspector and drag the "looks" weight up to watch the cards reorder.
   - Turn off same-category to show the difference.
   - Show a fallback badge on a sparse category.
   - Briefly show `/docs`.
4. **(1:45–2:30) Evaluation.**
   - The ablation table with CIs.
   - How the fused model compares with the nearest-price baseline.
   - One honest failure case and why it happens.
5. **(2:30–2:50) Scaling.** What changes at 10k+ items, and what gets added when clicks arrive.
