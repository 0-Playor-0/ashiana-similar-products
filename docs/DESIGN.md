# D6 design — "light ground, dark bands, bold moments" (redo, approved)

Status: **implemented, final visual sign-off pending a live click-through** (§10.4's two-pass
method). This replaces an earlier direction ("velvet tray" — dark ground, jewel-tone accents)
that was approved through pass 2, implemented, and then rejected by the user on visual review:
"doesn't match what I want." This document is the redo that followed, run through the same
two-pass process from scratch.

## Brief recap

- **Subject:** Ashiana — handcrafted ethnic jewelry; collections Antique, Kundan, Zircon,
  Crystal, plus (per the real catalog) Contemporary, Oxidised, 92.5 Sterling Silver.
- **Audience:** Ashiana's team — a technical reviewer and the business owner.
- **Primary job:** make the recommendations feel like a real shop, while making the model's
  reasoning legible.
- **Additional input for the redo:** the user attached screenshots of a generic Figma
  fashion-e-commerce template (bold black type, flat white cards, dense polished grid) and
  asked for a fusion of that template's boldness/polish with the *actual* Ashiana storefront's
  real structure and palette — fetched and studied live at ashianayouronestopshop.com, not
  guessed. Real colors below are sampled via computed styles, not eyeballed.

## Research: what the real site actually does

Sampled via `getComputedStyle`, not screenshots-and-guessing:

| Element | Value |
|---|---|
| Page ground | `#FFF9F5` — warm ivory |
| Secondary band (trust-badge strip) | `#F2E5D9` — soft beige-tan |
| Dark band (announcement bar, footer, testimonial-card frame) | `#643307` — deep umber |
| Primary CTA fill ("Buy Now", white text) | `#DD8130` — burnt amber |
| Discount text | `#12853D` green (used inconsistently — sometimes amber instead) |
| Display heading font | Yeseva One (chunky bold serif) |
| Body font | Inter |

Content rhythm confirmed by browsing the live site: hero carousel → Featured Products →
"Ashiana by Collection" (a 4-across model-photography grid: Antique/Zircon/Crystal/Kundan) →
beige trust-badge strip → "Charm Jewellery" (large split promo) → "Our Categories" (circular
icon strip) → "New Season Styles" (banner + product cards with a tinted footer band) →
testimonials (dark-umber card carousel) → "Ashiana By Shagun" (beige + deep-plum/gold-script
brand panel) → dark umber footer. Cards are flat — no border, no shadow.

**The tension this creates, named up front:** this palette (cream + serif + warm-amber) sits
close to the brief's #1 banned default, "cream background + serif + terracotta accent."
Sourcing the hex values from the real site doesn't automatically escape that — a generic
template built from different real hex values would still look generic if the *structure*
matches. Two concrete, non-color choices do the actual work of escaping it (see Principles).

