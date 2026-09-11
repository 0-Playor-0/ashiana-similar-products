"""Phase 2: boilerplate stripping -> LLM design-attribute extraction -> a
deterministic descriptor sentence per product (§8 Phase 2).

Two independent steps, runnable separately:
  strip_boilerplate()  — no API key needed, safe to preview any time.
  run_llm_descriptors() — needs LLM_API_KEY (D4: Groq, see docs/DECISIONS.md).

Both steps read/write data/catalog.jsonl in place (same pattern as
pipeline/apply_image_review.py), plus write review artifacts under
artifacts/eval/ for the Phase 2 checkpoint.

LLM provider is Groq (roadmap §3's other LOCKED option besides Gemini),
through the OpenAI-compatible endpoint the roadmap originally specified —
see docs/DECISIONS.md ("D4 final pivot: Groq") for why Gemini's free tier
didn't work out (both the OpenAI-compat key format issue and, separately, a
hard 20-requests/day cap on every model tried).
"""

import hashlib
import json
import os
import random
import re
import time

import yaml
from openai import APIStatusError, APITimeoutError, OpenAI
from pydantic import BaseModel, Field, ValidationError
from tqdm import tqdm

from pipeline.paths import ARTIFACTS_DIR, CONFIG_DIR, DATA_DIR
from pipeline.schema import Product

SETTINGS = yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text())
TAXONOMY = yaml.safe_load((CONFIG_DIR / "taxonomy.yaml").read_text())

BOILERPLATE_MIN_SHARE = SETTINGS["text"]["boilerplate_min_share"]
PROMPT_VERSION = SETTINGS["llm"]["prompt_version"]
TEMPERATURE = SETTINGS["llm"]["temperature"]
MIN_INTERVAL_S = SETTINGS["llm"]["min_interval_s"]
MAX_RETRIES = SETTINGS["llm"]["max_retries"]
REQUEST_TIMEOUT_S = 30.0

DESCRIPTORS_CACHE_PATH = ARTIFACTS_DIR / "descriptors.json"
REMOVED_BOILERPLATE_PATH = ARTIFACTS_DIR / "eval" / "removed_boilerplate.json"
GROUNDING_LOG_PATH = ARTIFACTS_DIR / "eval" / "grounding_log.json"
BEFORE_AFTER_PATH = ARTIFACTS_DIR / "eval" / "descriptor_before_after.json"

SYSTEM_PROMPT = (
    "You extract design attributes from a jewelry product listing. Use only "
    "information explicitly present in the input; do not infer or embellish. "
    "If a field has no support in the input, return an empty list."
)


class ExtractedAttrs(BaseModel):
    materials: list[str] = Field(default_factory=list)
    stones: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)


class LLMDescriptor(BaseModel):
    motifs: list[str] = Field(default_factory=list)
    style: list[str] = Field(default_factory=list)
    finish: list[str] = Field(default_factory=list)
    occasion: list[str] = Field(default_factory=list)
    design_features: list[str] = Field(default_factory=list)
    extracted: ExtractedAttrs = Field(default_factory=ExtractedAttrs)


# ---------------------------------------------------------------------------
# Boilerplate stripping (no API key needed)
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


# Product-noun words that vary the same templated sentence per product
# ("this latest trendy and stylish EARRING/RING/NECKLACE makes an undeniable
# statement...") — collapsed to a placeholder before frequency-counting so
# the template itself is recognized as boilerplate, not just exact matches.
# Built from what actually recurs in the scraped descriptions (see
# docs/DECISIONS.md), not guessed.
_PRODUCT_NOUN_RE = re.compile(
    r"\b("
    r"earrings?|ear\s?cuffs?|neck\s?pieces?|necklaces?|rings?|bracelets?|"
    r"jhumkas?|jhumkis?|bangles?|kadas?|brooch(?:es)?|pendants?|"
    r"hair\s?bands?|hair\s?clips?|hair\s?combs?|hair\s?pins?|"
    r"cuffs?|watch(?:es)?|jewell?ery|toran|hangings?"
    r")\b",
    re.IGNORECASE,
)


def _normalize_sentence(sentence: str) -> str:
    normalized = re.sub(r"\s+", " ", sentence.lower()).strip()
    return _PRODUCT_NOUN_RE.sub("ITEM", normalized)


