# FutureProof

**Consequence timeline for any contract.**

Upload a lease, employment offer, or insurance policy. FutureProof shows every future cost — the exact date it fires, the dollar amount, and whether it's legal in your jurisdiction.

Illegal clauses are blocked by a deterministic Python gate. Legal-but-expensive fees are flagged. When no reliable legal source exists, the system says *"I cannot determine."*

Every analysis produces a hash-chained receipt that verifies in a fresh terminal with no app running.

🎬 **Demo video:** https://youtu.be/UnnY0YSMCaI
---

## The Problem

Leases hide clauses that fire years later. A rent increase on the first anniversary. An auto-renewal at month 22. A maintenance shift at month 9. You can't see the date, the dollar amount, or whether the clause is even legal. You sign, and months later it fires.

FutureProof is built for the person signing that contract tomorrow. No lawyer, no time to read 8-point legal text, no way to know if the 18% rent increase in section 2 is normal or a trap.

---

## What It Does

1. **Upload a contract** — `.pdf`, `.txt`, or `.md`
2. **See a consequence timeline** — every future cost with the firing date and dollar amount
3. **Get a verdict per clause** — one of four honest states:

| State | Meaning |
|---|---|
| **LEGAL** (green) | Enforceable. Plan for the cost. |
| **ILLEGAL** (red) | Exceeds the jurisdiction's legal cap. Blocked. |
| **UNCERTAIN** (yellow) | Source exists but isn't authoritative. Consult a lawyer. |
| **NO EVIDENCE** (gray) | Cannot determine. The system says so. |

4. **Negotiate with a number** — *"If you negotiate from 18% to 8%, you save $15,024 over the life of the contract."*
5. **Compare two leases** — side by side, to answer *"which is safer?"*
6. **Download the receipt** — a hash-chained JSON file verifiable by anyone

---

## How It Works

The pipeline is five stages, and no stage trusts the one before it.

```
Document → Extract → Reason → Verify → Gate → Receipt
```

| Stage | What happens | Model |
|---|---|---|
| **Extract** | Every clause with a monetary consequence or legal right, structured as JSON | Nemotron 3.5 Lightning (reasoning off, temp 0) |
| **Reason** | Computes firing dates and dollar impacts from each clause | Nemotron 3.5 Super (reasoning on) |
| **Normalize** | Forces annual impact for rent clauses: `rate × base_rent × 12` | Plain Python |
| **Verify** | Per-event Tavily search for the jurisdiction's statutory cap | Tavily advanced search |
| **Gate** | Applies 6 event rules + 4 source rules. Every rejection cites a rule ID | Plain Python |

**The gate is code, not a second LLM call.** The money rule is **R6**:

```python
if event.rate_pct > tavily.legal_rate_pct * 1.01:
    return REMOVE
```

When the clause says 18% and California caps at 10%, R6 fires with the exact reason: *"clause rate 18.00% exceeds verified legal max 10.00%."* A 10.5% rate against a 10% cap fires. A 10.0% rate does not. The model cannot override the gate.

The gate is deterministic Python. Its behavior is testable with `pytest`. The receipt records every rule that fired.

---

## The Receipt

Every event — including blocked ones — is serialized to canonical JSON and hashed with SHA-256. Verify it in a fresh terminal with no app running:

```bash
python scripts/verify_receipt.py receipts/fp_2026_10_27T023041_178c38.json
```

Output:

```
════════════════════════════════════════
  FutureProof Receipt Verification
════════════════════════════════════════
  Receipt ID:  fp_2026_10_27T023041_178c38
  Hash integrity: ✓ VALID
  Events: 5
  Verdict: ✓ VALID
════════════════════════════════════════
```

The receipt is a cryptographic proof, not a screenshot. A bank, a court, or a dispute service can recompute the hash without trusting the app.

---

## The Adversarial Corpus

`tests/corpus/` runs the pipeline against **12 labeled test cases** across California, New York, Oregon, and Wyoming:

- Safe rates (3%, 4%, 8%, 9%) → should ACCEPT
- Edge cases (exactly 10%, exactly 5%) → should ACCEPT
- Predatory rates (10.5%, 12%, 18%, 25%) → should REMOVE
- Unknown jurisdiction (Wyoming) → should NO_EVIDENCE

