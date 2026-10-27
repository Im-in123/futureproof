"""Extract a numeric rate from a Tavily snippet using Lightning (reasoning off)."""
from __future__ import annotations
import json
import os
from openai import OpenAI
from app.models.schema import RateExtraction

_RATE_SCHEMA = {
    "type": "object",
    "properties": {
        "rate": {"type": ["number", "null"]},
        "rate_kind": {"type": "string", "enum": ["percentage", "absolute", "unknown"]},
        "effective_date": {"type": ["string", "null"]},
        "scope": {"type": "string", "enum": ["state", "city", "unknown"]},
        "jurisdiction": {"type": ["string", "null"]},
        "source_url": {"type": ["string", "null"]},
    },
    "required": ["rate", "rate_kind", "effective_date", "scope", "jurisdiction", "source_url"],
}

_PROMPT = "Extract the numeric rent-increase rate. Return JSON only. If no rate is stated, rate=null and rate_kind='unknown'. Do not guess."


def extract_rate(snippet: str, source_url: str | None = None) -> RateExtraction:
    client = OpenAI(
        base_url=os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        api_key=os.environ.get("NVIDIA_API_KEY"),
    )
    resp = client.chat.completions.create(
        model=os.environ.get("NEMOTRON_LIGHTNING_MODEL",
                            "nvidia/nemotron-3.5-lightning-30b-a3b"),
        messages=[{"role": "system", "content": _PROMPT},
                  {"role": "user", "content": snippet}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": "rate", "schema": _RATE_SCHEMA}},
        temperature=0.0, max_tokens=256,
        extra_body={"reasoning_effort": "none"},
    )
    data = json.loads(resp.choices[0].message.content)
    if source_url:
        data["source_url"] = source_url
    return RateExtraction(**data)
