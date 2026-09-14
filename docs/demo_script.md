# Demo video script (2:50 total)

Expands ROADMAP.md §14's beat outline into exact UI actions, SKUs, and
talking points, synced to timestamps. Record locally against
`make api && make ui` (not the live Render URLs — product photography only
exists locally, per D3 in DECISIONS.md).

**Prep before hitting record:**
- Both servers up: `make api` (port 8000), `make ui` (port 5173).
- Browser window at a normal desktop width (not resized/mobile).
- Have `docs/architecture.svg` and the README's Evaluation table (§Evaluation)
  ready to alt-tab to, or screen-recorded in a second pass and edited in —
  whichever is easier for your recording setup.

---

## 1. Problem (0:00–0:15)

**Screen:** Catalog page, `http://localhost:5173/`.

**Talking points:**
> "Ashiana is a handcrafted ethnic jewelry brand with a 472-product catalog,
> but no purchase or click history — a classic cold-start problem. This is a
> content-based 'similar products' recommender built for exactly that case:
> every recommendation comes from the product itself — its photo, its
> description, its metadata — not from what other shoppers did."

---

## 2. Architecture (0:15–0:45)

**Screen:** Switch to `docs/architecture.svg` (open the file directly, or
scroll to the Architecture section of the rendered README on GitHub).

**Talking points:**
> "The pipeline splits into two halves. Offline — rerun only when the
> catalog changes — DINOv2 embeds each product photo, bge embeds an
> LLM-grounded text descriptor, and a Gower-style metric compares
> structured metadata. Each signal's similarity matrix gets z-scored and
> written to a versioned artifact bundle, committed to git.
>
> Online, the API just loads that bundle once at startup and does a
> weighted sum of three precomputed matrices — no model inference at
> request time. That's why it runs on Render's free tier with nothing
> heavier than numpy — no torch, no GPU, in production."

---

## 3. Live demo (0:45–1:45)

### 3a. Open a kundan earring, point out reason chips (0:45–1:05)

**Action:** Navigate to
`http://localhost:5173/p/1f89d63f-a6e0-4f8a-bb6e-18972d4a8516`
("Ashiana Contemporary Gold Crescent Kundan Dangle and Drop earrings for
Women"). Hover/click one of the similar-piece reason chips to show the
tooltip with real cosine/z/contribution numbers.

**Talking points:**
> "Here's a kundan earring. The similar pieces aren't a black box — each
> one shows why: 'visually similar,' 'same collection: Kundan,' 'also
> features kundan.' Clicking a signal's contribution bar shows the actual
> cosine similarity and z-score behind that reason."

### 3b. Drag the image weight up, watch the grid reorder (1:05–1:25)

**Action:** Open the Inspector. Drag "How much looks matter" from 0.60
toward the far right (~0.95) while dragging text/meta down (~0.02 / ~0.03).
Let the debounce settle (~250ms) and let the FLIP reorder animation play.

**Talking points:**
> "The inspector's sliders aren't cosmetic — they're live weights on the
> fusion formula. Pushing 'looks' up re-ranks almost the entire grid in
> real time, with the cards animating into their new order rather than
> just snapping."

*(Drag the slider back down to defaults — or just navigate away — before
the next beat.)*

### 3c. Toggle "Same category only" off (1:25–1:35)

**Action:** Navigate to
`http://localhost:5173/p/0648687f-ed22-4d6b-bf93-26b1d1211e77`
("Ashiana Diwali Special! LED Crystal Flower Chain Shubh Labh - Green," a
home_decor item). With "Same category only" checked (default), point out
all 6 results are home_decor. Uncheck it — the list changes to pull in
visually similar earrings ranked purely by score.

**Talking points:**
> "By default, similar pieces are hard-filtered to the same product type —
> a home décor item's matches are always other home décor. Turn that off,
> and it ranks the whole catalog by score alone — you can see visually
> similar earrings creep in, purely because they photograph similarly."

### 3d. Show a fallback badge (1:35–1:42)

**Prep note (not part of the recorded UI action):** With this catalog, no
product naturally triggers the fallback badge at the app's real k=6 — the
thin categories (9–10 items each) sit just above that threshold by design
(see README Limitations). To show the badge honestly, temporarily raise
`K` in `frontend/src/routes/ProductPage.tsx` from `6` to `10` right before
this shot, then change it back to `6` immediately after — the same
technique already used to verify this in DECISIONS.md. Do not leave `K`
changed in the committed code.

**Action:** With `K = 10`, navigate to
`http://localhost:5173/p/01311aee-ed32-415a-87a6-841648e1f0b5`
("Ashiana Silver Brass CZ Unisex Brooch (AS0871)," a brooch — 9 products in
that type). Scroll to the last two cards, which carry the "From a related
category" badge.

**Talking points:**
> "When a category is too thin to fill the grid — brooches only have 9
> products — it backfills from related types instead of returning fewer
> results, and says so explicitly with this badge, rather than silently
> mixing in unrelated items."

### 3e. Briefly show /docs (1:42–1:45)

**Action:** Navigate to `http://localhost:8000/docs`. A 2–3 second pan is
enough — no need to click into an endpoint.

**Talking points:**
> "The API's fully documented via FastAPI's auto-generated OpenAPI docs."

---

## 4. Evaluation (1:45–2:30)

**Screen:** README's Evaluation section (rendered on GitHub, or scrolled to
in an editor) — the results table and the two paragraphs below it.

**Talking points:**
> "Evaluated against 25 stratified queries and 595 hand-labeled pairs,
> NDCG@5 and precision@5 with bootstrap confidence intervals. The tuned
> fusion — 0.6 image, 0.1 text, 0.3 metadata — beats a same-type,
> nearest-price baseline on NDCG@5, 0.819 versus 0.618.
>
> Reported plainly: image-only is statistically indistinguishable from the
> full fusion here — this catalog's studio packshots are consistent enough
> that DINOv2 carries most of the signal on its own, with text and metadata
> adding real but smaller value. With only 25 queries, every number here
> has a wide interval — these are directional findings, not fine-grained
> claims between close methods."

**Failure case (segue into ~2:15):**

**Action (optional):** Navigate to
`http://localhost:5173/p/50883ecb-aaaf-4af6-ab3e-c0c935bd2aa7`
("Ashiana Diwali Special! Traditional Unique Designer Crystal Box") to show
the actual top-5 live — the same home_decor category from beat 3c.

**Talking points:**
> "One honest failure case: this Diwali-themed crystal box scores 0 NDCG.
> Its top-5 are other home-décor items that share the same seasonal
> framing and studio lighting, but nothing structurally similar — the
> taxonomy has no concept of 'festive novelty item,' so it can't distinguish
> a candle stand from a hanging toran beyond 'both photographed on a
> similar background.'"

---

## 5. Scaling (2:30–2:50)

**Screen:** Back to the README (Limitations → "What changes at 10k+ items"),
or just talk over the catalog page.

**Talking points:**
> "Today's catalog is 472 products — small enough that exact search over
> precomputed matrices is both fast and exactly correct. Past roughly
> 100k items, that stops being true, and a weighted sum of cosines is
> exactly a dot product over per-signal vectors pre-scaled by root-weight
> and concatenated — that's what makes an ANN index usable at all, since
> ANN libraries index under one fixed metric, not a runtime-adjustable
> weighted sum of three. And once real click data exists, the honest move
> is to blend it in as a re-ranker signal alongside content, not replace
> content-based fusion outright — content is what makes cold start work in
> the first place."

---

**Total: ~2:50.** Trim the architecture or evaluation beats first if you're
running long — the live demo (section 3) is the section most worth keeping
at full length.
