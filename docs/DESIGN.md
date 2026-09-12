# D6 design proposal — pass 2 (revised)

Status: **revised, pending final sign-off** (§10.4's two-pass method). Pass 1's concept was
approved; this pass self-critiques it against the brief, fixes real gaps found along the
way, and is what's asked for before any UI code gets written.

## Brief recap

- **Subject:** Ashiana — handcrafted ethnic jewelry; collections Antique, Kundan, Zircon,
  Crystal, plus (per the real catalog) Contemporary, Oxidised, 92.5 Sterling Silver.
- **Audience:** Ashiana's team — a technical reviewer and the business owner.
- **Primary job:** make the recommendations feel like a real shop, while making the model's
  reasoning legible.
- **Constraint:** product photos are the hero (white-background packshots) — palette and
  surfaces must frame them, not compete with them.

## Self-critique: what pass 1 got wrong

1. **Dark ground + gold risks reading as generic "luxury brand template,"** not specifically
   "jewelry tray." Black-and-gold is *also* the default reflex for watches, spirits, and
   premium-anything sites — it's not on the brief's explicit banned list, but it's adjacent
   to the same failure mode (a subject-agnostic "premium" reskin). Fix below: commit to a
   warm, uneven surface (patina/grain, not a flat corporate-gradient dark) and to specific
   card framing that reads as *displayed-on-a-tray*, not *floating-on-a-dark-website*.
2. **No text colors were actually specified — and one obvious pairing fails contrast
   outright.** Pass 1 named surface/accent colors but never said what color *text* is, so I
   went back and checked real WCAG contrast ratios rather than assuming the palette would
   work (see table below). Antique Gold text on Card Ivory measures **2.18:1** — a hard
   failure (needs 4.5:1). Gold must stay a fill/accent, never a text color on the light
   cards. Oxidised Silver as small secondary text on Ivory measures **3.14:1** — also fails
   at body-text size. Fixed by making Smoked Bronze do double duty as the text color on
   light surfaces (it already existed for the page ground; reusing it keeps the palette at
   6 named colors, not 7) and restricting Oxidised Silver's on-light use to non-text
   elements (hairline borders, dividers) where the accessibility bar is lower.
3. **Card treatment was left unspecified** — pass 1's "avoid soft grey shadows" was stated
   as a principle but never actually resolved into a token. Fixed below: hairline border,
   no shadow.
4. **"How much the write-up matters"** is awkward, not plain — a shopper doesn't call a
   product description a "write-up." Changed to "How much the description matters."
5. **No accessibility tokens** (focus ring, reduced-motion commitment) were named, despite
   the brief's explicit quality floor. Added below.

## Concept (kept from pass 1, sharpened)

Jewelry photography is shot against a dark backdrop — velvet, wood, brushed metal — because
that's what makes gold and stones read as luminous rather than washed out. The page shell
takes that logic rather than defaulting to a light "cream + serif + terracotta" storefront.
To keep this from collapsing into generic black-and-gold luxury branding, the ground isn't a
flat color: it's specified as a very subtle warm radial variation (center slightly lighter
than edges, like light catching an uneven oxidised-metal surface) and every card sits inside
a thin gold *hairline*, not a shadow — the visual metaphor is a piece resting in a
compartment of a display tray, not a card floating on a dark webpage.

## Colors

| Name | Hex | Role |
|---|---|---|
| Smoked Bronze | `#241C17` | Page ground (subtle warm radial variation, not flat) **and** body text color on light (Ivory) surfaces |
| Card Ivory | `#FBF7F0` | Card/surface background — every product photo sits here; also the text color on dark (Smoked Bronze) surfaces |
| Antique Gold | `#C9A55C` | Fill/accent only — CTAs, active-state fills, card hairline borders, "image" signal in the contribution bar. **Never used as text on light surfaces** (fails contrast, see below) |
| Oxidised Silver | `#8A8D8C` | "text" signal in the contribution bar; secondary text **on dark ground only** (5.0:1); non-text use only on light (dividers, disabled states) |
| Zircon Ice | `#B7DEE0` | "meta" signal in the contribution bar; focus-ring color on both light and dark |
| Garnet | `#7A2E2E` | Discount/sale badges only — the one warm-red note, echoing the red stones common across the catalog |

### Verified contrast (WCAG 2.1 relative luminance, not eyeballed)

| Pair | Ratio | Passes |
|---|---|---|
| Smoked Bronze text on Card Ivory | 15.69:1 | AAA |
| Card Ivory text on Smoked Bronze | 15.69:1 | AAA |
| Antique Gold on Smoked Bronze (icons/labels on dark) | 7.20:1 | AAA |
| Oxidised Silver on Smoked Bronze (secondary text on dark) | 5.00:1 | AA |
| Zircon Ice on Smoked Bronze | 11.60:1 | AAA |
| Garnet on Card Ivory (badge text) | 8.71:1 | AAA |
| Antique Gold on Card Ivory | **2.18:1** | **Fails — fill/accent only, never text** |
| Oxidised Silver on Card Ivory, body-text size | **3.14:1** | **Fails at text size — non-text use only** |

Three signals (image/text/meta) still map to three distinct accent hues (gold/silver/ice) so
the inspector's contribution bar reads as three genuinely different colors — the "spend
boldness in one place" instruction in practice.

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

## Card treatment (resolved, was left open in pass 1)

No drop shadow, ever. Every card is Card Ivory with a **1px Antique Gold hairline border**
(not grey, not a shadow) — the metaphor is a compartment in a display tray, not a floating
panel. Corners are barely rounded (4px, enough to soften, not enough to read as a generic
rounded-rectangle SaaS card).

## Accessibility tokens (added in pass 2)

