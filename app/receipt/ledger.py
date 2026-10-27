"""Tamper-evident hash-chained receipt ledger."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LEDGER_PATH = Path("receipts/ledger.jsonl")


def canonical(obj: Any) -> bytes:
    """Deterministic JSON for hashing: sorted keys, no whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def document_hash(text: str) -> str:
    return f"sha256:{sha256_hex(text.encode('utf-8'))}"


def get_previous_hash(ledger_path: Path | None = None) -> str | None:
    """Return self_hash of the last receipt in the chain, or None."""
    if ledger_path is None:
        ledger_path = LEDGER_PATH
    if not ledger_path.exists():
        return None
    last_line = None
    with ledger_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last_line = line
    if last_line is None:
        return None
    try:
        prev = json.loads(last_line)
        return prev.get("self_hash")
    except json.JSONDecodeError:
        return None


def compute_self_hash(receipt: dict) -> str:
    """Hash the receipt WITHOUT the self_hash field."""
    payload = {k: v for k, v in receipt.items()
               if k != "self_hash" and not k.startswith("_")}
    return f"sha256:{sha256_hex(canonical(payload))}"


def append_to_ledger(receipt: dict, ledger_path: Path | None = None) -> None:
    if ledger_path is None:
        ledger_path = LEDGER_PATH
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(receipt, sort_keys=True) + "\n")


def new_receipt_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y_%m_%dT%H%M%S")
    nonce = sha256_hex(str(datetime.now(timezone.utc).timestamp()).encode())[:6]
    return f"fp_{ts}_{nonce}"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