Routes, components, and interaction logic are unchanged from Phase 6 — this is a token/visual
redo only, not a rebuild. "Content rhythm" translates into the catalog page's filter-chip
treatment and a bold intro header, not into new marketing sections (no hero carousel,
testimonials, or brand-story block were added — those don't exist in this prototype's IA and
adding them would mean fabricating copy/imagery this project doesn't have, against rule 7).

## Colors

| Name | Hex | Role |
|---|---|---|
| Ivory | `#FFF8F2` | Page ground — light throughout, not dark |
| Sand | `#F3E6D8` | Secondary surface — section bands, card-footer tint, active-chip fill, dividers |
| Umber | `#4A2712` | Primary text on light; dark-band background (nav, inspector, cold-start banner); "text" signal color |
| Amber | `#C97327` | Accent/outline/focus-ring/"image" signal only — **never a text-bearing solid fill** (see contrast table) |
| Garnet | `#7A2E2E` | Rare accent; "meta" signal color — echoes the red stones common across the catalog |

Amber and Garnet are both real gemstones — deliberate, reinforcing "jewelry" rather than a
generic warm palette. The as-sampled site value for the CTA amber was `#DD8130`; it's deepened
here to `#C97327` specifically so the focus ring clears WCAG 1.4.11's 3:1 non-text-contrast
bar against *both* Ivory and Umber (see below) — the one hex changed between pass 1 and pass 2.

### WCAG contrast — computed (relative-luminance formula), not eyeballed

| Pair | Ratio | Verdict |
|---|---|---|
| Umber text on Ivory | 12.55:1 | AAA |
| Ivory text on Umber | 12.55:1 | AAA |
| Umber text on Sand | 10.77:1 | AAA |
| Sand text on Umber | 10.77:1 | AAA |
| Garnet text on Ivory | 8.84:1 | AAA |
| Garnet text on Sand | 7.59:1 | AAA |
| Ivory text on Garnet (filled badge) | 8.84:1 | AAA |
| Amber text on Ivory | **2.84:1** | **Fails — never used** |
| White text on Amber fill | **2.99:1** | **Fails — real site does this; we don't** |
| Umber text on Amber fill | 3.75:1 | Passes 3:1 (bold/large labels only); short of 4.5:1, so never used for small dense text |
| Amber focus ring on Ivory (deepened value) | 3.35:1 | Passes WCAG 1.4.11 non-text contrast |
| Amber focus ring on Umber (deepened value) | 3.75:1 | Passes WCAG 1.4.11 non-text contrast |
| Garnet on Umber | 1.42:1 | Fails badly — never paired; Garnet only appears on light surfaces or as a non-text chart/bar fill |

**Resolution driven by the two real failures:** Amber never carries visible text as a solid
fill anywhere in the app. It's an outline (filter chips, buttons, focus ring), a non-text
accent (one signal-bar segment, a chart bar with no text on top of it), or paired with Umber
text at bold/large sizes only. Every button/chip that needs a filled "active" state uses
Sand fill + Umber text + Amber border instead — verified via the table above, not assumed.

**A real regression caught and fixed during implementation:** axe-core flagged the catalog
page's "472 pieces" count text at 4.38:1 (needs 4.5:1) — `opacity: 0.65` on Umber-on-Ivory text
dims it further than it looks. Audited every `opacity` value used on text across the app;
raised every one below ~0.70 (the real computed threshold, not a round number) to 0.72, which
composites to ≥5:1 in every case checked. Confirmed via a second axe-core pass: 0 violations on
`/`, `/p/:sku`, `/under-the-hood`.

**Accepted tradeoff, not fixed:** Umber and Garnet (the "text" and "meta" signal colors) are
both dark, muted, warm-toned hues that could read similarly to red-green colorblind viewers —
a real weakness the old gold/silver/ice trio didn't have (that one spanned warm/neutral/cool).
No cool hue was imported to fix this, since nothing cool exists anywhere on the real site and
doing so would undercut the "sourced, not generic" reasoning above. Mitigated by what the
implementation already does regardless of this redo: the three contribution-bar segments have
a fixed left-to-right order (image/text/meta) and the tooltip/`aria-label` always states the
signal by name — color reinforces, it isn't the only channel (WCAG 1.4.1).

## Typography

- **Display — Bitter**, a sturdy slab serif: real character, reads confident and crafted at
  large sizes. Chosen specifically to be neither the real site's own Yeseva One (avoiding a
  literal copy) nor the rejected direction's Fraunces (a genuinely fresh choice, not a rerun).
- **Body/UI — Inter**, unchanged; both references already agree on it.

| Token | Size / weight | Use |
|---|---|---|
| display | 56px / 700 | Catalog page's bold intro title |
| h1 | 34px / 700 | Product title, page titles |
| h2 | 22px / 600 | Section headers |
| body | 15px / 400 (Inter) | Descriptions, filters |
| small | 13px / 400 (Inter) | Prices, metadata |
| micro | 11px / 600 (Inter) | Badges, reason chips — sentence case, never all-caps |

## Layout concept — "light ground, dark bands, bold moments"

The structural opposite of the rejected direction: the app stays Ivory throughout — white-
background packshots need a light stage, and the real storefront itself is light. Boldness
comes from type scale and solid color fills, not from darkening the whole page. **The one
dark-Umber band is persistent, not a one-off**: it's the nav header on every route *and* the
product page's inspector panel *and* the cold-start banner — the same material reused as a
structural signature, echoing how the real site itself uses dark umber for its own nav/
announcement bar and footer. Cards are flat: no border in the literal sense, just a barely-
perceptible Sand hairline (1.17:1 against Ivory — near-imperceptible, reads as a soft edge, not
a frame) — whitespace does the separating work, matching the real site's own card treatment.

