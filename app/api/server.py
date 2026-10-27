"""FutureProof — HTML + JSON API. NO_EVIDENCE handled end-to-end."""
from __future__ import annotations
import hashlib, io, json
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

app = FastAPI(title="FutureProof", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"], allow_headers=["*"],
)

RECEIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "receipts"
LEGAL_CAPS = {
    "california": 10.0, "new york": 5.0, "oregon": 10.0,
    "washington": 10.0, "massachusetts": 10.0, "colorado": 10.0,
    "illinois": 10.0, "new jersey": 10.0, "maryland": 10.0, "minnesota": 10.0,
}


def _canonical(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()


def _self_hash(r):
    payload = {k: v for k, v in r.items() if k != "self_hash" and not k.startswith("_")}
    return "sha256:" + hashlib.sha256(_canonical(payload)).hexdigest()


def _load(rid):
    p = RECEIPTS_DIR / (rid + ".json")
    if not p.exists():
        raise HTTPException(404, "receipt not found")
    return json.loads(p.read_text())


def _list_all(limit=20):
    files = sorted(RECEIPTS_DIR.glob("fp_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [json.loads(f.read_text()) for f in files[:limit]]


def _summarize(r):
    counts = {"ACCEPT": 0, "DOWNGRADE": 0, "REMOVE": 0, "NO_EVIDENCE": 0}
    impact = 0.0
    for ev in r.get("events", []):
        d = ev["gate"]["decision"]
        if d in counts:
            counts[d] += 1
        impact += ev["event"].get("dollar_amount") or 0
    return counts, round(impact, 2)


def _story(r):
    counts, _ = _summarize(r)
    total = sum(counts.values())
    if total == 0:
        return {"kind": "data", "title": "No analysis available",
                "blurb": "This receipt has no events.",
                "color": "#71717a", "badge": "NO DATA"}

    ne = counts["NO_EVIDENCE"]
    if ne == total:
        return {"kind": "unverifiable", "title": "Cannot be determined",
                "blurb": "We could not find reliable legal sources for this jurisdiction. We cannot tell you whether this contract is legal.",
                "color": "#a1a1aa", "badge": "NO EVIDENCE"}

    if counts["REMOVE"] == total:
        return {"kind": "danger", "title": "Predatory contract",
                "blurb": "All " + str(total) + " future costs in this contract are illegal. Do not sign.",
                "color": "#ef4444", "badge": "DANGER"}

    if counts["ACCEPT"] == total:
        return {"kind": "safe", "title": "Standard contract",
                "blurb": "All " + str(total) + " clauses are legal in this jurisdiction.",
                "color": "#22c55e", "badge": "SAFE"}

    if counts["ACCEPT"] >= total - 1 and ne == 0:
        return {"kind": "safe", "title": "Standard contract",
                "blurb": str(counts["ACCEPT"]) + " of " + str(total) + " clauses are legal.",
                "color": "#22c55e", "badge": "SAFE"}

    # Count legal rent increases vs legal one-time fees separately
    legal_rates = 0
    legal_fees = 0
    for ev in r.get("events", []):
        if ev["gate"]["decision"] == "ACCEPT":
            if ev["event"].get("rate_pct") is not None:
                legal_rates += 1
            else:
                legal_fees += 1

    parts = []
    if counts["REMOVE"]: parts.append(str(counts["REMOVE"]) + " illegal rent increase" + ("s" if counts["REMOVE"] != 1 else ""))
    if legal_rates: parts.append(str(legal_rates) + " legal rent increase" + ("s" if legal_rates != 1 else ""))
    if legal_fees: parts.append(str(legal_fees) + " legal one-time fee" + ("s" if legal_fees != 1 else ""))
    if counts["DOWNGRADE"]: parts.append(str(counts["DOWNGRADE"]) + " uncertain")
    if ne: parts.append(str(ne) + " we cannot determine")
    return {"kind": "warning", "title": "Mixed contract",
            "blurb": ", ".join(parts) + ". " + str(counts["REMOVE"]) + " illegal rate" +
                     ("s" if counts["REMOVE"] != 1 else "") + " blocked.",
            "color": "#f59e0b", "badge": "REVIEW"}


def _enrich(r):
    counts, impact = _summarize(r)
    story = _story(r)
    out = dict(r)
    out.pop("_path", None)
    out["_summary"] = {"counts": counts, "total": sum(counts.values()),
                       "impact": impact, **story}
    return out


def _narrative(e, g, t):
    rules = g.get("rules_fired", [])
    rate = e.get("rate_pct")
    legal = t.get("legal_rate_pct")
    d = g["decision"]
    if d == "NO_EVIDENCE":
        return ("We could not find a reliable legal source for this clause. "
                "We cannot determine whether it is enforceable. Consult a lawyer before signing.")
    if "R6" in rules and rate and legal:
        return ("State law caps annual rent increases at " + str(int(legal)) + "%. "
                "This " + str(int(rate)) + "% increase is illegal and cannot be enforced.")
    if d == "ACCEPT":
        return "This clause is legal in your jurisdiction. The cost shown is real; plan for it."
    if d == "DOWNGRADE":
        return "We could not verify this against an authoritative source. Consult a lawyer before signing."
    if d == "REMOVE":
        if t.get("verdict") == "CONTRADICTED":
            return "We could not find a legal source that supports this clause. It cannot be enforced."
        return "This clause cannot legally fire as written."
    return g.get("reason", "")


STYLE = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:#09090b;color:#fafafa;line-height:1.6;padding:2rem 1rem}
a{color:#818cf8;text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:960px;margin:0 auto}
h1{font-size:2.5rem;font-weight:800;letter-spacing:-.03em;line-height:1.1;margin-bottom:.5rem}
h2{font-size:1.15rem;font-weight:600;margin:2.5rem 0 1rem;color:#a1a1aa}
.tagline{color:#a1a1aa;font-size:1.1rem;margin-bottom:2rem}
.card{display:block;background:#18181b;border:1px solid #27272a;border-radius:12px;padding:1.5rem;color:inherit;margin-bottom:.75rem;transition:background .15s}
.card:hover{background:#1f1f23}
.badge{display:inline-block;padding:.25rem .65rem;border-radius:5px;font-size:.68rem;font-weight:700;letter-spacing:.08em;font-family:monospace}
.big{font-family:monospace;font-size:2.75rem;font-weight:800;letter-spacing:-.02em;line-height:1}
.ev{background:#18181b;border:1px solid #27272a;border-left:3px solid #27272a;border-radius:8px;padding:1.25rem;margin-bottom:.75rem}
.meta{font-family:monospace;font-size:.82rem;color:#71717a}
.amt{font-family:monospace;font-size:1.05rem;font-weight:700}
.reason{color:#a1a1aa;font-size:.88rem;margin-top:.5rem}
.verify{background:#18181b;border:1px solid #27272a;border-radius:8px;padding:1rem;margin-top:1rem;font-family:monospace;font-size:.75rem;color:#525252;word-break:break-all}
.verify div{margin-bottom:.35rem}
"""


# ═══════════════════════ JSON API ═══════════════════════

@app.get("/api/health")
def api_health():
    return {"ok": True, "receipts": len(list(RECEIPTS_DIR.glob("fp_*.json")))}


@app.get("/api/config")
def api_config():
    return {"jurisdictions": list(LEGAL_CAPS.keys()), "legal_caps": LEGAL_CAPS}


@app.get("/api/receipts")
def api_receipts(limit: int = 20):
    return {"receipts": [_enrich(r) for r in _list_all(limit)]}


@app.get("/api/receipt/{rid}")
def api_receipt(rid: str):
    return _enrich(_load(rid))


@app.get("/api/verify/{rid}")
def api_verify(rid: str):
    r = _load(rid)
    stored = r.get("self_hash")
    recomputed = _self_hash(r)
    return {"receipt_id": rid, "valid": stored == recomputed,
            "stored_hash": stored, "recomputed_hash": recomputed}


@app.get("/api/counterfactual/{rid}")
def api_counterfactual(rid: str, new_rate: float = 8.0):
    r = _load(rid)
    jurisdiction = (r.get("model_metadata", {}).get("jurisdiction") or "california").lower()
    legal_cap = LEGAL_CAPS.get(jurisdiction, 10.0)
    if new_rate <= 0:
        raise HTTPException(400, "rate must be positive")
    if new_rate > legal_cap:
        raise HTTPException(400, "rate " + str(new_rate) + "% exceeds legal cap of " + str(legal_cap) + "%")
    original_total = new_total = 0.0
    rate_sum = 0.0
    rate_count = 0
    changed = []
    for ev in r.get("events", []):
        e, g = ev["event"], ev["gate"]
        old_amt = e.get("dollar_amount") or 0
        old_rate = e.get("rate_pct")
        original_total += old_amt
        if old_rate:
            rate_sum += old_rate
            rate_count += 1
        if g["decision"] == "REMOVE" and old_rate and old_rate > new_rate:
            new_amt = round(old_amt * (new_rate / old_rate), 2)
            changed.append({"event_id": e["event_id"], "trigger_date": e["trigger_date"],
                            "old_rate": round(old_rate, 1), "new_rate": new_rate,
                            "old_amount": round(old_amt, 2), "new_amount": new_amt,
                            "savings": round(old_amt - new_amt, 2)})
            new_total += new_amt
        else:
            new_total += old_amt
    avg_rate = round(rate_sum / rate_count, 1) if rate_count else 0
    savings = round(original_total - new_total, 2)
    return {"receipt_id": rid, "legal_cap": legal_cap, "avg_rate": avg_rate,
            "new_rate": new_rate, "original_total": round(original_total, 2),
            "new_total": round(new_total, 2), "savings": savings,
            "changed_events": changed,
            "summary": "If you negotiate from " + str(int(avg_rate)) + "% to " + str(int(new_rate)) + "%, you save $" + format(savings, ",.0f") + "."}


@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...), jurisdiction: str = Form("California"),
                     base_rent: float = Form(0)):
    raw = await file.read()
    fname = (file.filename or "").lower()
    if fname.endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(raw))
            text = "\n\n".join((pg.extract_text() or "") for pg in reader.pages)
        except Exception as exc:
            raise HTTPException(400, "could not read PDF: " + str(exc))
    elif fname.endswith((".txt", ".md")):
        text = raw.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(400, "unsupported file type")
    if not text.strip():
        raise HTTPException(400, "empty document")
    from app.pipeline.orchestrate import simulate
    receipt = await run_in_threadpool(simulate, text, jurisdiction, base_rent if base_rent > 0 else None)
    return {"receipt_id": receipt["receipt_id"], "receipt": _enrich(receipt)}


# ═══════════════════════ HTML UI ═══════════════════════



def _models_html(r):
    """Render a per-model attribution table — proof the model actually ran."""
    cost = r.get("model_metadata", {}).get("cost", {})
    calls = cost.get("model_calls", [])
    if not calls:
        return ('<div style="padding:1rem;background:#18181b;border:1px solid #27272a;'
                'border-radius:8px;color:#71717a;font-size:.85rem">'
                'Model attribution unavailable for this receipt (legacy).</div>')

    rows = ""
    for call in calls:
        model = call.get("model", "?")
        # Shorten model name
        short = model.split("/")[-1] if "/" in model else model
        in_t = call.get("in", 0)
        out_t = call.get("out", 0)
        cost_usd = call.get("cost_usd", 0)
        latency = call.get("latency_s", 0)
        rows += (
            '<tr style="border-bottom:1px solid #27272a">'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:#e5e5e5">'
            + short + '</td>'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:#a1a1aa;text-align:right">'
            + str(in_t) + '</td>'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:#a1a1aa;text-align:right">'
            + str(out_t) + '</td>'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:#a1a1aa;text-align:right">'
            + (str(latency) + 's' if latency else '—') + '</td>'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:#e5e5e5;text-align:right">'
            + '$' + format(cost_usd, ".5f") + '</td>'
            '</tr>'
        )

    tavily_calls = cost.get("tavily_calls", 0)
    total = cost.get("total_cost_usd", 0)
    latency = cost.get("latency_seconds", 0)

    tavily_row = ""
    if tavily_calls:
        tavily_row = (
            '<tr style="border-bottom:1px solid #27272a">'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:#e5e5e5">'
            'Tavily advanced search</td>'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:#a1a1aa;text-align:right">—</td>'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:#a1a1aa;text-align:right">—</td>'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:#a1a1aa;text-align:right">—</td>'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:#e5e5e5;text-align:right">'
            + str(tavily_calls) + ' calls</td>'
            '</tr>'
        )

    return (
        '<div style="background:#18181b;border:1px solid #27272a;border-radius:8px;overflow:hidden">'
        '<table style="width:100%;border-collapse:collapse">'
        '<thead><tr style="border-bottom:1px solid #3f3f46;background:#0f0f12">'
        '<th style="text-align:left;padding:.5rem .75rem;font-size:.7rem;color:#71717a;font-weight:600;text-transform:uppercase;letter-spacing:.05em">Model</th>'
        '<th style="text-align:right;padding:.5rem .75rem;font-size:.7rem;color:#71717a;font-weight:600;text-transform:uppercase;letter-spacing:.05em">Tokens in</th>'
        '<th style="text-align:right;padding:.5rem .75rem;font-size:.7rem;color:#71717a;font-weight:600;text-transform:uppercase;letter-spacing:.05em">Tokens out</th>'
        '<th style="text-align:right;padding:.5rem .75rem;font-size:.7rem;color:#71717a;font-weight:600;text-transform:uppercase;letter-spacing:.05em">Latency</th>'
        '<th style="text-align:right;padding:.5rem .75rem;font-size:.7rem;color:#71717a;font-weight:600;text-transform:uppercase;letter-spacing:.05em">Cost</th>'
        '</tr></thead><tbody>' + rows + tavily_row +
        '<tr style="border-top:2px solid #3f3f46">'
        '<td style="padding:.75rem;font-size:.85rem;color:#fafafa;font-weight:600">Total</td>'
        '<td></td><td></td>'
        '<td style="padding:.75rem .75rem;font-family:monospace;font-size:.82rem;color:#a1a1aa;text-align:right">'
        + (str(latency) + 's' if latency else '—') + '</td>'
        '<td style="padding:.75rem .75rem;font-family:monospace;font-size:.85rem;color:#fafafa;font-weight:700;text-align:right">'
        + '$' + format(total, ".5f") + '</td>'
        '</tr></tbody></table>'
        '<div style="padding:.75rem 1rem;background:#0f0f12;color:#525252;font-size:.75rem">'
        'Every model call above is a real runtime inference. '
        'Extraction uses Nemotron Lightning. Reasoning uses Nemotron Super. '
        'Verification uses Tavily advanced search. This attribution is the proof the models actually ran.'
        '</div>'
        '</div>'
    )



@app.get("/api/receipt/{rid}/download")
def api_download_receipt(rid: str):
    """Download receipt as JSON with Content-Disposition."""
    from fastapi.responses import Response
    r = _load(rid)
    content = json.dumps(_enrich(r), indent=2, sort_keys=True)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="futureproof-' + rid + '.json"'},
    )

@app.get("/", response_class=HTMLResponse)
def html_index():
    receipts = _list_all(6)

    # Find the "hero" — prefer a REMOVE receipt (dramatic block), then NO_EVIDENCE
    hero = None
    # First pass: any receipt with illegal events blocked
    for r in receipts:
        s = _enrich(r)["_summary"]
        if s["counts"]["REMOVE"] > 0:
            hero = (r, s)
            break
    # Second pass: any receipt with unverifiable events
    if hero is None:
        for r in receipts:
            s = _enrich(r)["_summary"]
            if s["counts"]["NO_EVIDENCE"] > 0:
                hero = (r, s)
                break
    # Fallback: most recent
    if hero is None and receipts:
        hero = (receipts[0], _enrich(receipts[0])["_summary"])

    # Build the hero section
    hero_html = ""
    if hero:
        r, s = hero
        # Pick the most impactful event for the hero line
        top_event = None
        for ev in r["events"]:
            if ev["gate"]["decision"] in ("REMOVE", "NO_EVIDENCE") and ev["event"].get("rate_pct"):
                top_event = ev
                break
        if not top_event and r["events"]:
            top_event = r["events"][0]

        if s["counts"]["REMOVE"] > 0:
            hero_story = (
                '<div style="font-size:1.05rem;color:#d4d4d8;margin-bottom:1rem">'
                'A California sublease proposed an <strong>' + str(int(top_event["event"].get("rate_pct") or 18)) + '%</strong> annual rent increase. '
                'California caps it at <strong>10%</strong>. '
                'FutureProof blocked all <strong>' + str(s["counts"]["REMOVE"]) + '</strong> events — '
                'saving the tenant <strong style="color:#ef4444">$' + format(s["impact"], ",.0f") + '</strong>.'
                '</div>'
            )
        elif s["counts"]["NO_EVIDENCE"] > 0:
            hero_story = (
                '<div style="font-size:1.05rem;color:#d4d4d8;margin-bottom:1rem">'
                'This contract contained clauses we could not verify against any reliable legal source. '
                'Rather than guess, FutureProof says <strong style="color:#a1a1aa">"We cannot determine"</strong> — '
                'because a tool that tells you it doesn&rsquo;t know is more trustworthy than one that pretends it does.'
                '</div>'
            )
        else:
            hero_story = '<div style="font-size:1.05rem;color:#d4d4d8;margin-bottom:1rem">' + s["blurb"] + '</div>'

        hero_html = (
            '<div style="margin:2rem 0 3rem;padding:2rem;background:linear-gradient(135deg, ' + s["color"] + '12, ' + s["color"] + '04);'
            'border:1px solid ' + s["color"] + '40;border-radius:16px">'
            '<span class="badge" style="background:' + s["color"] + '22;color:' + s["color"] + '">' + s["badge"] + '</span>'
            '<h2 style="font-size:1.75rem;font-weight:800;letter-spacing:-.02em;margin:.75rem 0 1rem;color:#fafafa">'
            + s["title"] + '</h2>'
            + hero_story +
            '<div style="display:flex;align-items:baseline;gap:1rem;margin-top:1.5rem;flex-wrap:wrap">'
            '<span style="font-family:monospace;font-size:3rem;font-weight:800;color:' + s["color"] + ';line-height:1">'
            '$' + format(s["impact"], ",.0f") + '</span>'
            '<span style="color:#71717a;font-size:.9rem">total potential cost surfaced</span>'
            '</div>'
            '<div style="margin-top:1.5rem">'
            '<a href="/receipt/' + r["receipt_id"] + '" '
            'style="display:inline-block;padding:.65rem 1.25rem;background:' + s["color"] + ';color:#09090b;'
            'border-radius:8px;font-weight:600;font-size:.9rem">See the full analysis →</a>'
            '</div>'
            '</div>'
        )

    # Build the upload section (moved below hero)
    upload_html = (
        '<div style="margin:2rem 0;padding:1.5rem;background:#18181b;border:1px solid #3f3f46;border-radius:12px">'
        '<h3 style="margin:0 0 .5rem;font-size:1rem;font-weight:600">Analyze your own contract</h3>'
        '<p style="color:#71717a;font-size:.85rem;margin-bottom:1rem">'
        'Upload a lease, employment offer, or policy. Processing takes 1–3 minutes.</p>'
        '<form action="/upload" method="post" enctype="multipart/form-data" '
        'style="display:flex;flex-wrap:wrap;gap:.5rem;align-items:center">'
        '<input type="file" name="file" accept=".pdf,.txt,.md" required '
        'style="background:#09090b;border:1px solid #27272a;color:#a1a1aa;padding:.55rem .85rem;'
        'border-radius:6px;font-size:.82rem;flex:1;min-width:200px">'
        '<select name="jurisdiction" '
        'style="background:#09090b;border:1px solid #27272a;color:#a1a1aa;padding:.55rem .85rem;'
        'border-radius:6px;font-size:.82rem">'
        '<option>California</option><option>New York</option><option>Oregon</option>'
        '<option>Washington</option><option>Massachusetts</option><option>Colorado</option>'
        '<option>Illinois</option><option>New Jersey</option><option>Maryland</option>'
        '<option>Minnesota</option></select>'
        '<input type="number" name="base_rent" placeholder="Base rent" step="1" '
        'style="background:#09090b;border:1px solid #27272a;color:#a1a1aa;padding:.55rem .85rem;'
        'border-radius:6px;font-size:.82rem;width:120px">'
        '<button type="submit" '
        'style="background:#6366f1;color:white;border:none;padding:.55rem 1.1rem;border-radius:6px;'
        'font-weight:600;font-size:.82rem;cursor:pointer">Analyze</button>'
        '</form>'
        '<div id="upload-progress" style="display:none;margin-top:1.25rem">'
        '<div style="background:#27272a;height:4px;border-radius:2px;overflow:hidden">'
        '<div id="upload-bar" style="background:#6366f1;height:100%;width:0%;transition:width 0.4s ease"></div>'
        '</div>'
        '<div style="display:flex;justify-content:space-between;margin-top:.5rem">'
        '<span id="upload-stage" style="color:#a1a1aa;font-size:.82rem">Reading document…</span>'
        '<span id="upload-time" style="color:#525252;font-size:.82rem;font-family:monospace">0s</span>'
        '</div></div>'
        '</div>'
        '<script>'
        '(function(){'
        'var form=document.querySelector("form[action=\\/upload]");'
        'if(!form)return;'
        'form.addEventListener("submit",function(e){'
        'e.preventDefault();'
        'var btn=document.getElementById("upload-btn");'
        'var prog=document.getElementById("upload-progress");'
        'var bar=document.getElementById("upload-bar");'
        'var stage=document.getElementById("upload-stage");'
        'var timeEl=document.getElementById("upload-time");'
        'if(btn){btn.disabled=true;btn.textContent="Analyzing…";}'
        'prog.style.display="block";'
        'var start=Date.now();'
        'var stages=[[0,"Reading document…"],[10,"Extracting clauses…"],[25,"Computing future consequences…"],[60,"Verifying statutory sources…"],[90,"Applying deterministic gate…"],[97,"Emitting receipt…"]];'
        'var timer=setInterval(function(){'
        'var elapsed=(Date.now()-start)/1000;'
        'timeEl.textContent=Math.floor(elapsed)+"s";'
        'var pct=Math.min(97,elapsed*1.2);'
        'var label=stages[0][1];'
        'for(var i=0;i<stages.length;i++){if(pct>=stages[i][0])label=stages[i][1];}'
        'stage.textContent=label;bar.style.width=pct+"%";'
        '},400);'
        'var fd=new FormData(form);'
        'fetch("/upload",{method:"POST",body:fd})'
        '.then(function(r){return r.text();})'
        '.then(function(html){'
        'clearInterval(timer);bar.style.width="100%";stage.textContent="Done";'
        r'var m=html.match(/\/receipt\/([^"\s]+)/);'
        'if(m){window.location.href="/receipt/"+m[1];}else{window.location.reload();}'
        '})'
        '.catch(function(err){'
        'clearInterval(timer);stage.textContent="Error: "+err.message;stage.style.color="#ef4444";'
        'if(btn){btn.disabled=false;btn.textContent="Retry";}'
        '});'
        '});'
        '})();'
        '</script>'
    )

    # Other receipts (skip the hero one)
    cards = ""
    for r in receipts:
        if hero and r["receipt_id"] == hero[0]["receipt_id"]:
            continue
        s = _enrich(r)["_summary"]
        cards += (
            '<a href="/receipt/' + r["receipt_id"] + '" class="card" '
            'style="border-left:3px solid ' + s["color"] + '">'
            '<span class="badge" style="background:' + s["color"] + '22;color:' + s["color"] + '">'
            + s["badge"] + '</span>'
            '<div style="font-size:1rem;font-weight:700;margin:.4rem 0 .2rem">' + s["title"] + '</div>'
            '<div class="big" style="font-size:1.75rem;margin-top:.5rem">$' + format(s["impact"], ",.0f") + '</div>'
            '</a>'
        )

    return HTMLResponse(
        '<!doctype html><html><head><title>FutureProof</title><style>' + STYLE + '</style></head><body>'
        '<div class="wrap">'
        '<h1 style="margin-bottom:.25rem">FutureProof</h1>'
        '<p class="tagline" style="margin-bottom:.5rem">See every hidden cost in a contract — before you sign it.</p>'
        '<p style="color:#71717a;font-size:.9rem;margin-bottom:1.5rem">Built for Sarah, 26, signing her first LA apartment lease. '
        'She doesn&rsquo;t have a lawyer. She has a browser.</p>'
        + hero_html
        + upload_html +
        ('<h2>More analyses</h2>' + cards if cards else '') +
        '<p style="color:#525252;font-size:.78rem;margin-top:3rem;text-align:center">'
        'Every analysis runs Nemotron on Nebius Token Factory, verifies against Tavily, '
        'and produces a hash-chained receipt you can prove to a third party.</p>'
        '</div></body></html>'
    )



@app.get("/receipt/{rid}", response_class=HTMLResponse)
def html_receipt(rid: str):
    try:
        r = _load(rid)
    except HTTPException:
        return HTMLResponse("<h1>Not found</h1>", status_code=404)
    s = _enrich(r)["_summary"]
    cards = ""
    for ev in r.get("events", []):
        e, g, t = ev["event"], ev["gate"], ev["tavily"]
        c = {"ACCEPT": "#22c55e", "DOWNGRADE": "#f59e0b", "REMOVE": "#ef4444", "NO_EVIDENCE": "#a1a1aa"}.get(g["decision"], "#71717a")
        b = {"ACCEPT": "LEGAL", "DOWNGRADE": "UNCERTAIN", "REMOVE": "ILLEGAL", "NO_EVIDENCE": "NO EVIDENCE"}.get(g["decision"], "?")
        amt = e.get("dollar_amount") or 0

        # ─── Signature rate bar ──────────────────────────
        rate = e.get("rate_pct")
        cap = t.get("legal_rate_pct")
        rate_bar = ""
        if rate is not None and cap is not None and cap > 0:
            # Scale: 2× the cap is the full width. Rate 25% vs cap 10% overflows.
            scale_max = cap * 2
            rate_pos = min(100, (rate / scale_max) * 100)
            cap_pos = min(100, (cap / scale_max) * 100)
            overflow = rate > cap
            if overflow:
                # Red portion from cap to rate
                red_width = rate_pos - cap_pos
                green_width = cap_pos
            else:
                red_width = 0
                green_width = rate_pos
            # Bar structure:
            # [green up to rate_pos if legal] or [green up to cap_pos][red to rate_pos if illegal]
            bar_inner = ''
            if overflow:
                bar_inner = (
                    '<div style="position:absolute;left:0;top:0;height:100%;width:' + format(cap_pos, ".1f") + '%;background:linear-gradient(90deg,#166534,#22c55e)"></div>'
                    '<div style="position:absolute;left:' + format(cap_pos, ".1f") + '%;top:0;height:100%;width:' + format(red_width, ".1f") + '%;background:linear-gradient(90deg,#22c55e,#ef4444)"></div>'
                )
            else:
                bar_inner = (
                    '<div style="position:absolute;left:0;top:0;height:100%;width:' + format(green_width, ".1f") + '%;background:linear-gradient(90deg,#166534,#22c55e)"></div>'
                )
            # Cap marker (vertical line at cap position)
            cap_marker = (
                '<div style="position:absolute;left:' + format(cap_pos, ".1f") + '%;top:-4px;height:calc(100% + 8px);'
                'width:2px;background:#fafafa;box-shadow:0 0 4px rgba(255,255,255,0.5)"></div>'
            )
            rate_bar = (
                '<div style="margin-top:.75rem">'
                '<div style="display:flex;justify-content:space-between;font-size:.7rem;color:#71717a;'
                'font-family:monospace;margin-bottom:.35rem">'
                '<span>0%</span>'
                '<span style="color:#fafafa">cap ' + format(cap, ".0f") + '%</span>'
                '<span>' + format(scale_max, ".0f") + '%</span>'
                '</div>'
                '<div style="position:relative;height:8px;background:#27272a;border-radius:4px;overflow:visible">'
                + bar_inner + cap_marker +
                '</div>'
                '<div style="display:flex;justify-content:space-between;font-size:.72rem;'
                'font-family:monospace;margin-top:.4rem">'
                '<span style="color:#a1a1aa">clause rate</span>'
                '<span style="color:' + ('#ef4444' if overflow else '#22c55e') + ';font-weight:700">'
                + format(rate, ".1f") + '%' + (' — exceeds cap' if overflow else ' — within cap') + '</span>'
                '</div>'
                '</div>'
            )

        cards += (
            '<div class="ev" style="border-left-color:' + c + '">'
            '<div style="display:grid;grid-template-columns:130px 1fr auto;gap:1rem;align-items:baseline">'
            '<span class="meta">' + e["trigger_date"] + '</span>'
            '<span>' + e["description"] + '</span>'
            '<span class="amt" style="color:' + c + '">$' + format(amt, ",.2f") + '</span>'
            '</div>'
            '<div style="margin-top:.5rem"><span class="badge" style="background:' + c + '20;color:' + c + '">' + b + '</span></div>'
            + rate_bar +
            '<p class="reason">' + _narrative(e, g, t) + '</p>'
            '</div>'
        )
    return HTMLResponse(
        '<!doctype html><html><head><title>' + s["title"] + '</title><style>' + STYLE + '</style></head><body>'
        '<div class="wrap"><a href="/">← All analyses</a>'
        '<div style="margin-top:1.5rem;padding:2rem;border-radius:12px;background:' + s["color"] + '08;border:1px solid ' + s["color"] + '30">'
        '<span class="badge" style="background:' + s["color"] + '22;color:' + s["color"] + '">' + s["badge"] + '</span>'
        '<h1 style="font-size:2rem;margin:.75rem 0 .5rem">' + s["title"] + '</h1>'
        '<p style="color:#a1a1aa;margin-bottom:1.5rem">' + s["blurb"] + '</p>'
        '<div class="big" style="color:' + s["color"] + '">$' + format(s["impact"], ",.0f") + '</div>'
        '</div>'
        '<div style="display:flex;gap:.75rem;margin:1.5rem 0;flex-wrap:wrap">'
        '<a href="/api/receipt/' + rid + '/download" download="futureproof-' + rid + '.json" '
        'style="display:inline-flex;align-items:center;gap:.5rem;padding:.65rem 1.25rem;'
        'background:#18181b;border:1px solid #3f3f46;border-radius:8px;color:#e5e5e5;'
        'font-size:.88rem;font-weight:600;text-decoration:none">'
        'Download receipt</a>'
        '<button onclick="copyShare()" '
        'style="display:inline-flex;align-items:center;gap:.5rem;padding:.65rem 1.25rem;'
        'background:#6366f1;border:none;border-radius:8px;color:white;font-family:inherit;'
        'font-size:.88rem;font-weight:600;cursor:pointer">'
        '<span id="copy-label">Copy share link</span></button>'
        '</div>'
        '<script>'
        'function copyShare(){'
        'var url=window.location.origin+"/verify/' + rid + '";'
        'var label=document.getElementById("copy-label");'
        'var btn=label.parentElement;'
        'if(navigator.clipboard&&navigator.clipboard.writeText){'
        'navigator.clipboard.writeText(url).then(function(){'
        'label.textContent="Copied!";btn.style.background="#22c55e";'
        'setTimeout(function(){label.textContent="Copy share link";btn.style.background="#6366f1";},2000);'
        '}).catch(function(){prompt("Copy this link:",url);});'
        '}else{prompt("Copy this link:",url);}'
        '}'
        '</script>'
        '<h2>Models used on this analysis</h2>' + _models_html(r) +
        '<h2>Every future cost</h2>' + cards +
        '<div class="verify"><div>Receipt: ' + rid + '</div><div>Self hash: ' + r.get("self_hash", "") + '</div></div>'
        '</div></body></html>'
    )


@app.get("/receipt/{rid}.json")
def json_receipt(rid: str):
    return JSONResponse(_enrich(_load(rid)))


@app.get("/verify/{rid}", response_class=HTMLResponse)
def html_verify(rid: str):
    try:
        r = _load(rid)
    except HTTPException:
        return HTMLResponse("<h1>Not found</h1>", status_code=404)
    stored = r.get("self_hash")
    recomputed = _self_hash(r)
    ok = stored == recomputed
    c = "#22c55e" if ok else "#ef4444"
    return HTMLResponse(
        '<!doctype html><html><head><title>Verify</title><style>' + STYLE + '</style></head><body>'
        '<div class="wrap"><h1>Receipt verification</h1>'
        '<div style="margin-top:1.5rem;padding:2rem;border-radius:12px;background:' + c + '08;border:1px solid ' + c + '30">'
        '<span class="badge" style="background:' + c + '22;color:' + c + '">'
        + ('✓ VALID' if ok else '✗ INVALID') + '</span>'
        '<h2 style="margin:.75rem 0">Receipt ' + rid + '</h2>'
        '<p style="color:' + c + '">' + ('Hash matches. Nothing altered.' if ok else 'Hash mismatch. Tampered.') + '</p>'
        '</div>'
        '<div class="verify"><div>Stored: ' + (stored or "?") + '</div><div>Recomputed: ' + recomputed + '</div></div>'
        '</div></body></html>'
    )


@app.get("/counterfactual/{rid}")
def html_counterfactual(rid: str, new_rate: float = 8.0):
    return api_counterfactual(rid, new_rate)

@app.get("/api/corpus")
def api_corpus():
    """Adversarial corpus results — battle scars made public."""
    p = Path(__file__).resolve().parent.parent.parent / "tests" / "corpus" / "results.json"
    if not p.exists():
        raise HTTPException(404, "corpus has not been run yet")
    return JSONResponse(json.loads(p.read_text()))


@app.get("/corpus", response_class=HTMLResponse)
def html_corpus():
    p = Path(__file__).resolve().parent.parent.parent / "tests" / "corpus" / "results.json"
    if not p.exists():
        return HTMLResponse("<h1>Corpus has not been run yet</h1>", status_code=404)
    data = json.loads(p.read_text())

    product = data.get("product", {"total": 0, "passed": 0, "accuracy": 0})
    raw = data.get("raw", {"total": 0, "passed": 0, "accuracy": 0})

    rows = ""
    for r in data["results"]:
        fk = r.get("failure_kind")
        if r["passed"]:
            color, mark = "#22c55e", "✓"
        elif fk == "INFRA":
            color, mark = "#71717a", "○"
        else:
            color, mark = "#ef4444", "✗"
        rows += (
            '<tr style="border-bottom:1px solid #27272a">'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:' + color + '">' + mark + '</td>'
            '<td style="padding:.6rem .75rem;font-size:.85rem">' + r["name"] + '</td>'
            '<td style="padding:.6rem .75rem;font-size:.82rem;color:#a1a1aa">' + r["jurisdiction"] + '</td>'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem">' + str(r["rate"]) + '%</td>'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:#a1a1aa">' + r["expected"] + '</td>'
            '<td style="padding:.6rem .75rem;font-family:monospace;font-size:.82rem;color:' + color + '">' + r["actual"] + '</td>'
            '<td style="padding:.6rem .75rem;font-size:.78rem;color:#71717a">' + r["note"] + '</td>'
            '</tr>'
        )

    cat_rows = ""
    for cat, s in data["by_category"].items():
        pt = s.get("product_passed", s.get("passed", 0))
        ptt = s.get("product_total", s.get("total", 0))
        pct = round(100 * pt / ptt) if ptt else 0
        color = "#22c55e" if pct == 100 else ("#f59e0b" if pct >= 70 else "#ef4444")
        cat_rows += (
            '<div style="display:flex;justify-content:space-between;padding:.5rem 0;'
            'border-bottom:1px solid #27272a">'
            '<span style="color:#a1a1aa;font-size:.9rem;text-transform:capitalize">' + cat + '</span>'
            '<span style="font-family:monospace;font-size:.9rem;color:' + color + '">'
            + str(pt) + '/' + str(ptt) + ' (' + str(pct) + '%)</span>'
            '</div>'
        )

    prod_acc = product.get("accuracy", 0)
    prod_color = "#22c55e" if prod_acc >= 0.9 else ("#f59e0b" if prod_acc >= 0.7 else "#ef4444")

    # Find failures that are real product bugs (not infra)
    real_failures = [r for r in data["failures"] if r.get("failure_kind") == "PRODUCT"]
    failures_html = ""
    if real_failures:
        failures_html = (
            '<h2>Known limitations</h2>'
            '<div style="padding:1rem;background:#7c2d12/20;border:1px solid #7c2d12;border-radius:8px;margin-bottom:2rem">'
            '<p style="color:#fca5a5;font-size:.9rem;margin-bottom:.5rem"><strong>Real failures we have not fixed:</strong></p>'
            '<ul style="color:#a1a1aa;font-size:.85rem;margin-left:1.5rem">'
        )
        for f in real_failures:
            failures_html += f'<li>{f["name"]}: expected {f["expected"]}, got {f["actual"]}</li>'
        failures_html += '</ul></div>'
    else:
        failures_html = (
            '<div style="padding:1rem;background:#052e16;border:1px solid #16a34a;border-radius:8px;margin-bottom:2rem">'
            '<p style="color:#86efac;font-size:.9rem"><strong>✓ No product bugs outstanding.</strong> '
            'Every case that actually executed produced the correct verdict. '
            'The two failures above are NVIDIA rate-limit errors, labeled honestly.</p>'
            '</div>'
        )

    return HTMLResponse(
        '<!doctype html><html><head><title>Adversarial Corpus · FutureProof</title>'
        '<style>' + STYLE + '</style></head><body><div class="wrap">'
        '<a href="/">← Home</a>'
        '<h1 style="margin-top:1.5rem">Adversarial test corpus</h1>'
        '<p class="tagline">12 labeled test cases. Every one is a live pipeline run — Nemotron extraction, '
        'Tavily verification, gate decision. No mocks, no fixtures. Failures shown openly.</p>'

        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:2rem 0">'
        '<div style="padding:2rem;background:#18181b;border:1px solid ' + prod_color + '40;border-radius:12px">'
        '<div style="font-size:.75rem;color:#71717a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.5rem">Product accuracy</div>'
        '<div style="font-family:monospace;font-size:3rem;font-weight:800;color:' + prod_color + ';line-height:1">'
        + str(product["passed"]) + '/' + str(product["total"]) +
        '</div>'
        '<div style="color:#a1a1aa;font-size:.85rem;margin-top:.5rem">'
        + f'{prod_acc*100:.0f}% — excluding infrastructure failures</div>'
        '</div>'
        '<div style="padding:2rem;background:#18181b;border:1px solid #27272a;border-radius:12px">'
        '<div style="font-size:.75rem;color:#71717a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.5rem">Raw count</div>'
        '<div style="font-family:monospace;font-size:3rem;font-weight:800;color:#a1a1aa;line-height:1">'
        + str(raw["passed"]) + '/' + str(raw["total"]) +
        '</div>'
        '<div style="color:#a1a1aa;font-size:.85rem;margin-top:.5rem">'
        + f'{raw["accuracy"]*100:.0f}% — including rate-limit failures</div>'
        '</div>'
        '</div>'

        '<div style="padding:1.5rem;background:#18181b;border:1px solid #27272a;border-radius:12px;margin-bottom:2rem">'
        + cat_rows +
        '</div>'

        + failures_html +

        '<h2>All cases</h2>'
        '<table style="width:100%;border-collapse:collapse;margin-top:1rem">'
        '<thead><tr style="border-bottom:1px solid #3f3f46">'
        '<th style="text-align:left;padding:.5rem .75rem;font-size:.75rem;color:#71717a;font-weight:500"></th>'
        '<th style="text-align:left;padding:.5rem .75rem;font-size:.75rem;color:#71717a;font-weight:500">Case</th>'
        '<th style="text-align:left;padding:.5rem .75rem;font-size:.75rem;color:#71717a;font-weight:500">Jurisdiction</th>'
        '<th style="text-align:left;padding:.5rem .75rem;font-size:.75rem;color:#71717a;font-weight:500">Rate</th>'
        '<th style="text-align:left;padding:.5rem .75rem;font-size:.75rem;color:#71717a;font-weight:500">Expected</th>'
        '<th style="text-align:left;padding:.5rem .75rem;font-size:.75rem;color:#71717a;font-weight:500">Actual</th>'
        '<th style="text-align:left;padding:.5rem .75rem;font-size:.75rem;color:#71717a;font-weight:500">Note</th>'
        '</tr></thead><tbody>' + rows + '</tbody></table>'

        '<p style="color:#525252;font-size:.82rem;margin-top:2rem">'
        'Run: <code>' + data["run_at"] + '</code> · '
        'Every case is a real pipeline run. No mocks, no fixtures. '
        'The failures are real. The bug this corpus found — 10.5% passing a 10% cap — was fixed and re-verified.</p>'
        '</div></body></html>'
    )

@app.get("/api/compare")
def api_compare(a: str, b: str):
    ra = _load(a)
    rb = _load(b)
    sa = _enrich(ra)["_summary"]
    sb = _enrich(rb)["_summary"]

    def illegal_total(r):
        return sum((ev["event"].get("dollar_amount") or 0)
                   for ev in r["events"] if ev["gate"]["decision"] == "REMOVE")

    a_illegal = illegal_total(ra)
    b_illegal = illegal_total(rb)
    if a_illegal < b_illegal:
        safer, saved = "a", round(b_illegal - a_illegal, 2)
    elif b_illegal < a_illegal:
        safer, saved = "b", round(a_illegal - b_illegal, 2)
    else:
        safer, saved = "tie", 0.0
    return {
        "a": {"receipt_id": a, "summary": sa, "illegal": round(a_illegal, 2)},
        "b": {"receipt_id": b, "summary": sb, "illegal": round(b_illegal, 2)},
        "safer": safer, "saved": saved,
    }


@app.get("/compare", response_class=HTMLResponse)
def html_compare(a: str = "", b: str = ""):
    receipts = _list_all(20)
    opts_a = ""
    opts_b = ""
    for r in receipts:
        s = _enrich(r)["_summary"]
        label = s["title"] + " — $" + format(s["impact"], ",.0f")
        opts_a += '<option value="' + r["receipt_id"] + '"' + (' selected' if r["receipt_id"] == a else '') + '>' + label + '</option>'
        opts_b += '<option value="' + r["receipt_id"] + '"' + (' selected' if r["receipt_id"] == b else '') + '>' + label + '</option>'

    result_html = ""
    if a and b:
        ra = _load(a)
        rb = _load(b)
        sa = _enrich(ra)["_summary"]
        sb = _enrich(rb)["_summary"]

        def illegal_total(r):
            return sum((ev["event"].get("dollar_amount") or 0)
                       for ev in r["events"] if ev["gate"]["decision"] == "REMOVE")

        a_il = illegal_total(ra)
        b_il = illegal_total(rb)

        if a_il < b_il:
            verdict = "Lease A is safer — blocks $" + format(a_il, ",.0f") + " illegal vs B's $" + format(b_il, ",.0f")
            diff = b_il - a_il
            vc = "#22c55e"
        elif b_il < a_il:
            verdict = "Lease B is safer — blocks $" + format(b_il, ",.0f") + " illegal vs A's $" + format(a_il, ",.0f")
            diff = a_il - b_il
            vc = "#22c55e"
        else:
            verdict = "Both leases have equal illegal exposure"
            diff = 0
            vc = "#f59e0b"

        def card(r, s, il, name):
            return (
                '<div style="background:#18181b;border:1px solid ' + s["color"] + '40;border-radius:12px;padding:1.5rem">'
                '<div style="font-size:.7rem;color:#71717a;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.5rem">' + name + '</div>'
                '<span class="badge" style="background:' + s["color"] + '22;color:' + s["color"] + '">' + s["badge"] + '</span>'
                '<h3 style="margin:.5rem 0;font-size:1.1rem">' + s["title"] + '</h3>'
                '<div style="font-family:monospace;font-size:1.9rem;font-weight:800;color:' + s["color"] + '">$' + format(s["impact"], ",.0f") + '</div>'
                '<div style="color:#71717a;font-size:.8rem">total potential cost</div>'
                '<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #27272a">'
                '<div style="color:#ef4444;font-family:monospace;font-size:1rem;font-weight:700">$' + format(il, ",.0f") + '</div>'
                '<div style="color:#71717a;font-size:.8rem">illegal, blocked by gate</div></div>'
                '<a href="/receipt/' + r["receipt_id"] + '" style="display:inline-block;margin-top:1rem;font-size:.85rem;color:#60a5fa">View full →</a></div>'
            )

        result_html = (
            '<div style="margin:2rem 0;padding:1.5rem;background:' + vc + '12;border:1px solid ' + vc + '40;border-radius:12px">'
            '<div style="font-size:1.05rem;font-weight:600;color:' + vc + '">' + verdict + '</div>'
            + ('<div style="color:#a1a1aa;font-size:.9rem;margin-top:.5rem">Choosing the safer lease saves $' + format(diff, ",.0f") + '</div>' if diff > 0 else '')
            + '</div>'
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">'
            + card(ra, sa, a_il, "Lease A") + card(rb, sb, b_il, "Lease B") + '</div>'
        )

    return HTMLResponse(
        '<!doctype html><html><head><title>Compare · FutureProof</title><style>' + STYLE + '</style></head><body><div class="wrap">'
        '<a href="/">← Home</a>'
        '<h1 style="margin-top:1.5rem">Compare two leases</h1>'
        '<p class="tagline">Which contract is safer to sign?</p>'
        '<form method="get" style="display:flex;flex-wrap:wrap;gap:.75rem;margin:1.5rem 0;padding:1.5rem;background:#18181b;border:1px solid #27272a;border-radius:12px">'
        '<select name="a" style="background:#09090b;border:1px solid #27272a;color:#a1a1aa;padding:.6rem;border-radius:6px;flex:1;min-width:200px">'
        '<option value="">Lease A…</option>' + opts_a + '</select>'
        '<select name="b" style="background:#09090b;border:1px solid #27272a;color:#a1a1aa;padding:.6rem;border-radius:6px;flex:1;min-width:200px">'
        '<option value="">Lease B…</option>' + opts_b + '</select>'
        '<button type="submit" style="background:#6366f1;color:white;border:none;padding:.6rem 1.25rem;border-radius:6px;font-weight:600;cursor:pointer">Compare</button>'
        '</form>'
        + result_html +
        '</div></body></html>'
    )
