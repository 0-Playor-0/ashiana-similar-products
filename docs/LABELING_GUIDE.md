# Labeling guide (Phase 4)

You'll see a **query product** and a **candidate product**, shown as image + title + price +
collection, with the method that produced the candidate hidden (image-only / text-only /
meta-only / fused / a baseline — all shuffled together so the label isn't biased by knowing
which method suggested it). For each candidate, answer one question:

> **If a shopper is looking at the query product, would this candidate be a reasonable thing
> to show them as an alternative?**

Not "is this a good product" — some candidates are objectively lower quality than the query
and that's fine, the question is only about *substitutability*: could a shopper reasonably
pick this instead of the query.

## The scale

| Score | Meaning |
|---|---|
| **2** | I'd happily show this as an alternative. Same kind of piece, a shopper comparing the two would see why they're grouped together — similar style, materials, or occasion, roughly the price range they were already looking at. |
| **1** | Acceptable. Not a great match, but not wrong either — some real overlap (same product type and one clear shared trait), a shopper wouldn't be confused or annoyed to see it, just wouldn't be excited by it. |
| **0** | Wrong or irrelevant. Different product type where that matters, or no meaningful stylistic/material connection, or a jump in price/occasion that makes the pairing feel like a mistake rather than a suggestion. |

Use keyboard shortcuts `0`, `1`, `2` in the labeling tool (`/label`, dev-only route).

## Worked examples, grounded in this catalog

**Score 2** — Query: *Ashiana 92.5 Sterling Silver Blossom Ring* (₹1,650, floral motif).
Candidate: *Ashiana Silver Daisy Flower Rhinestone Studded Nail Ring* (₹550). Same product
type, same floral motif, same silver-tone material family, price in a similar band. A
shopper browsing the first would reasonably consider the second.

**Score 1** — Query: the same Blossom Ring. Candidate: *Ashiana Antique Leave and Blue Stone
Ring* (₹350). Same product type (ring), but different collection aesthetic (antique vs.
contemporary silver) and a different stone story. Not a strong match, but a shopper looking
at rings wouldn't be surprised or put off seeing it.

**Score 0** — Query: the same Blossom Ring. Candidate: *Ashiana Diwali Special! LED Crystal
Flower Chain Shubh Labh* (a home-decor door hanging, ₹450). Wrong product type entirely, and
nothing a ring shopper would consider "instead of" a ring — this project's definition of
"similar" (§1 of the roadmap) is substitutes only, and a decor item is never a substitute for
jewelry.

## Edge cases

- **Fallback candidates** (flagged `fallback: true`, from a different product type when the
  query's own type is too sparse for k candidates): judge them on the same substitutability
  question. A related-but-different type (e.g. a bangle shown for a ring query) can still
  score 1 or even 2 if the styling genuinely connects; it should score 0 if it's only in the
  pool because nothing else was available, not because it's actually a reasonable swap.
- **Price outliers**: a big price gap alone doesn't force a 0 — a shopper comparing a ₹350
  piece to a ₹3,500 piece in the *same* strong style match might still see the connection
  (score 1), but a large price gap *combined with* weak style overlap should push toward 0.
- **Out-of-stock candidates**: label purely on substitutability, not availability — stock
  status is a separate filter, not part of what "similar" means here.
- **When you genuinely can't tell** (e.g. the image is ambiguous, or the title is
  uninformative): score 1, not 0 — a 0 should mean "this is a bad suggestion," not "I
  wasn't sure." If this happens often for a specific query, flag it as a note rather than
  guessing.
- **Don't reward mere visual repetition**: two identical-looking pieces that are actually
  the same design in different metal colors are a strong 2, but two pieces that just happen
  to share a plain white studio background (nothing about the piece itself) obviously aren't
  — score on the product, not the photo's backdrop.

## What this feeds into

Labels go into `labels/relevance_labels.json` (downloaded from `/label`, committed by hand).
`pipeline/evaluate.py` (Phase 4) uses them for NDCG@5 and P@5 with bootstrap CIs, comparing
image-only / text-only / meta-only / fused-default / fused-tuned against two baselines
(random-within-type, same-type + nearest-price). See ROADMAP.md §8 Phase 4 for the full
metrics list.
