"""Consequence reasoning. Super with Lightning fallback. Cached and timed."""
from __future__ import annotations
import json, os, re, sys, time
from datetime import date
from openai import OpenAI
from app.models.schema import Clause, Event
from app.pipeline.cost import CostTracker

_EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "clause_id": {"type": "string"},
                    "trigger_date": {"type": "string"},
                    "dollar_amount": {"type": ["number", "null"]},
                    "dollar_formula": {"type": ["string", "null"]},
                    "dollar_basis": {"type": "string",
                        "enum": ["explicit_amount", "percentage_of_base", "formula", "unknown"]},
                    "rate_pct": {"type": ["number", "null"]},
                    "is_one_time": {"type": "boolean"},
                    "probability": {"type": "number"},
                    "probability_basis": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["event_id", "clause_id", "trigger_date", "dollar_amount",
                             "dollar_formula", "dollar_basis", "rate_pct", "is_one_time",
                             "probability", "probability_basis", "description"],
            },
        }
    },
    "required": ["events"],
}

_PROMPT = """You are a contract consequence simulator.
Produce up to 5 future events where a clause will cost the signer money.

CRITICAL RULES:
1. trigger_date MUST be AFTER today. "First anniversary of commencement 2027-03-14"
   means 2028-03-14, NOT 2027-03-14.
2. If base_rent is given, compute dollar_amount as a number.
3. If base_rent is null, dollar_amount=null + dollar_formula + dollar_basis=percentage_of_base.
4. NEVER dollar_amount=0 with dollar_basis=unknown.
5. Every event cites a clause_id from input.
6. rate_pct = the percentage number from the clause (18 for "18 percent").
   If no percentage in the clause, rate_pct=null.
7. probability_basis explains WHY.
8. Sort by expected impact descending.
Return JSON only."""


_CACHE_DIR = Path = __import__("pathlib").Path(__file__).resolve().parent.parent.parent / "fixtures" / "reasoning_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_file(model_id: str, context: dict):
    import hashlib
    payload = hashlib.sha256(
        (model_id + json.dumps(context, sort_keys=True)).encode()
    ).hexdigest()[:16]
    return _CACHE_DIR / (payload + ".json")


def _rate_from_text(text: str) -> float | None:
    if not text:
        return None
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:percent|%)", text, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _parse_events(data, clauses, document_text="", base_rent_hint=None):
    clauses_by_id = {c.clause_id: c for c in clauses}
    events = []
    for idx, e in enumerate(data.get("events", []), start=1):
        if (e.get("dollar_amount") or 0) == 0 and not e.get("dollar_formula"):
            continue
        e["event_id"] = "ev_" + format(idx, "03d")

        # Rate fallback only for rent/deposit clauses
        if e.get("rate_pct") is None:
            matched = clauses_by_id.get(e.get("clause_id", ""))
            clause_type = matched.clause_type if matched else "other"
            if clause_type in ("rent_adjustment", "deposit"):
                candidates = [matched.text if matched else "", e.get("description", "")]
                for cand in candidates:
                    r = _rate_from_text(cand)
                    if r is not None:
                        e["rate_pct"] = r
                        print(f"      [rate] {e['event_id']} rate_pct={r:.2f} (clause={clause_type})", file=sys.stderr)
                        break
                else:
                    print(f"      [rate] {e['event_id']} rate_pct=None (rent clause, no rate found)", file=sys.stderr)
            else:
                print(f"      [rate] {e['event_id']} SKIP rate (clause={clause_type}, not rent)", file=sys.stderr)

        # Ensure is_one_time is a bool (schema requires it)
        if "is_one_time" not in e or e["is_one_time"] is None:
            e["is_one_time"] = False

        # Normalize: recurring rent adjustments must compute ANNUAL impact
        clause = clauses_by_id.get(e.get("clause_id", ""))
        clause_type = clause.clause_type if clause else "other"
        rate = e.get("rate_pct")
        if clause_type == "rent_adjustment" and rate and base_rent_hint:
            annual = round(base_rent_hint * (rate / 100.0) * 12, 2)
            old_amt = e.get("dollar_amount")
            e["dollar_amount"] = annual
            e["dollar_basis"] = "explicit_amount"
            e["description"] = (e.get("description", "") +
                                f" (${annual:,.0f}/year = ${base_rent_hint * rate / 100.0:,.0f}/month)")
            if old_amt is not None and abs(old_amt - annual) > 1:
                print(f"      [normalize] {e['event_id']} rent: {old_amt} → {annual} (annual)",
                      file=sys.stderr)

        try:
            events.append(Event(**e))
        except Exception as exc:
            print(f"      [skip] malformed event: {exc}", file=sys.stderr)
    return events


