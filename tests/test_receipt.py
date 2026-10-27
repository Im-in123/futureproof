"""Receipt hash-chain tests."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.receipt.emit import emit_receipt
from app.receipt.ledger import (
    canonical,
    compute_self_hash,
    document_hash,
    sha256_hex,
)


@pytest.fixture
def tmp_ledger(tmp_path, monkeypatch):
    """Isolate the ledger per test."""
    ledger_file = tmp_path / "ledger.jsonl"
    import app.receipt.ledger as ledger_mod
    import app.receipt.emit as emit_mod
    monkeypatch.setattr(ledger_mod, "LEDGER_PATH", ledger_file)
    monkeypatch.setattr(emit_mod, "get_previous_hash",
                        lambda *a, **k: ledger_mod.get_previous_hash(ledger_file))
    return tmp_path, ledger_file


def sample_event(eid="ev_001", clause="§4.2(b)"):
    return {
        "event": {
            "event_id": eid, "clause_id": clause,
            "trigger_date": "2028-03-14",
            "dollar_amount": 340.0, "dollar_formula": None,
            "dollar_basis": "explicit_amount",
            "probability": 0.87,
            "probability_basis": "contractual obligation",
            "description": "rent increase",
        },
        "tavily": {
            "event_id": eid, "verdict": "VERIFIED",
            "query": "CA rent law",
            "source_url": "https://santa-ana.gov/",
            "source_tier": "official",
            "snippet": "2.87%",
            "published_date": "2026-08-31",
            "jurisdiction_match": True,
        },
        "gate": {
            "event_id": eid, "decision": "ACCEPT",
            "rules_fired": ["R1", "R2", "R3", "R4", "R5"],
            "reason": "all event rules passed",
        },
    }


def test_document_hash_is_deterministic():
    a = document_hash("hello world")
    b = document_hash("hello world")
    assert a == b
    assert a.startswith("sha256:")


def test_canonical_is_key_order_independent():
    a = canonical({"b": 2, "a": 1})
    b = canonical({"a": 1, "b": 2})
    assert a == b


def test_receipt_emits_with_valid_self_hash(tmp_ledger):
    tmp_path, _ = tmp_ledger
    events = [sample_event("ev_001"), sample_event("ev_002", "§7.1(a)")]
    receipt = emit_receipt("lease text here", events, output_dir=tmp_path)

    stored = receipt["self_hash"]
    recomputed = compute_self_hash(receipt)
    assert stored == recomputed, "self_hash must match recomputation"
    assert Path(receipt["_path"]).exists()


def test_receipt_chain_links_previous_hash(tmp_ledger):
    tmp_path, _ = tmp_ledger
    r1 = emit_receipt("doc one", [sample_event()], output_dir=tmp_path)
    r2 = emit_receipt("doc two", [sample_event()], output_dir=tmp_path)
    assert r1["previous_receipt_hash"] is None, "genesis has no previous"
    assert r2["previous_receipt_hash"] == r1["self_hash"], "chain must link"


def test_tampered_receipt_fails_verification(tmp_ledger):
    tmp_path, _ = tmp_ledger
    receipt = emit_receipt("doc", [sample_event()], output_dir=tmp_path)

    # Tamper: flip a decision from ACCEPT to REMOVE
    receipt["events"][0]["gate"]["decision"] = "REMOVE"

    stored = receipt["self_hash"]
    recomputed = compute_self_hash(receipt)
    assert stored != recomputed, "tampering must break the hash"


def test_verifier_script_on_real_receipt(tmp_ledger, capsys):
    import subprocess, sys
    tmp_path, _ = tmp_ledger
    receipt = emit_receipt("doc", [sample_event()], output_dir=tmp_path)

    result = subprocess.run(
        [sys.executable, "scripts/verify_receipt.py", receipt["_path"]],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"verifier failed: {result.stdout}\n{result.stderr}"
    assert "✓ VALID" in result.stdout
    assert receipt["receipt_id"] in result.stdout
