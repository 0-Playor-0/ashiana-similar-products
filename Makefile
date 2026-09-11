.PHONY: setup data build eval api ui test lint

VENV := .venv/bin

setup:
	uv venv --python 3.11 .venv
	$(VENV)/pip install -r requirements-pipeline.txt
	$(VENV)/python -m playwright install chromium

# Re-scraping is not automated (see pipeline/ingest/scrape_site.py header and
# docs/DECISIONS.md) — the WAF blocks non-browser clients, so the raw snapshot
# under data/raw/ was collected interactively and is committed. `make data`
# rebuilds catalog.jsonl from that committed snapshot.
data:
	$(VENV)/python -m pipeline.ingest.merge_raw
	$(VENV)/python -m pipeline.clean

build:
	$(VENV)/python -m pipeline.build

eval:
	$(VENV)/python -m pipeline.evaluate

api:
	$(VENV)/uvicorn api.app.main:app --reload --port 8000

ui:
	cd frontend && npm run dev

test:
	$(VENV)/pytest
	$(VENV)/ruff check .

lint:
	$(VENV)/ruff check .