def strip_boilerplate(products: list[Product]) -> tuple[dict[str, str], dict]:
    """Returns (sku -> cleaned description, removed-boilerplate report)."""
    per_product_sentences: dict[str, list[str]] = {}
    doc_freq: dict[str, int] = {}
    example_sentence: dict[str, str] = {}

    for p in products:
        if not p.description_raw:
            continue
        sentences = _split_sentences(p.description_raw)
        per_product_sentences[p.sku] = sentences
        seen = set()
        for s in sentences:
            key = _normalize_sentence(s)
            if key not in seen:
                doc_freq[key] = doc_freq.get(key, 0) + 1
                seen.add(key)
                example_sentence.setdefault(key, s)

    n = len(products)
    boilerplate_keys = {
        key for key, count in doc_freq.items() if count / n >= BOILERPLATE_MIN_SHARE
    }

    cleaned: dict[str, str] = {}
    for p in products:
        sentences = per_product_sentences.get(p.sku, [])
        kept = [s for s in sentences if _normalize_sentence(s) not in boilerplate_keys]
        cleaned[p.sku] = " ".join(kept)

    report = {
        "boilerplate_min_share": BOILERPLATE_MIN_SHARE,
        "n_products": n,
        "removed_sentences": sorted(
            (
                {
                    "template": key,
                    "example": example_sentence[key],
                    "n_products": count,
                    "share": round(count / n, 4),
                }
                for key, count in doc_freq.items()
                if key in boilerplate_keys
            ),
            key=lambda r: -r["n_products"],
        ),
    }
    return cleaned, report


# ---------------------------------------------------------------------------
# LLM descriptor extraction
# ---------------------------------------------------------------------------


def _cache_key(input_text: str, model: str) -> str:
    payload = f"{input_text}\x00{PROMPT_VERSION}\x00{model}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_cache() -> dict:
    if DESCRIPTORS_CACHE_PATH.exists():
        return json.loads(DESCRIPTORS_CACHE_PATH.read_text())
    return {}


def _save_cache(cache: dict) -> None:
    DESCRIPTORS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DESCRIPTORS_CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False))


_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "llm_descriptor",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "motifs": {"type": "array", "items": {"type": "string"}},
                "style": {"type": "array", "items": {"type": "string"}},
                "finish": {"type": "array", "items": {"type": "string"}},
                "occasion": {"type": "array", "items": {"type": "string"}},
                "design_features": {"type": "array", "items": {"type": "string"}},
                "extracted": {
                    "type": "object",
                    "properties": {
                        "materials": {"type": "array", "items": {"type": "string"}},
                        "stones": {"type": "array", "items": {"type": "string"}},
                        "colors": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["materials", "stones", "colors"],
                    "additionalProperties": False,
                },
            },
            "required": [
                "motifs",
                "style",
                "finish",
                "occasion",
                "design_features",
                "extracted",
            ],
            "additionalProperties": False,
        },
    },
}


def _call_llm(client: OpenAI, model: str, user_input: str, retry_note: str = "") -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input + retry_note},
    ]
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=TEMPERATURE,
                response_format=_RESPONSE_FORMAT,
                timeout=REQUEST_TIMEOUT_S,
            )
            return resp.choices[0].message.content
        except APITimeoutError as e:
            # A hard client-side timeout — always retryable.
            last_err = e
            time.sleep(min(2**attempt, 30))
            continue
        except APIStatusError as e:
            last_err = e
            status = getattr(e, "status_code", None)
            if status in _RETRYABLE_STATUS or status is None:
                time.sleep(min(2**attempt, 30))
                continue
            raise
    raise last_err


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _is_grounded(term: str, text_norm: str, synonyms: dict[str, str]) -> bool:
    term_norm = term.lower().strip()
    for phrase, canon in synonyms.items():
        if phrase in term_norm:
            term_norm = term_norm.replace(phrase, canon)
    return term_norm in text_norm


def _apply_grounding_check(
    descriptor: LLMDescriptor, source_text: str, synonyms: dict[str, str]
) -> tuple[LLMDescriptor, dict]:
    text_norm = source_text.lower()
    for phrase, canon in synonyms.items():
        if phrase in text_norm:
            text_norm = text_norm.replace(phrase, canon)

    dropped = {"materials": [], "stones": [], "colors": []}
    for field in ("materials", "stones", "colors"):
        terms = getattr(descriptor.extracted, field)
        grounded = [t for t in terms if _is_grounded(t, text_norm, synonyms)]
        dropped[field] = [t for t in terms if t not in grounded]
        setattr(descriptor.extracted, field, grounded)

    flagged_ungrounded = []
    for field in ("motifs", "style", "finish", "occasion", "design_features"):
        for term in getattr(descriptor, field):
            if not _is_grounded(term, text_norm, synonyms):
                flagged_ungrounded.append({"field": field, "term": term})

    log = {"dropped_extracted": dropped, "flagged_ungrounded_not_dropped": flagged_ungrounded}
    return descriptor, log


