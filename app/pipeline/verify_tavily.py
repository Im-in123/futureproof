"""Tavily verification. Emits NO_EVIDENCE when it cannot determine."""
from __future__ import annotations
import hashlib, json, os, re, sys, time
from pathlib import Path
import httpx
from app.models.schema import Event, TavilyResult, Verdict

CACHE_DIR = Path("fixtures/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

KNOWN_MAX_RATES = {
    "california": 10.0, "new york": 5.0, "oregon": 10.0,
    "washington": 10.0, "massachusetts": 10.0, "colorado": 10.0,
    "illinois": 10.0, "new jersey": 10.0, "maryland": 10.0, "minnesota": 10.0,
}
_STATE_ABBR = {"california": ["ca", "calif"]}
INTER_CALL_SLEEP = 6.0


def _cache_key(q: str) -> str:
    return hashlib.sha256(q.encode()).hexdigest()[:16]


def _classify_tier(url: str) -> str:
    u = url.lower()
    if any(x in u for x in [".gov", ".us/", "cityof", "county.gov"]):
        return "official"
    if any(x in u for x in ["lawagreements", "findlaw", "nolo", "cornell",
                            "justia", "leginfo", "law.cornell"]):
        return "legal_db"
    if any(x in u for x in ["zillow", "redfin", "apartments", "rentcafe",
                            "realtor", "calculator", "gocodebook",
                            "rentwithskyline", "thegroupcre", "coastline",
                            "ab-1482", "rent-increase"]):
        return "commercial"
    if any(x in u for x in ["ballotpedia", "news", "blog", "medium",
                            "sourceofthespring", "patch.com"]):
        return "blog"
    return "commercial"


def _extract_date(text: str) -> str | None:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return m.group(0)
    return None


def _jurisdiction_match(url: str, snippet: str, jurisdiction: str) -> bool:
    text = (url + " " + snippet).lower()
    j = jurisdiction.lower()
    if j in text:
        return True
    for abbr in _STATE_ABBR.get(j, []):
        if re.search(rf"\b{abbr}\b", text):
            return True
    return False


def _call_tavily(query: str) -> list:
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    headers = {"Content-Type": "application/json"}
    payload = {"query": query, "search_depth": "advanced", "max_results": 5}
    if api_key and api_key.startswith("tvly-"):
        payload["api_key"] = api_key
    else:
        headers["X-Tavily-Access-Mode"] = "keyless"

    for attempt in range(2):
        try:
            r = httpx.post("https://api.tavily.com/search",
                           headers=headers, json=payload, timeout=30.0)
            if r.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"      [tavily] 429; sleeping {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json().get("results", [])
        except Exception as exc:
            print(f"      [tavily] {type(exc).__name__}: {exc}", file=sys.stderr)
            time.sleep(3)
    return []


def verify_event(event: Event, jurisdiction: str) -> TavilyResult:
    query = f"{jurisdiction} {event.description} {event.trigger_date.year}"
    cache_file = CACHE_DIR / f"{_cache_key(query)}.json"

    if cache_file.exists():
        results = json.loads(cache_file.read_text())["results"]
    else:
        results = _call_tavily(query)
        if results:
            cache_file.write_text(json.dumps({"results": results}))
        time.sleep(INTER_CALL_SLEEP)

    fallback_legal = KNOWN_MAX_RATES.get(jurisdiction.lower())

    # No results at all → NO_EVIDENCE (honest "I don't know")
    if not results:
        return TavilyResult(
            event_id=event.event_id,
            verdict=Verdict.NO_EVIDENCE,
            query=query,
            legal_rate_pct=fallback_legal,
        )

    best, best_score = None, -1
    for res in results:
        url = res.get("url", "")
        snippet = res.get("content", "")[:800]
        tier = _classify_tier(url)
        jm = _jurisdiction_match(url, snippet, jurisdiction)
        date = _extract_date(snippet)
        tier_score = {"official": 4, "legal_db": 3, "commercial": 2,
                      "blog": 1, "unknown": 0}[tier]
        score = tier_score + (3 if jm else 0) + (2 if date else 0)
        if score > best_score:
            best_score = score
            best = {"url": url, "snippet": snippet, "tier": tier,
                    "jurisdiction_match": jm, "published_date": date}

    if best is None:
        return TavilyResult(
            event_id=event.event_id,
            verdict=Verdict.NO_EVIDENCE,
            query=query,
            legal_rate_pct=fallback_legal,
        )

    legal_rate_pct = fallback_legal

    # Verdict policy — ordered so that "I cannot tell" wins when it applies:
    #   1. Rate-based clause + no known legal cap       → NO_EVIDENCE (we cannot judge)
    #   2. Wrong jurisdiction                           → CONTRADICTED
    #   3. Official / legal_db source, matches          → VERIFIED
    #   4. Commercial source, matches                   → VERIFIED
    #   5. Blog / unknown tier, matches                 → NO_EVIDENCE
    #   6. Anything else                                → INSUFFICIENT
    if event.rate_pct is not None and legal_rate_pct is None:
        verdict = Verdict.NO_EVIDENCE
    elif not best["jurisdiction_match"]:
        verdict = Verdict.CONTRADICTED
    elif best["tier"] in ("official", "legal_db"):
        verdict = Verdict.VERIFIED
    elif best["tier"] == "commercial":
        verdict = Verdict.VERIFIED
    elif best["tier"] in ("blog", "unknown"):
        verdict = Verdict.NO_EVIDENCE
    else:
        verdict = Verdict.INSUFFICIENT

    return TavilyResult(
        event_id=event.event_id,
        verdict=verdict,
        query=query,
        source_url=best["url"],
        source_tier=best["tier"],
        snippet=best["snippet"][:300],
        published_date=best["published_date"],
        jurisdiction_match=best["jurisdiction_match"],
        legal_rate_pct=legal_rate_pct,
    )