- **Focus ring:** 2px solid Zircon Ice with a 1px Smoked-Bronze (on light) or Card-Ivory (on
  dark) inner offset ring, so the ring stays visible against either surface without needing
  a different color per context.
- **Reduced motion:** the one deliberate animation (card reorder on weight change) is
  disabled under `prefers-reduced-motion`; cards simply re-render in their new order with no
  transition. Nothing else in the app animates, so this is the only thing to gate.
- **Alt text:** every product image's alt text is the product title (already in the data,
  no extra authoring needed).

## Layout — ASCII wireframes

**Catalog (`/`)**

```
┌──────────────────────────────────────────────────────────┐
│  Ashiana — similar pieces, a prototype      [ Search... ] │
├──────────────────────────────────────────────────────────┤
│  Earrings   Necklaces   Rings   Bracelets   ...            │
│  Antique   Kundan   Zircon   Crystal   Contemporary   ...  │
├──────────────────────────────────────────────────────────┤
│  ╭───────────╮  ╭───────────╮  ╭───────────╮  ╭────────╮  │
│  │  (ivory,  │  │  (ivory,  │  │  (ivory,  │  │ (ivory,│  │
│  │  gold     │  │  gold     │  │  gold     │  │ gold   │  │
│  │  hairline)│  │  hairline)│  │  hairline)│  │hairline│  │
│  │  packshot │  │  packshot │  │  packshot │  │packshot│  │
│  ├───────────┤  ├───────────┤  ├───────────┤  ├────────┤  │
│  │ Title     │  │ Title     │  │ Title     │  │ Title  │  │
│  │ ₹1,299    │  │ ₹850      │  │ ₹2,450    │  │ ₹550   │  │
│  ╰───────────╯  ╰───────────╯  ╰───────────╯  ╰────────╯  │
│  (grid continues on the Smoked Bronze ground)              │
└──────────────────────────────────────────────────────────┘
```

**Product page (`/p/:sku`) — shopper layer + inspector**

```
┌──────────────────────────────────────────────────────────┐
│  ← Back to catalog                                        │
├───────────────────────────┬────────────────────────────── ┤
│                           │  Antique Peacock Drop Earring  │
│    ╭──────────────╮       │  ₹1,299 · Antique collection   │
│    │   (ivory,    │       │                                 │
│    │   gold       │       │  ┌ Inspector ──────────────┐   │
│    │   hairline)  │       │  │ How much looks matter    │   │
│    │   large      │       │  │ ●━━━━━○──────────  0.5   │   │
│    │   product    │       │  │ How much the description │   │
│    │   photo      │       │  │ matters                   │  │
│    ╰──────────────╯       │  │ ●━○───────────────  0.2   │   │
│                           │  │ How much details matter   │  │
│                           │  │ ●━━━○─────────────  0.3   │   │
│                           │  │ [x] Same category only     │  │
│                           │  │ Max price ratio: [ 2.0x ]  │  │
│                           │  └────────────────────────────┘ │
├──────────────────────────────────────────────────────────┤
│  Similar pieces                                            │
│  ╭───────────╮  ╭───────────╮  ╭───────────╮  ╭────────╮  │
│  │ (ivory,   │  │ (ivory,   │  │ (ivory,   │  │(ivory, │  │
│  │  gold     │  │  gold     │  │  gold     │  │ gold   │  │
│  │  hairline)│  │  hairline)│  │  hairline)│  │hairline│  │
│  │ packshot  │  │ packshot  │  │ packshot  │  │packshot│  │
│  ├───────────┤  ├───────────┤  ├───────────┤  ├────────┤  │
│  │▓▓▓▓░░░░░░░│  │▓░░░▓▓▓░░░░│  │▓▓▓░░░▓░░░░│  │░▓▓░░▓░░│  │ <- 3-segment
│  │ gold/silv/ice contribution bar, per card                │  │    bar
│  │ Title              ₹1,450                                │
│  │ Visually similar · Same collection: Kundan               │
│  │                                    [from related category]│ <- fallback badge
│  ╰───────────╯  ╰───────────╯  ╰───────────╯  ╰────────╯  │
└──────────────────────────────────────────────────────────┘
```

## Three design principles (unchanged — held up under critique)

1. **The piece is the point.** Product photography stays the largest, brightest element on
   every screen. UI chrome — nav, filters, labels — recedes into the Smoked Bronze ground so
   nothing on the page competes with the jewelry itself for attention.
2. **Show the seams.** The inspector layer is where this app is honest about being a model,
   not a stylist. Contribution bars use hard-edged segments and real numbers (cosine, z),
   not soft rounded "AI vibes" pills — the shift from the warm shopper layer to the more
   diagrammatic inspector layer is itself a legibility cue: "you are now looking at how this
   was computed."
3. **One motion, one moment.** The card-reorder animation when a weight slider moves is the
   *only* deliberate motion in the app (and is skipped entirely under `prefers-reduced-
   motion`). Nothing else transitions, fades, or bounces — that restraint is what makes the
   one animation that exists actually mean something.

## Explicitly avoided (per the brief's list of generated-UI defaults)

Cream + serif + terracotta (inverted to dark ground + warm gold, not light); near-black +
single neon accent (three distinct jewel-tone accents, not one neon); identical rounded
cards with soft grey shadows (hairline border, no shadow, 4px corners — resolved in pass 2,
was only a stated intention in pass 1); all-caps eyebrow labels (sentence case throughout);
"A · B · C" meta strings ("₹1,299 · Antique collection" is the one deliberate two-fact
exception, not a run of three-plus fragments); "→" appended to buttons (plain verbs — "See
similar pieces," not "See similar pieces →").

## Copy fixed in pass 2

"How much the write-up matters" → **"How much the description matters"** — a shopper doesn't
call a product description a "write-up."