```
CATALOG (/)
┌──────────────────────────────────────────────────────────┐
│ Similar pieces — a prototype for Ashiana     Catalog  UTH │  ← Umber band, Ivory text,
├──────────────────────────────────────────────────────────┤    every page
│  Find your next favourite piece                            │  Bitter 56px/700, Umber
│  Filter by type or collection, or search by name.          │
│  (Earrings 338) (Necklaces 78) ...             [Search]    │  amber-outline pill chips,
├──────────────────────────────────────────────────────────┤  Umber text, Sand fill when active
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐               │
│  │ ivory, flat, near-imperceptible sand hairline │         │
│  ├────────┤ ├────────┤ ├────────┤ ├────────┤               │
│  │ Title    ₹1,299 (bold Umber)                  │         │
│  └────────┘ └────────┘ └────────┘ └────────┘               │
└──────────────────────────────────────────────────────────┘

PRODUCT PAGE (/p/:sku)
┌──────────────────────────────────────────────────────────┐
│  ← Back to catalog                                         │
├───────────────────────────┬─────────────────────────────── ┤
│                            │ Antique Peacock Drop Earring   │  Bitter, bold
│    ivory, flat, large      │ ₹1,299 · Antique collection    │
│    product photo           ├─ Inspector ───────────────────┤  ← Umber dark band,
│                            │ How much looks matter   0.5   │    Ivory text — same
│                            │ ●━━━━━○────────                │    material as the nav
│                            │ How much the description       │    band above it
│                            │ matters                  0.2   │
│                            │ ●━○───────────────              │
│                            │ How much details matter  0.3   │
│                            │ ●━━━○─────────────              │
│                            │ [x] Same category only          │
│                            │ Max price ratio: [ 2.0x ]       │
│                            └────────────────────────────────┘│
├──────────────────────────────────────────────────────────┤
│  Similar pieces                                              │  sentence case, bold
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                │
│  │ivory, flat│         │         │         │                │
│  ├────────┤ ├────────┤ ├────────┤ ├────────┤                │
│  │▓▓▓▓░░░░│ │░▓░▓▓▓░░│ │▓▓▓░░░▓░│ │░▓▓░░▓░░│  ← amber/umber/ │
│  │ Title      ₹1,450                          │    garnet bar│
│  │ Visually similar · Also features zircon     │              │
│  │                          [From related category]│         │
│  └────────┘ └────────┘ └────────┘ └────────┘                │
└──────────────────────────────────────────────────────────┘
```

## Three design principles

1. **Light does the heavy lifting.** An airy Ivory ground throughout — like the real
   storefront, and because white-background packshots need a light stage to read cleanly.
   Warmth comes from tone (Ivory → Sand → Umber), not from darkness.
2. **Bold where it counts, structural where it repeats.** Figma-level confidence — a big slab
   serif, real numerals, solid-fill accents — concentrated on a few moments (page titles,
   primary actions, contribution bars). The dark Umber band is a *repeating structural
   signature* (nav, inspector, status banner), not competing boldness — it's a frame, not a
   flourish.
3. **Earn the resemblance, don't default to it.** Because the real brand's own palette already
   sits close to a generic-UI default, every color and font traces to something specific
   actually observed (a sampled hex, a real button convention) or a deliberate departure from
   it (Bitter instead of the site's own Yeseva One; bold 56px instead of the delicate serif a
   generic version of this palette would reach for) — not a generic "warm boutique" reflex.

## Generic-defaults checklist

| Banned default | Status |
|---|---|
| Cream + serif + terracotta | Addressed above — sourced values, persistent dark band, bold execution differentiate it |
| Near-black + single neon accent | N/A — opposite direction |
| Identical rounded cards, soft grey shadow | Avoided — flat, near-borderless cards |
| All-caps eyebrow labels | Caught in pass 2: an early wireframe sketch wrote "SIMILAR PIECES" in caps as shorthand for "bold" — corrected to sentence case, larger/bolder weight instead |
| "A · B · C" meta strings | Only the one justified two-fact exception ("₹1,299 · Antique collection") |
| "→" on buttons | None used |

## Accessibility tokens

- **Focus ring:** a single 2px solid Amber ring (deepened specifically so one color clears
  3:1 against both Ivory and Umber — see contrast table — no per-surface variant needed).
- **Reduced motion:** unchanged from Phase 6 — the card-reorder animation (`motion`'s `layout`
  prop, wrapped in `MotionConfig reducedMotion="user"`) is the only deliberate animation and is
  disabled under `prefers-reduced-motion`.
- **Alt text:** every product image's alt text is the product title.