def _call_model(client, model_id, context, reasoning_effort, max_tokens, tracker=None):
    """Call model with cache, retry, and latency tracking. Returns parsed dict."""
    cache_file = _cache_file(model_id, context)
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text())
            print(f"      [cache] hit for {model_id.split('/')[-1]}", file=sys.stderr)
            if tracker:
                tracker.record_model(model_id,
                                     cached.get("in_tokens", 0),
                                     cached.get("out_tokens", 0),
                                     cached.get("latency_s", 0.0))
            return cached["data"]
        except Exception:
            pass

    resp = None
    t_start = time.time()
    last_exc = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "system", "content": _PROMPT},
                          {"role": "user", "content": json.dumps(context)}],
                response_format={"type": "json_schema",
                                 "json_schema": {"name": "events", "schema": _EVENT_SCHEMA}},
                temperature=0.2,
                max_tokens=max_tokens,
                extra_body={"reasoning_effort": reasoning_effort},
            )
            break
        except Exception as exc:
            last_exc = exc
            print(f"      [retry {attempt+1}/3] {model_id.split('/')[-1]}: {type(exc).__name__}", file=sys.stderr)
            if attempt < 2:
                time.sleep(3 * (attempt + 1))

    if resp is None:
        raise last_exc if last_exc else RuntimeError("all attempts failed")

    elapsed = round(time.time() - t_start, 2)
    content = resp.choices[0].message.content
    if not content or not content.strip():
        raise ValueError(f"null content (finish={resp.choices[0].finish_reason})")

    # Track
    if tracker:
        in_t = resp.usage.prompt_tokens if resp.usage else 0
        out_t = resp.usage.completion_tokens if resp.usage else 0
        print(f"      [tracker] reason: {model_id.split('/')[-1]} in={in_t} out={out_t} lat={elapsed}s", file=sys.stderr)
        tracker.record_model(model_id, in_t, out_t, elapsed)

    data = json.loads(content)

    # Cache write
    try:
        cache_file.write_text(json.dumps({
            "data": data,
            "in_tokens": resp.usage.prompt_tokens if resp.usage else 0,
            "out_tokens": resp.usage.completion_tokens if resp.usage else 0,
            "latency_s": elapsed,
        }))
    except Exception:
        pass

    return data


def reason_consequences(clauses, jurisdiction, today, base_rent=None,
                        document_text="", tracker: CostTracker | None = None):
    client = OpenAI(
        base_url=os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        api_key=os.environ["NVIDIA_API_KEY"],
    )
    context = {
        "clauses": [c.model_dump() for c in clauses],
        "jurisdiction": jurisdiction,
        "today": today.isoformat(),
        "base_rent": base_rent,
    }
    super_model = os.environ.get("NEMOTRON_SUPER_MODEL",
                                 "nvidia/nemotron-3.5-super-vl-120b-a12b")
    lightning_model = os.environ.get("NEMOTRON_LIGHTNING_MODEL",
                                     "nvidia/nemotron-3.5-lightning-30b-a3b")

    for model, effort, tokens, label in [
        (super_model, "medium", 16384, "Super"),
        (lightning_model, "none", 4096, "Lightning"),
    ]:
        try:
            data = _call_model(client, model, context, effort, tokens, tracker)
            events = _parse_events(data, clauses, document_text, base_rent_hint=base_rent)
            if events:
                print(f"      [ok] {label} produced {len(events)} events", file=sys.stderr)
                return events
            print(f"      [warn] {label} produced no valid events", file=sys.stderr)
        except Exception as exc:
            print(f"      [warn] {label} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
    return []