def _strip_taxonomy_words(title: str, taxonomy: dict) -> str:
    words_to_strip = set()
    for vocab_key in ("materials_vocab", "stones_vocab", "colors_vocab"):
        words_to_strip.update(w.replace("_", " ") for w in taxonomy[vocab_key])
    words_to_strip.update(v.lower() for v in taxonomy["product_type_map"].values())
    words_to_strip.update(v.lower() for v in taxonomy["collection_map"].values())

    result = title
    for word in sorted(words_to_strip, key=len, reverse=True):
        result = re.sub(rf"\b{re.escape(word)}\b", "", result, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", result).strip()


def _build_descriptor_sentence(descriptor: LLMDescriptor, title: str, taxonomy: dict) -> str:
    parts = []
    for label, field in [
        ("Motifs", "motifs"),
        ("Style", "style"),
        ("Finish", "finish"),
        ("Occasion", "occasion"),
        ("Features", "design_features"),
    ]:
        values = getattr(descriptor, field)
        if values:
            parts.append(f"{label}: {', '.join(values)}")
    if parts:
        return " ".join(parts)
    return _strip_taxonomy_words(title, taxonomy) or title


def run_llm_descriptors(products: list[Product], cleaned_descriptions: dict[str, str]) -> None:
    api_key = os.environ.get("LLM_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL")
    model = os.environ.get("LLM_MODEL")
    if not api_key:
        raise RuntimeError(
            "LLM_API_KEY is not set. Add it to .env (gitignored) and export it, "
            "e.g. `set -a && source .env && set +a`, before running this."
        )

    # Explicit per-request timeout: earlier debugging (see DECISIONS.md) found
    # requests that hang with no bytes back rather than erroring — without a
    # timeout that's unrecoverable, but with one it becomes just another
    # retryable failure.
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=REQUEST_TIMEOUT_S)
    cache = _load_cache()
    synonyms = TAXONOMY["synonyms"]

    grounding_log: dict[str, dict] = {}
    updated: list[Product] = []
    api_calls_made = 0

    for p in tqdm(products, desc="LLM descriptors"):
        description = cleaned_descriptions.get(p.sku, "")
        input_text = f"{p.title}\n{description}".strip()
        key = _cache_key(input_text, model)

        if key in cache:
            raw_output = cache[key]["output"]
        else:
            api_calls_made += 1
            raw_output = _call_llm(client, model, input_text)
            try:
                LLMDescriptor.model_validate_json(_strip_json_fences(raw_output))
            except ValidationError as e:
                raw_output = _call_llm(
                    client,
                    model,
                    input_text,
                    retry_note=f"\n\nYour previous response was invalid: {e}. "
                    "Return only the corrected JSON object.",
                )
            cache[key] = {
                "input": input_text,
                "output": raw_output,
                "model": model,
                "prompt_version": PROMPT_VERSION,
            }
            _save_cache(cache)
            time.sleep(MIN_INTERVAL_S)

        descriptor = LLMDescriptor.model_validate_json(_strip_json_fences(raw_output))
        descriptor, log = _apply_grounding_check(descriptor, input_text, synonyms)
        if log["dropped_extracted"]["materials"] or log["dropped_extracted"]["stones"] or (
            log["dropped_extracted"]["colors"] or log["flagged_ungrounded_not_dropped"]
        ):
            grounding_log[p.sku] = log

        for field in ("materials", "stones", "colors"):
            if not getattr(p, field):
                extracted_values = getattr(descriptor.extracted, field)
                if extracted_values:
                    setattr(p, field, extracted_values)
                    p.attr_provenance[field] = "llm"

        p.descriptor_sentence = _build_descriptor_sentence(descriptor, p.title, TAXONOMY)
        p.descriptor_attrs = descriptor.model_dump()
        updated.append(p)

    out_path = DATA_DIR / "catalog.jsonl"
    with out_path.open("w") as f:
        for p in sorted(updated, key=lambda p: p.sku):
            f.write(p.model_dump_json() + "\n")
    print(f"wrote {len(updated)} products (with descriptors) to {out_path}")

    GROUNDING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    GROUNDING_LOG_PATH.write_text(json.dumps(grounding_log, indent=2, ensure_ascii=False))
    print(f"wrote {GROUNDING_LOG_PATH} ({len(grounding_log)} products had grounding issues)")
    print(f"made {api_calls_made} LLM calls, {len(updated) - api_calls_made} served from cache")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _load_catalog() -> list[Product]:
    with (DATA_DIR / "catalog.jsonl").open() as f:
        return [Product.model_validate_json(line) for line in f]


def write_before_after_table(seed: int = 0, n: int = 10) -> None:
    products = [p for p in _load_catalog() if p.descriptor_sentence]
    random.seed(seed)
    sample = random.sample(products, min(n, len(products)))
    rows = [
        {
            "sku": p.sku,
            "title": p.title,
            "description_raw": p.description_raw,
            "descriptor_sentence": p.descriptor_sentence,
            "descriptor_attrs": p.descriptor_attrs,
        }
        for p in sample
    ]
    BEFORE_AFTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    BEFORE_AFTER_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"wrote {BEFORE_AFTER_PATH} ({len(rows)} products)")


def preview_boilerplate() -> None:
    products = _load_catalog()
    _, report = strip_boilerplate(products)
    REMOVED_BOILERPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REMOVED_BOILERPLATE_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"wrote {REMOVED_BOILERPLATE_PATH} ({len(report['removed_sentences'])} sentences)")


def main() -> None:
    products = _load_catalog()
    cleaned, report = strip_boilerplate(products)
    REMOVED_BOILERPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REMOVED_BOILERPLATE_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"wrote {REMOVED_BOILERPLATE_PATH} ({len(report['removed_sentences'])} sentences)")

    run_llm_descriptors(products, cleaned)
    write_before_after_table()


if __name__ == "__main__":
    main()
