"""Run the pipeline on each case. Distinguish real failures from infra failures."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.pipeline.orchestrate import simulate

RESULTS_PATH = Path("tests/corpus/results.json")


def _find_rate_event(receipt):
    for ev in receipt.get("events", []):
        if ev["event"].get("rate_pct") is not None:
            return ev
    return None


def _classify_failure(actual, error_msg):
    """Distinguish product bugs from infrastructure failures."""
    if error_msg:
        if any(kw in error_msg.lower() for kw in
               ["connection", "timeout", "rate limit", "429", "503",
                "apiconnection", "internal server"]):
            return "INFRA"
        return "PRODUCT"
    if actual == "NO_RATE_EVENT":
        return "PRODUCT"
    return "PRODUCT"


def run():
    from tests.corpus.cases import CASES
    results = []
    print(f"Running {len(CASES)} adversarial cases...\n")

    for i, case in enumerate(CASES, 1):
        print(f"[{i}/{len(CASES)}] {case['name']}: {case['rate']}% in {case['jurisdiction']} "
              f"(expected {case['expected']})")
        t0 = time.time()
        error_msg = None
        try:
            receipt = simulate(case["text"], case["jurisdiction"], case["base_rent"])
            rate_ev = _find_rate_event(receipt)
            actual = rate_ev["gate"]["decision"] if rate_ev else "NO_RATE_EVENT"
            actual_verdict = rate_ev["tavily"]["verdict"] if rate_ev else None
            actual_reason = rate_ev["gate"]["reason"] if rate_ev else "no rate event found"
        except Exception as exc:
            actual = "ERROR"
            actual_verdict = None
            actual_reason = ""
            error_msg = f"{type(exc).__name__}: {exc}"

        elapsed = round(time.time() - t0, 1)
        passed = (actual == case["expected"])
        failure_kind = None if passed else _classify_failure(actual, error_msg)

        results.append({
            "name": case["name"],
            "category": case["category"],
            "jurisdiction": case["jurisdiction"],
            "rate": case["rate"],
            "expected": case["expected"],
            "actual": actual,
            "actual_verdict": actual_verdict,
            "reason": actual_reason,
            "passed": passed,
            "failure_kind": failure_kind,
            "error": error_msg,
            "elapsed_s": elapsed,
            "note": case["note"],
        })
        status = "✓ PASS" if passed else f"✗ {failure_kind} FAIL"
        print(f"  → {actual:12} {status}  ({elapsed}s)")

    # Split product vs infra
    executed = [r for r in results if r["failure_kind"] != "INFRA"]
    product_passed = sum(1 for r in executed if r["passed"])
    product_total = len(executed)
    product_accuracy = round(product_passed / product_total, 3) if product_total else 0

    raw_passed = sum(1 for r in results if r["passed"])
    raw_total = len(results)

    by_category = {}
    for r in results:
        cat = r["category"]
        if cat not in by_category:
            by_category[cat] = {"total": 0, "passed": 0, "product_total": 0, "product_passed": 0}
        by_category[cat]["total"] += 1
        if r["passed"]:
            by_category[cat]["passed"] += 1
        if r["failure_kind"] != "INFRA":
            by_category[cat]["product_total"] += 1
            if r["passed"]:
                by_category[cat]["product_passed"] += 1

    summary = {
        "run_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "raw": {"total": raw_total, "passed": raw_passed,
                "accuracy": round(raw_passed / raw_total, 3) if raw_total else 0},
        "product": {"total": product_total, "passed": product_passed,
                    "accuracy": product_accuracy},
        "by_category": by_category,
        "failures": [r for r in results if not r["passed"]],
        "results": results,
    }
    RESULTS_PATH.write_text(json.dumps(summary, indent=2))

    print(f"\n{'='*60}")
    print(f"  Product accuracy: {product_passed}/{product_total} "
          f"({product_accuracy*100:.0f}%)  — excluding infra failures")
    print(f"  Raw:              {raw_passed}/{raw_total} "
          f"({summary['raw']['accuracy']*100:.0f}%)  — includes rate-limit failures")
    print(f"{'='*60}")
    for cat, s in by_category.items():
        print(f"  {cat:12}  {s['product_passed']}/{s['product_total']} product   "
              f"({s['passed']}/{s['total']} raw)")
    return summary


if __name__ == "__main__":
    run()
