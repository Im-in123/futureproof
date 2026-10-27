"""Clause extraction. Catches ALL monetary clauses, not just time-bound ones."""
from __future__ import annotations
import json, os
from openai import OpenAI
from app.models.schema import Clause
from app.pipeline.cost import CostTracker

import hashlib as _hashlib
from pathlib import Path as _Path

_extract_cache = _Path(__file__).resolve().parent.parent.parent / "fixtures" / "extraction_cache"
_extract_cache.mkdir(parents=True, exist_ok=True)


def _extract_cache_file(model: str, text: str) -> _Path:
    key = _hashlib.sha256((model + text).encode()).hexdigest()[:16]
    return _extract_cache / (key + ".json")

_CLAUSE_SCHEMA = {
    "type": "object",
    "properties": {
        "clauses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "clause_id": {"type": "string"},
                    "text": {"type": "string"},
                    "clause_type": {
                        "type": "string",
                        "enum": ["rent_adjustment", "renewal", "maintenance",
                                 "penalty", "deposit", "termination",
                                 "fee", "arbitration", "other"],
                    },
                    "temporal_trigger": {"type": ["string", "null"]},
                    "is_one_time": {"type": "boolean"},
                    "stated_amount": {"type": ["number", "null"]},
                },
                "required": ["clause_id", "text", "clause_type",
                             "temporal_trigger", "is_one_time", "stated_amount"],
            },
        }
    },
    "required": ["clauses"],
}

_PROMPT = """Extract every clause from this contract that has a monetary consequence OR a legal right.

DO NOT SKIP a clause just because it lacks a future trigger date. Include:

- Rent adjustments (with or without a specific date)
- Security deposits and deposit increases
- Maintenance responsibilities with dollar thresholds
- Late fees and penalties
- One-time fees (franchise fee, application fee, move-in fee, pet deposit)
- Auto-renewal clauses
- Early termination penalties
- Arbitration clauses (these matter legally even without a dollar amount)

For each clause, provide:
- clause_id: the section reference from the document (e.g. "2", "4.1", "§12")
- text: the exact clause text (up to 500 characters)
- clause_type: one of the types in the schema
- temporal_trigger: the date-based trigger if one exists (e.g. "first anniversary of commencement"), else null
- is_one_time: true if the cost fires only once, false if it recurs
- stated_amount: the dollar amount if explicitly stated in the clause, else null

Do not invent clauses. Do not skip a clause because it lacks a date. If a clause has neither a monetary consequence nor a legal right, skip it.

Return JSON matching the schema."""


def extract_clauses(document_text: str, tracker: CostTracker | None = None) -> list[Clause]:
    client = OpenAI(
        base_url=os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        api_key=os.environ["NVIDIA_API_KEY"],
    )
    model_name = os.environ.get("NEMOTRON_LIGHTNING_MODEL",
                                "nvidia/nemotron-3.5-lightning-30b-a3b")
    cache_file = _extract_cache_file(model_name, document_text)
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text())
            print(f"      [extract-cache] hit", file=__import__("sys").stderr)
            if tracker:
                # Record cached call with the original token counts
                tracker.record_model(
                    model_name,
                    cached.get("in_tokens", 0),
                    cached.get("out_tokens", 0),
                    cached.get("latency_s", 0.01),
                )
            return [Clause(**c) for c in cached["clauses"]]
        except Exception:
            pass

    import time as _time
    _t_start = _time.time()
    resp = None
    for _attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model_name,
        messages=[{"role": "system", "content": _PROMPT},
                  {"role": "user", "content": document_text}],
                response_format={"type": "json_schema",
                                 "json_schema": {"name": "clauses", "schema": _CLAUSE_SCHEMA}},
                temperature=0.0,
                max_tokens=4096,
                extra_body={"reasoning_effort": "none"},
            )
            break
        except Exception as _e:
            if _attempt == 2:
                raise
            _time.sleep(3 * (_attempt + 1))
    if tracker and resp.usage:
        _elapsed = round(_time.time() - _t_start, 2)
        print(f"      [tracker] extract: {model_name.split('/')[-1]} in={resp.usage.prompt_tokens} out={resp.usage.completion_tokens} lat={_elapsed}s", file=__import__("sys").stderr)
        tracker.record_model(model_name, resp.usage.prompt_tokens, resp.usage.completion_tokens, _elapsed)
    data = json.loads(resp.choices[0].message.content)
    try:
        cache_file.write_text(json.dumps({
            "clauses": data["clauses"],
            "in_tokens": resp.usage.prompt_tokens if resp.usage else 0,
            "out_tokens": resp.usage.completion_tokens if resp.usage else 0,
            "latency_s": _elapsed if "_elapsed" in dir() else 0.01,
        }))
    except Exception:
        pass
    return [Clause(**c) for c in data["clauses"]]
