"""Gate tests seeded with REAL Tavily output from the live query."""
from datetime import date
from app.gate.rules import ConsequenceGate
from app.models.schema import Decision, Event, TavilyResult, Verdict

TODAY = date(2026, 10, 19)
gate = ConsequenceGate()


def make_event(**kw):
    base = dict(event_id="ev_001", clause_id="§4.2(b)",
                trigger_date=date(2028, 3, 14),
                dollar_amount=340.0, dollar_formula=None,
                dollar_basis="explicit_amount", probability=0.87,
                probability_basis="contractual obligation with fixed date",
                description="rent increase of 10% on first anniversary")
    base.update(kw)
    return Event(**base)


def make_tavily(**kw):
    base = dict(event_id="ev_001", verdict=Verdict.VERIFIED,
                query="California rent stabilization annual rent increase limit 2026",
                source_url="https://santa-ana.gov/rent-stabilization-newsletter",
                source_tier="official",
                snippet="Maximum Allowable Rent Increase 2.87% effective September 1, 2026",
                published_date="2026-08-31", jurisdiction_match=True)
    base.update(kw)
    return TavilyResult(**base)


def test_accept_when_all_event_rules_pass():
    r = gate.evaluate(make_event(), make_tavily())
    assert r.decision == Decision.ACCEPT
    assert set(r.rules_fired) == {"R1", "R2", "R3", "R4", "R5"}

def test_remove_when_tavily_contradicts():
    r = gate.evaluate(make_event(), make_tavily(verdict=Verdict.CONTRADICTED))
    assert r.decision == Decision.REMOVE and "R2" in r.rules_fired

def test_downgrade_when_tavily_insufficient():
    r = gate.evaluate(make_event(), make_tavily(verdict=Verdict.INSUFFICIENT))
    assert r.decision == Decision.DOWNGRADE and "R2" in r.rules_fired

def test_remove_when_no_clause_citation():
    r = gate.evaluate(make_event(clause_id=""), make_tavily())
    assert r.decision == Decision.REMOVE and "R1" in r.rules_fired

def test_remove_zero_amount_unknown_basis():
    r = gate.evaluate(make_event(dollar_amount=0, dollar_basis="unknown",
                                 dollar_formula=None), make_tavily())
    assert r.decision == Decision.REMOVE and "R4" in r.rules_fired

def test_accept_formula_when_base_unknown():
    r = gate.evaluate(make_event(dollar_amount=None,
                                 dollar_formula="prev_rent * 1.10",
                                 dollar_basis="percentage_of_base"),
                      make_tavily())
    assert r.decision == Decision.ACCEPT

def test_accept_official_gov_source():
    t = make_tavily(source_url="https://santa-ana.gov/rent-stabilization-newsletter",
                    source_tier="official", published_date="2026-08-31",
                    jurisdiction_match=True)
    r = gate.evaluate_source(t, "California", "state", today=TODAY)
    assert r.decision == Decision.ACCEPT

def test_remove_stale_ballotpedia():
    t = make_tavily(source_url="https://ballotpedia.org/St._Helena_Measure_F",
                    source_tier="blog", published_date="2019-06-01",
                    jurisdiction_match=True)
    r = gate.evaluate_source(t, "California", "state", today=TODAY)
    assert r.decision == Decision.REMOVE and "T2" in r.rules_fired

def test_remove_wrong_jurisdiction_montgomery():
    t = make_tavily(source_url="https://www.sourceofthespring.com/montgomery",
                    source_tier="blog", published_date="2025-04-01",
                    jurisdiction_match=False)
    r = gate.evaluate_source(t, "California", "state", today=TODAY)
    assert r.decision == Decision.REMOVE and "T1" in r.rules_fired

def test_downgrade_city_scope_for_state_query():
    t = make_tavily(source_url="https://gocodebook.com/oxnard",
                    source_tier="commercial", published_date="2026-09-28",
                    snippet="Oxnard Rent Stabilization 4% limit",
                    jurisdiction_match=True)
    r = gate.evaluate_source(t, "California", "state", today=TODAY)
    assert r.decision == Decision.DOWNGRADE and "T4" in r.rules_fired