**Result:** 10/10 product accuracy on cases that executed.

**The corpus found a real bug.** A 5% tolerance in R6 was letting a 10.5% rate pass a 10% cap. Fixed to 1% float tolerance. Re-verified. Published on the `/corpus` page.

The two raw failures are NVIDIA rate limits, labeled honestly on the page.

Run it yourself:

```bash
python -m tests.corpus.runner
```

---

## Quickstart

### Prerequisites

- Python 3.11+
- Node 20+
- An NVIDIA API key (`build.nvidia.com`)
- A Tavily API key (`tavily.com` — 1,000 free credits/month)

### Install

```bash
git clone https://github.com/Im-in123/futureproof.git
cd futureproof
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### Configure

```bash
cp .env.example .env
```

Edit `.env`:

```
NVIDIA_API_KEY=nvapi-...
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NEMOTRON_LIGHTNING_MODEL=nvidia/nemotron-3.5-lightning-30b-a3b
NEMOTRON_SUPER_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b
TAVILY_API_KEY=tvly-...
```

### Run

```bash
# Backend (FastAPI on :9090)
python scripts/serve.py

# Frontend (Vite on :5173) — in another terminal
cd frontend && npm run dev
```

Open `http://127.0.0.1:5173/`

### Verify a receipt

```bash
python scripts/verify_receipt.py receipts/<receipt_id>.json
```

---

## The Nebius Situation — Documented Blocker

The pipeline was **built for Nebius Token Factory**. The OpenAI SDK client points at `https://api.tokenfactory.nebius.com/v1/` by default. The pricing table uses Nebius's published rates. The models are Nemotron 3.5 — the same models served on both platforms.

**At runtime, the demo runs on NVIDIA's free Nemotron endpoint.** Ghana is on Nebius's restricted-country list for account creation. The promo code from the Devpost form arrived but cannot be applied without a billing account with a card, and adding a card from Ghana is blocked at the country dropdown. The Builder Program application was declined for the same reason. **Nebius support confirmed directly that they cannot help with the country restriction.**

**What porting requires:**

1. Update `NEBIUS_BASE_URL` and `NEBIUS_API_KEY` in `.env` (2 lines)
2. Update the two model IDs from NVIDIA's catalog to Nebius's catalog
3. Verify the `reasoning_effort` parameter is accepted by Nebius's endpoint

Realistic estimate: **30 minutes of testing**, not a rewrite. The gate, the receipt, the Tavily verification, and the frontend are all platform-agnostic.

This is a documented blocker, not a design choice.

---

## Features

- PDF / TXT / Markdown upload
- 10 US jurisdictions (CA, NY, OR, WA, MA, CO, IL, NJ, MD, MN)
- Clause extraction with structured JSON output
- Automatic firing date computation
- Deterministic dollar amount per clause
- Tavily live statutory verification
- Deterministic gate — 6 event rules, 4 source rules
- Rate compliance check (R6)
- Four honest verdicts including NO EVIDENCE
- Visual rate bar — clause rate vs legal cap
- Counterfactual negotiation tool
- Comparison mode (two leases side by side)
- Hash-chained receipt
- Download receipt as JSON
- Copy share link
- Public verifier URL
- Standalone verifier script
- Adversarial corpus — 12 cases, 10/10 product accuracy
- Model attribution table with tokens, latency, cost per call
- Response caching for reproducible demos
- Progress bar with real pipeline stages

---

## Tech Stack

- **Models:** NVIDIA Nemotron 3.5 Lightning + Super
- **Verification:** Tavily advanced search
- **Backend:** Python 3.11, FastAPI, Pydantic
- **Frontend:** React 18, TypeScript, Vite, TailwindCSS
- **Receipt:** SHA-256 hash chain, canonical JSON
- **Tests:** pytest — 20 unit tests, 12-case corpus

---

## Tests

```bash
pytest tests/ -v
```

All 20 unit tests pass.

---

## License

MIT — see [LICENSE](./LICENSE).

---

## Built For

The Nebius x NVIDIA Global AI Hackathon 2026 — Best Apps & Agents track.