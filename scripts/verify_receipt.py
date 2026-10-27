#!/usr/bin/env python3
"""
FutureProof standalone receipt verifier.

Runs in a fresh environment. Takes a receipt JSON file.
Recomputes the self-hash and prints VALID / INVALID.

Usage:
    python scripts/verify_receipt.py receipts/fp_....json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def verify(path: Path) -> int:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"✗ File not found: {path}")
        return 1
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        return 1

    stored = receipt.get("self_hash")
    payload = {k: v for k, v in receipt.items()
               if k != "self_hash" and not k.startswith("_")}
    recomputed = f"sha256:{sha256_hex(canonical(payload))}"

    print("=" * 60)
    print("  FutureProof Receipt Verification")
    print("=" * 60)
    print(f"  Receipt ID:        {receipt.get('receipt_id', '?')}")
    print(f"  Created at:        {receipt.get('created_at', '?')}")
    print(f"  Document hash:     {receipt.get('document_hash', '?')}")
    print(f"  Prev receipt hash: {receipt.get('previous_receipt_hash') or '(genesis)'}")
    print(f"  Self hash stored:  {stored}")
    print(f"  Self hash recomputed: {recomputed}")
    print("-" * 60)

    hash_ok = stored == recomputed
    print(f"  Hash integrity:    {'✓ VALID' if hash_ok else '✗ MISMATCH'}")

    events = receipt.get("events", [])
    print(f"  Events in receipt: {len(events)}")
    print("-" * 60)

    event_ok = True
    counts = {"ACCEPT": 0, "DOWNGRADE": 0, "REMOVE": 0}
    for ev in events:
        e = ev.get("event", {})
        g = ev.get("gate", {})
        t = ev.get("tavily", {})
        eid = e.get("event_id", "?")
        cid = e.get("clause_id", "?")
        tdate = e.get("trigger_date", "?")
        amt = e.get("dollar_amount")
        formula = e.get("dollar_formula")
        amt_str = f"${amt:.2f}" if isinstance(amt, (int, float)) and amt else (formula or "?")
        dec = g.get("decision", "?")
        verdict = t.get("verdict", "?")
        tier = t.get("source_tier", "?")
        reason = g.get("reason", "")
        if dec in counts:
            counts[dec] += 1
        ok = dec in ("ACCEPT", "DOWNGRADE", "REMOVE")
        event_ok = event_ok and ok
        mark = "✓" if ok else "✗"
        reason_short = reason[:45] if reason else ""
        print(f"  {eid}  {cid:<6}  {tdate}  {amt_str:<12}  {dec:<10}  {verdict}/{tier:<10}  {mark}  {reason_short}")

    print("-" * 60)
    print(f"  Summary: {counts['ACCEPT']} ACCEPT, {counts['DOWNGRADE']} DOWNGRADE, "
          f"{counts['REMOVE']} REMOVE")
    print("-" * 60)
    verdict_ok = hash_ok and event_ok
    print(f"  Verdict: {'✓ VALID' if verdict_ok else '✗ INVALID'}")
    print("=" * 60)
    return 0 if verdict_ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/verify_receipt.py <receipt.json>")
        sys.exit(2)
    sys.exit(verify(Path(sys.argv[1])))
