"""Assemble and emit a signed, hash-chained receipt."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.receipt.ledger import (
    append_to_ledger,
    compute_self_hash,
    document_hash,
    get_previous_hash,
    new_receipt_id,
    now_iso,
)


def emit_receipt(
    document_text: str,
    events: list[dict[str, Any]],
    model_metadata: dict[str, Any] | None = None,
    output_dir: Path = Path("receipts"),
) -> dict:
    """
    events: list of {"event": {...}, "tavily": {...}, "gate": {...}}
    Returns the full receipt dict with self_hash.
    """
    receipt = {
        "receipt_id": new_receipt_id(),
        "created_at": now_iso(),
        "document_hash": document_hash(document_text),
        "previous_receipt_hash": get_previous_hash(),
        "model_metadata": model_metadata or {},
        "events": events,
    }
    receipt["self_hash"] = compute_self_hash(receipt)

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{receipt['receipt_id']}.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")

    append_to_ledger(receipt)
    receipt["_path"] = str(path)
    return receipt
