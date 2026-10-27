"""The deterministic consequence gate."""
from __future__ import annotations
from datetime import date, datetime
from app.models.schema import Decision, Event, GateResult, TavilyResult, Verdict

RECENCY_WINDOW_DAYS = 18 * 30


def _tier_name(tier) -> str:
    return tier.value if hasattr(tier, "value") else str(tier)


class ConsequenceGate:
    def __init__(self, strictness: str = "strict") -> None:
        self.strictness = strictness

    def evaluate(self, event: Event, tavily: TavilyResult) -> GateResult:
        """
        Rule order (REMOVE rules run before DOWNGRADE rules):
          R1  clause citation required       -> REMOVE
          R2a tavily contradicted            -> REMOVE
          R4  dollar amount or formula       -> REMOVE
          R5  zero amount + unknown basis    -> REMOVE
          R6  rate exceeds legal max         -> REMOVE   (runs BEFORE insufficient)
          R3  probability basis              -> DOWNGRADE
          R2b tavily insufficient            -> DOWNGRADE
        """
        rules: list[str] = []

        # R1: REMOVE rules first
        if not event.clause_id or not event.clause_id.strip():
            return self._rem_event(event, rules + ["R1"], "no clause citation")
        rules.append("R1")

        # R2a: contradicted = REMOVE
        if tavily.verdict == Verdict.CONTRADICTED:
            return self._rem_event(event, rules + ["R2"], "tavily contradicted")

        # R2c: no evidence = honest "we cannot determine"
        if tavily.verdict == Verdict.NO_EVIDENCE:
            return self._no_ev_event(event, rules + ["R2"],
                "no reliable legal source found — cannot determine legality")

        # R2c: no evidence = honest "we cannot determine"
        if tavily.verdict == Verdict.NO_EVIDENCE:
            return self._no_ev_event(event, rules + ["R2"],
                "no reliable legal source found — cannot determine legality")

        # R4
        has_amount = event.dollar_amount is not None and event.dollar_amount > 0
        has_formula = bool(event.dollar_formula and event.dollar_formula.strip())
        if not (has_amount or has_formula):
            return self._rem_event(event, rules + ["R4"], "no dollar amount and no formula")
        rules.append("R4")

        # R5
        if (event.dollar_amount or 0) == 0 and event.dollar_basis == "unknown":
            return self._rem_event(event, rules + ["R5"], "zero amount with unknown basis")
        rules.append("R5")

        # R6: rate compliance (BEFORE insufficient downgrade)
        if event.rate_pct is not None and tavily.legal_rate_pct is not None:
            if event.rate_pct > tavily.legal_rate_pct * 1.01:  # 1% only for float rounding; law is exact
                return self._rem_event(
                    event, rules + ["R6"],
                    f"clause rate {event.rate_pct:.2f}% exceeds verified legal max "
                    f"{tavily.legal_rate_pct:.2f}%"
                )
            rules.append("R6")

        # R3: DOWNGRADE rules now
        if not event.probability_basis or not event.probability_basis.strip():
            return self._dwn_event(event, rules + ["R3"], "no probability basis")
        rules.append("R3")

        # R2b: insufficient = DOWNGRADE (only after R6 had its chance)
        if tavily.verdict == Verdict.INSUFFICIENT:
            return self._dwn_event(event, rules + ["R2"], "tavily insufficient")
        rules.append("R2")

        return GateResult(event_id=event.event_id, decision=Decision.ACCEPT,
                          rules_fired=rules, reason="all event rules passed")

    def evaluate_source(self, tavily: TavilyResult, target_jurisdiction: str,
                        query_scope: str, today: date | None = None) -> GateResult:
        rules: list[str] = []
        today = today or date.today()
        if not tavily.jurisdiction_match:
            return self._rem_src(tavily, rules + ["T1"], "jurisdiction mismatch")
        rules.append("T1")
        if tavily.published_date:
            try:
                pub = datetime.fromisoformat(tavily.published_date[:10]).date()
                if (today - pub).days > RECENCY_WINDOW_DAYS:
                    return self._rem_src(tavily, rules + ["T2"],
                                         f"source older than 18 months ({pub})")
            except ValueError:
                return self._dwn_src(tavily, rules + ["T2"], "unparseable publish date")
        else:
            return self._dwn_src(tavily, rules + ["T2"], "no publish date")
        rules.append("T2")
        if _tier_name(tavily.source_tier) in ("blog", "unknown"):
            return self._dwn_src(tavily, rules + ["T3"],
                                 f"low-quality tier={_tier_name(tavily.source_tier)}")
        rules.append("T3")
        snippet = (tavily.snippet or "").lower()
        if query_scope == "state" and any(
            c in snippet for c in
            ["oxnard", "santa ana", "los angeles", "san francisco", "san jose"]
        ):
            return self._dwn_src(tavily, rules + ["T4"], "city-scoped for state query")
        rules.append("T4")
        return GateResult(event_id=tavily.event_id, decision=Decision.ACCEPT,
                          rules_fired=rules, reason="all source rules passed")

    def _rem_event(self, e, r, m): return GateResult(event_id=e.event_id, decision=Decision.REMOVE, rules_fired=r, reason=m)
    def _no_ev_event(self, e, r, m): return GateResult(event_id=e.event_id, decision=Decision.NO_EVIDENCE, rules_fired=r, reason=m)
    def _no_ev_event(self, e, r, m): return GateResult(event_id=e.event_id, decision=Decision.NO_EVIDENCE, rules_fired=r, reason=m)
    def _dwn_event(self, e, r, m): return GateResult(event_id=e.event_id, decision=Decision.DOWNGRADE, rules_fired=r, reason=m)
    def _rem_src(self, t, r, m): return GateResult(event_id=t.event_id, decision=Decision.REMOVE, rules_fired=r, reason=m)
    def _dwn_src(self, t, r, m): return GateResult(event_id=t.event_id, decision=Decision.DOWNGRADE, rules_fired=r, reason=m)
