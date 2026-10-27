"""Sushita asked twice: can the system say 'I cannot tell'?
This test verifies it can."""
from datetime import date
from app.gate.rules import ConsequenceGate
from app.models.schema import Decision, Event, TavilyResult, Verdict


def _event():
    return Event(event_id="ev_x", clause_id="§1", trigger_date=date(2028, 3, 14),
                 dollar_amount=200.0, dollar_basis="explicit_amount",
                 probability=0.87, probability_basis="fixed date",
                 rate_pct=10.0, description="rent increase")


def test_no_evidence_verdict_yields_no_evidence_decision():
    t = TavilyResult(event_id="ev_x", verdict=Verdict.NO_EVIDENCE,
                     query="test", source_url=None, source_tier="unknown",
                     snippet=None, jurisdiction_match=False, legal_rate_pct=None)
    r = ConsequenceGate().evaluate(_event(), t)
    assert r.decision == Decision.NO_EVIDENCE
    assert "R2" in r.rules_fired
    assert "cannot determine" in r.reason.lower()


def test_no_evidence_is_not_remove():
    """NO_EVIDENCE must NOT be confused with REMOVE. Different honesty."""
    t = TavilyResult(event_id="ev_x", verdict=Verdict.NO_EVIDENCE,
                     query="test", jurisdiction_match=False)
    r = ConsequenceGate().evaluate(_event(), t)
    assert r.decision != Decision.REMOVE


def test_no_evidence_is_not_accept():
    """NO_EVIDENCE must NOT be confused with ACCEPT."""
    t = TavilyResult(event_id="ev_x", verdict=Verdict.NO_EVIDENCE,
                     query="test", jurisdiction_match=False)
    r = ConsequenceGate().evaluate(_event(), t)
    assert r.decision != Decision.ACCEPT


def test_rate_clause_without_legal_cap_yields_no_evidence():
    """Commercial source + no known legal rate for the jurisdiction = 'I cannot tell'."""
    from app.pipeline.verify_tavily import verify_event
    from datetime import date

    ev = Event(event_id="ev_wy", clause_id="§1", trigger_date=date(2028, 1, 1),
               dollar_amount=100.0, dollar_basis="explicit_amount",
               probability=0.9, probability_basis="fixed", rate_pct=18.0,
               description="rent increase Wyoming")
    result = verify_event(ev, "Wyoming")
    assert result.legal_rate_pct is None, "Wyoming should have no known rate"
    assert result.verdict in (Verdict.NO_EVIDENCE, Verdict.INSUFFICIENT), \
        f"expected NO_EVIDENCE, got {result.verdict}"
