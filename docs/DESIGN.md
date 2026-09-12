# D6 design proposal — pass 1

Status: **draft, pending user approval** (§10.4's two-pass method). This is pass 1 (propose);
pass 2 (self-critique against the brief, revise, re-present) happens after feedback on this
pass. No UI code has been written yet.

## Brief recap

- **Subject:** Ashiana — handcrafted ethnic jewelry; collections Antique, Kundan, Zircon,
  Crystal, plus (per the real catalog) Contemporary, Oxidised, 92.5 Sterling Silver.
- **Audience:** Ashiana's team — a technical reviewer and the business owner.
- **Primary job:** make the recommendations feel like a real shop, while making the model's
  reasoning legible.
- **Constraint:** product photos are the hero (white-background packshots) — palette and
  surfaces must frame them, not compete with them.

## Concept: the velvet tray, not the daylight storefront

Jewelry photography is traditionally shot against a dark backdrop — velvet, wood, brushed
metal — because that's what makes gold and stones read as luminous rather than washed out.
Most generated e-commerce UI defaults to a light shell (the "cream + serif + terracotta"
pattern this brief explicitly warns against). Inverting that — a warm, dark ground holding
bright white product cards — is a choice that comes from how the *subject itself* is
normally photographed, not a generic dark-mode reskin. The product cards stay light (the
packshots need that to look right); the page shell around them goes dark and warm, like a
tray lined in oxidised metal.

## Colors

| Name | Hex | Role |
|---|---|---|
| Smoked Bronze | `#241C17` | Page ground — warm near-black, not pure black (avoids the "near-black + neon" default) |
| Card Ivory | `#FBF7F0` | Card/surface background — where every product photo sits |
| Antique Gold | `#C9A55C` | Primary accent — CTAs, active states, the "image" signal in the contribution bar |
| Oxidised Silver | `#8A8D8C` | Secondary accent — the "text" signal in the contribution bar, secondary text on dark ground |
| Zircon Ice | `#B7DEE0` | Tertiary accent — the "meta" signal in the contribution bar, cool counterpoint to the gold/bronze warmth |
| Garnet | `#7A2E2E` | Sparingly: sale/discount badges, the one warm-red note (echoes the red stones common across the catalog) |

Three signals (image/text/meta) map to three distinct accent hues (gold/silver/ice) so the
inspector's contribution bar reads as three genuinely different colors, not three shades of
one accent — this is the "spend boldness in one place" instruction in practice.

## Typography

- **Display/headings — Fraunces** (a warm, slightly idiosyncratic serif with real character
  in its curves — not Georgia/Playfair, which is what "generic serif elegance" usually
  means in practice). Used for product titles, section headers, the hero.
- **UI/body — Inter.** Clean, humanist, does the actual work: prices, filters, buttons,
  the inspector's numbers and labels.

| Token | Size | Weight | Typeface | Use |
|---|---|---|---|---|
| display | 40px / 1.1 | 600 | Fraunces | Hero moments only |
| h1 | 28px / 1.2 | 500 | Fraunces | Product title, page title |
| h2 | 20px / 1.3 | 500 | Fraunces | Section headers ("Similar pieces") |
| body | 15px / 1.5 | 400 | Inter | Descriptions, filters |
| small | 13px / 1.4 | 400 | Inter | Prices on cards, metadata |
| micro | 11px / 1.3 | 500 | Inter | Badges, reason chips — sentence case, never all-caps |

## Layout — ASCII wireframes

**Catalog (`/`)**

```
┌──────────────────────────────────────────────────────────┐
│  Ashiana — similar pieces, a prototype      [ Search... ] │
├──────────────────────────────────────────────────────────┤
│  Earrings   Necklaces   Rings   Bracelets   ...            │
│  Antique   Kundan   Zircon   Crystal   Contemporary   ...  │
├──────────────────────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌────────┐  │
│  │  (ivory)  │  │  (ivory)  │  │  (ivory)  │  │ (ivory)│  │
│  │  packshot │  │  packshot │  │  packshot │  │packshot│  │
│  ├───────────┤  ├───────────┤  ├───────────┤  ├────────┤  │
│  │ Title     │  │ Title     │  │ Title     │  │ Title  │  │
│  │ ₹1,299    │  │ ₹850      │  │ ₹2,450    │  │ ₹550   │  │
│  └───────────┘  └───────────┘  └───────────┘  └────────┘  │
│  (grid continues on the Smoked Bronze ground)              │
└──────────────────────────────────────────────────────────┘
```

**Product page (`/p/:sku`) — shopper layer + inspector**

```
┌──────────────────────────────────────────────────────────┐
│  ← Back to catalog                                        │
├───────────────────────────┬────────────────────────────── ┤
│                           │  Antique Peacock Drop Earring  │
│    ┌──────────────┐       │  ₹1,299 · Antique collection   │
│    │   (ivory)    │       │                                 │
│    │   large      │       │  ┌ Inspector ──────────────┐   │
│    │   product    │       │  │ How much looks matter    │   │
│    │   photo      │       │  │ ●━━━━━○──────────  0.5   │   │
│    │              │       │  │ How much the write-up    │   │
│    └──────────────┘       │  │ matters                   │  │
│                           │  │ ●━○───────────────  0.2   │   │
│                           │  │ How much details matter   │  │
│                           │  │ ●━━━○─────────────  0.3   │   │
│                           │  │ [x] Same category only     │  │
│                           │  │ Max price ratio: [ 2.0x ]  │  │
│                           │  └────────────────────────────┘ │
├──────────────────────────────────────────────────────────┤
│  Similar pieces                                            │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌────────┐  │
│  │ (ivory)   │  │ (ivory)   │  │ (ivory)   │  │(ivory) │  │
│  │ packshot  │  │ packshot  │  │ packshot  │  │packshot│  │
│  ├───────────┤  ├───────────┤  ├───────────┤  ├────────┤  │
│  │▓▓▓▓░░░░░░░│  │▓░░░▓▓▓░░░░│  │▓▓▓░░░▓░░░░│  │░▓▓░░▓░░│  │ <- 3-segment
│  │ gold/silv/ice contribution bar, per card                │  │    bar
│  │ Title              ₹1,450                                │
│  │ Visually similar · Same collection: Kundan               │
│  │                                    [from related category]│ <- fallback badge
│  └───────────┘  └───────────┘  └───────────┘  └────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Three design principles

1. **The piece is the point.** Product photography stays the largest, brightest element on
   every screen. UI chrome — nav, filters, labels — recedes into the Smoked Bronze ground so
   nothing on the page competes with the jewelry itself for attention.
2. **Show the seams.** The inspector layer is where this app is honest about being a model,
   not a stylist. Contribution bars use hard-edged segments and real numbers (cosine, z),
   not soft rounded "AI vibes" pills — the shift from the warm shopper layer to the more
   diagrammatic inspector layer is itself a legibility cue: "you are now looking at how this
   was computed."
3. **One motion, one moment.** The card-reorder animation when a weight slider moves is the
   *only* deliberate motion in the app. Nothing else transitions, fades, or bounces. That
   restraint is what makes the one animation that exists actually mean something, instead of
   competing with five other "polish" animations for the viewer's attention.

## Explicitly avoided (per the brief's list of generated-UI defaults)

Cream + serif + terracotta (inverted to dark ground + warm gold, not light); near-black +
single neon accent (three distinct jewel-tone accents, not one neon); identical rounded
cards with soft grey shadows (ivory cards on a dark ground read as lit trays, not floating
white rectangles); all-caps eyebrow labels (sentence case throughout, including the micro
type-scale step); "A · B · C" meta strings (metadata is written as prose — "₹1,299 ·
Antique collection" is the one deliberate exception, a genuine visual separator between two
short facts, not a run of three-plus fragments); "→" appended to buttons (button labels are
plain verbs — "See similar pieces," not "See similar pieces →").

## Open for pass 2

Things I'd specifically like feedback on before revising: whether the dark-ground concept
reads as "jewelry tray" or just "generic dark mode" without more visual context than ASCII
can convey; whether Fraunces is too idiosyncratic for the business-owner half of the
audience; whether Garnet needs a larger role or is fine staying rare.
