"""Full pipeline: extract -> reason -> verify -> gate -> receipt."""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from app.pipeline.extract import extract_clauses
from app.pipeline.reason import reason_consequences
from app.pipeline.verify_tavily import verify_event
from app.gate.rules import ConsequenceGate
from app.receipt.emit import emit_receipt
from app.pipeline.cost import CostTracker
import time
from app.models.schema import Decision


def simulate(document_text: str, jurisdiction: str, base_rent: float | None = None) -> dict:
    tracker = CostTracker()
    t0 = time.time()
    print(f"[1/4] Extracting clauses (Lightning, reasoning=off)...")
    clauses = extract_clauses(document_text, tracker=tracker)
    print(f"      {len(clauses)} clauses extracted")

    print(f"[2/4] Reasoning consequences (Super, reasoning=high)...")
    events = reason_consequences(clauses, jurisdiction, date.today(), base_rent,
                                document_text=document_text, tracker=tracker)
    print(f"      {len(events)} events proposed")

    gate = ConsequenceGate(strictness=os.environ.get("GATE_STRICTNESS", "strict"))
    receipt_events = []
    removed = 0
    downgraded = 0
    accepted = 0
    no_evidence = 0

    # ─── Normalize: extract base_rent if missing, then annual impact ───
    import re as _re

    print(f"      [norm] base_rent received: {base_rent}", file=sys.stderr)

    # If base_rent is None or 0, try to extract from the document text
    effective_base = base_rent
    if not effective_base or effective_base <= 0:
        patterns = [
            r'\$([0-9,]+(?:\.\d+)?)\s*(?:per month|/month|monthly|per month\b)',
            r'monthly rent\s*(?:of|is|shall be)\s*\$([0-9,]+(?:\.\d+)?)',
            r'rent\s*(?:of|is|shall be)\s*\$([0-9,]+(?:\.\d+)?)',
            r'\$([0-9,]+(?:\.\d+)?)\s*(?:per month|/mo\b|monthly)',
        ]
        for pat in patterns:
            m = _re.search(pat, document_text, _re.IGNORECASE)
            if m:
                try:
                    effective_base = float(m.group(1).replace(',', ''))
                    if effective_base > 0:
                        print(f"      [norm] extracted base_rent=${effective_base:,.0f} from document text",
                              file=sys.stderr)
                        break
                except ValueError:
                    pass

    # If still None, try formula strings
    if not effective_base or effective_base <= 0:
        for ev in events:
            if ev.dollar_formula:
                m = _re.search(r'\$([0-9,]+(?:\.\d+)?)\s*[×x*]\s*1\.', ev.dollar_formula)
                if m:
                    try:
                        effective_base = float(m.group(1).replace(',', ''))
                        if effective_base > 0:
                            print(f"      [norm] extracted base_rent=${effective_base:,.0f} from formula",
                                  file=sys.stderr)
                            break
                    except ValueError:
                        pass

    # Apply annual normalization to every rate-based event
    if effective_base and effective_base > 0:
        for ev in events:
            if ev.rate_pct is None:
                continue
            monthly = effective_base * (ev.rate_pct / 100.0)
            annual = round(monthly * 12, 2)
            old_amt = ev.dollar_amount
            ev.dollar_amount = annual
            ev.dollar_basis = "explicit_amount"
            if "/year" not in ev.description:
                ev.description = ev.description.rstrip(".") + f" (${annual:,.0f}/year = ${monthly:,.0f}/month)"
            print(f"      [norm] {ev.event_id}: rate={ev.rate_pct}% × ${effective_base:,.0f} × 12 = ${annual:,.0f}/yr (was ${old_amt or 0:,.0f})",
                  file=sys.stderr)
    else:
        print(f"      [norm] ⚠️  Could not determine base_rent — dollar amounts will be null",
              file=sys.stderr)

    # Also normalize events that came back with dollar_amount=0 but have a stated amount in the clause
    for ev in events:
        if (ev.dollar_amount is None or ev.dollar_amount == 0) and ev.rate_pct is None:
            # Try to extract explicit amount from description
            m = _re.search(r'\$([0-9,]+(?:\.\d+)?)', ev.description)
            if m:
                try:
                    amt = float(m.group(1).replace(',', ''))
                    if amt > 0:
                        ev.dollar_amount = amt
                        ev.dollar_basis = "explicit_amount"
                        print(f"      [norm] {ev.event_id}: extracted ${amt:,.0f} from description",
                              file=sys.stderr)
                except ValueError:
                    pass

    print(f"[3/4] Tavily verification + gate...")
    for event in events:
        tavily = verify_event(event, jurisdiction)
        tracker.record_tavily(1)
        gate_result = gate.evaluate(event, tavily)

        rate_s = f"{event.rate_pct:.1f}%" if event.rate_pct is not None else "None"
        legal_s = f"{tavily.legal_rate_pct:.1f}%" if tavily.legal_rate_pct is not None else "None"
        print(f"      {event.event_id}  §{event.clause_id:<8} "
              f"{event.trigger_date}  ${event.dollar_amount or 0:>8.2f}  "
              f"rate={rate_s:<7} legal={legal_s:<7} "
              f"{tavily.verdict.value:<13} {tavily.source_tier:<10} "
              f"-> {gate_result.decision.value:<10} {gate_result.reason}")

        if gate_result.decision == Decision.REMOVE:
            removed += 1
        elif gate_result.decision == Decision.DOWNGRADE:
            downgraded += 1
        elif gate_result.decision == Decision.NO_EVIDENCE:
            no_evidence += 1
        else:
            accepted += 1

        # ALL decisions go into the receipt — it is a complete audit trail,
        # not just a list of approvals. This is the difference between a
        # receipt and a screenshot.
        receipt_events.append({
            "event": event.model_dump(mode="json"),
            "tavily": tavily.model_dump(mode="json"),
            "gate": gate_result.model_dump(mode="json"),
        })

    print(f"[4/4] Emitting receipt...")
    tracker.latency_seconds = time.time() - t0
    receipt = emit_receipt(
        document_text=document_text,
        events=receipt_events,
        model_metadata={
            "jurisdiction": jurisdiction,
            "base_rent": base_rent,
            "extractor": os.environ.get("NEMOTRON_LIGHTNING_MODEL"),
            "reasoner": os.environ.get("NEMOTRON_SUPER_MODEL"),
            "gate_strictness": os.environ.get("GATE_STRICTNESS", "strict"),
            "cost": tracker.summary(),
        },
    )

    print()
    print(f"  Accepted:    {accepted}")
    print(f"  Downgraded:  {downgraded}")
    print(f"  Removed:     {removed}")
    print(f"  No evidence: {no_evidence}")
    print(f"  Receipt:    {receipt['_path']}")
    print()
    return receipt


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app.pipeline.orchestrate <doc.txt> [--jurisdiction X] [--base-rent N]")
        sys.exit(2)
    doc_path = Path(sys.argv[1])
    jurisdiction = "California"
    base_rent = None
    for i, arg in enumerate(sys.argv):
        if arg == "--jurisdiction" and i + 1 < len(sys.argv):
            jurisdiction = sys.argv[i + 1]
        if arg == "--base-rent" and i + 1 < len(sys.argv):
            base_rent = float(sys.argv[i + 1])
    text = doc_path.read_text(encoding="utf-8")
    receipt = simulate(text, jurisdiction, base_rent)
    print(f"Verify with: python scripts/verify_receipt.py {receipt['_path']}")


if __name__ == "__main__":
    main()
