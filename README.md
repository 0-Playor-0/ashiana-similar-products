# Ashiana Similar Products (prototype)

Content-based "similar products" recommender for Ashiana's jewelry/accessories catalog.
Cold-start, item-to-item, no user behavior data. See [ROADMAP.md](ROADMAP.md) for the full
design and build plan, and [docs/DECISIONS.md](docs/DECISIONS.md) for the decision log.

This README is a placeholder until Phase 9 (see ROADMAP.md §9 for the final outline: pitch,
architecture diagram, evaluation headline, design decisions, limitations, setup, repo map,
attribution).

## Status

Phase 0 (setup + data acquisition) complete: 472 in-scope products scraped from
`https://www.ashianayouronestopshop.com` into [data/catalog.jsonl](data/catalog.jsonl).

## Local setup so far

```bash
make setup   # venv + pipeline deps + Playwright's Chromium
make data    # rebuild catalog.jsonl from the committed raw snapshot
```

`pipeline/ingest/scrape_site.py` documents how the raw snapshot was produced but is not
run by `make data` — see its module docstring and docs/DECISIONS.md.
