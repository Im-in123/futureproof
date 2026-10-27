import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import type { Receipt as R, CounterfactualResult, VerifyResult } from '../types'
import { Badge } from '../components/Badge'
import { EventCard } from '../components/EventCard'

export function Receipt() {
  const { id } = useParams<{ id: string }>()
  const [r, setR] = useState<R | null>(null)
  const [verify, setVerify] = useState<VerifyResult | null>(null)
  const [verifying, setVerifying] = useState(false)
  const [rate, setRate] = useState(8)
  const [cf, setCf] = useState<CounterfactualResult | null>(null)
  const [cfBusy, setCfBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => { if (id) api.receipt(id).then(setR).catch(console.error) }, [id])

  async function doVerify() {
    if (!id) return
    setVerifying(true)
    try { setVerify(await api.verify(id)) } finally { setVerifying(false) }
  }

  async function doCounterfactual() {
    if (!id) return
    setCfBusy(true)
    try { setCf(await api.counterfactual(id, rate)) }
    catch (e) { setCf({ summary: String(e) } as CounterfactualResult) }
    finally { setCfBusy(false) }
  }

  function copyShare() {
    const url = `${window.location.origin}/verify/${id}`
    navigator.clipboard?.writeText(url).then(() => {
      setCopied(true); setTimeout(() => setCopied(false), 2000)
    })
  }

  if (!r) return <p className="text-zinc-500">Loading…</p>
  const s = r._summary

  return (
    <div>
      <Link to="/" className="text-sm text-zinc-500 hover:text-zinc-100 inline-block mb-6">← All analyses</Link>

      <div className="rounded-2xl border p-8 mb-6"
        style={{ background: `${s.color}08`, borderColor: `${s.color}40` }}>
        <Badge label={s.badge} color={s.color} />
        <h1 className="text-3xl font-extrabold mt-3 mb-2">{s.title}</h1>
        <p className="text-zinc-300 mb-5">{s.blurb}</p>
        <div className="font-mono text-5xl font-extrabold leading-none" style={{ color: s.color }}>
          ${s.impact.toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </div>
        <p className="text-sm text-zinc-500 mt-2">total potential cost over the life of this contract</p>
      </div>

      <div className="flex flex-wrap gap-3 mb-8">
        <a href={`/api/receipt/${id}/download`} download={`futureproof-${id}.json`}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-sm font-semibold text-zinc-100 hover:bg-zinc-800">
          ⬇ Download receipt
        </a>
        <button onClick={copyShare}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-colors"
          style={{ background: copied ? '#22c55e' : '#6366f1' }}>
          {copied ? '✓ Copied!' : '🔗 Copy share link'}
        </button>
      </div>

      <h2 className="text-lg font-semibold text-zinc-300 mb-4">Every future cost</h2>
      <div className="space-y-3">
        {r.events.map(ev => <EventCard key={ev.event.event_id} ev={ev} />)}
      </div>

      {r.model_metadata.cost && (
        <>
          <h2 className="text-lg font-semibold text-zinc-300 mt-10 mb-4">Models used</h2>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-700 bg-zinc-950">
                  <th className="text-left py-2.5 px-4 text-[10px] text-zinc-500 uppercase tracking-wider">Model</th>
                  <th className="text-right py-2.5 px-4 text-[10px] text-zinc-500 uppercase tracking-wider">In</th>
                  <th className="text-right py-2.5 px-4 text-[10px] text-zinc-500 uppercase tracking-wider">Out</th>
                  <th className="text-right py-2.5 px-4 text-[10px] text-zinc-500 uppercase tracking-wider">Latency</th>
                  <th className="text-right py-2.5 px-4 text-[10px] text-zinc-500 uppercase tracking-wider">Cost</th>
                </tr>
              </thead>
              <tbody>
                {r.model_metadata.cost.model_calls.map((c, i) => (
                  <tr key={i} className="border-b border-zinc-800">
                    <td className="py-2 px-4 font-mono text-xs text-zinc-100">{c.model.split('/').pop()}</td>
                    <td className="py-2 px-4 text-right font-mono text-xs text-zinc-400">{c.in}</td>
                    <td className="py-2 px-4 text-right font-mono text-xs text-zinc-400">{c.out}</td>
                    <td className="py-2 px-4 text-right font-mono text-xs text-zinc-400">{c.latency_s ? `${c.latency_s}s` : '—'}</td>
                    <td className="py-2 px-4 text-right font-mono text-xs text-zinc-100">${c.cost_usd.toFixed(5)}</td>
                  </tr>
                ))}
                {r.model_metadata.cost.tavily_calls > 0 && (
                  <tr className="border-b border-zinc-800">
                    <td className="py-2 px-4 font-mono text-xs text-zinc-100">Tavily advanced search</td>
                    <td className="py-2 px-4 text-right text-zinc-500">—</td>
                    <td className="py-2 px-4 text-right text-zinc-500">—</td>
                    <td className="py-2 px-4 text-right text-zinc-500">—</td>
                    <td className="py-2 px-4 text-right font-mono text-xs text-zinc-100">{r.model_metadata.cost.tavily_calls} calls</td>
                  </tr>
                )}
                <tr className="border-t-2 border-zinc-700">
                  <td className="py-3 px-4 font-semibold text-zinc-100">Total</td>
                  <td></td><td></td>
                  <td className="py-3 px-4 text-right font-mono text-xs text-zinc-400">{r.model_metadata.cost.latency_seconds}s</td>
                  <td className="py-3 px-4 text-right font-mono text-sm font-bold text-zinc-100">${r.model_metadata.cost.total_cost_usd.toFixed(5)}</td>
                </tr>
              </tbody>
            </table>
            <div className="px-4 py-2.5 bg-zinc-950 text-zinc-500 text-xs">
              {r.model_metadata.cost.pricing_note}
            </div>
          </div>
        </>
      )}

      {s.counts.REMOVE > 0 && (
        <div className="mt-10 rounded-xl border border-indigo-500/30 bg-indigo-500/[0.04] p-6">
          <h2 className="text-xl font-semibold mb-1">What if you negotiated?</h2>
          <p className="text-sm text-zinc-400 mb-4">
            This contract proposes illegal rates. Try a legal rate and see the savings.
          </p>
          <div className="flex items-center gap-3 mb-4">
            <input type="number" value={rate} min={1} max={10} step={0.5}
              onChange={e => setRate(parseFloat(e.target.value) || 8)}
              className="bg-zinc-900 border border-zinc-800 text-zinc-100 px-4 py-2 rounded-md text-sm w-24 font-mono" />
            <span className="text-sm text-zinc-500">% annual increase</span>
            <button onClick={doCounterfactual} disabled={cfBusy}
              className="bg-indigo-500 hover:bg-indigo-400 disabled:bg-zinc-700 text-white font-semibold px-5 py-2 rounded-md text-sm">
              {cfBusy ? 'Simulating…' : 'Simulate'}
            </button>
          </div>
          {cf && (
            <div className="rounded-md border border-emerald-500/40 bg-emerald-500/10 text-emerald-300 p-4 font-mono text-sm space-y-1">
              <p className="font-bold mb-2 text-emerald-200">{cf.summary}</p>
              <p>Original: ${cf.original_total?.toLocaleString()}</p>
              <p>At {cf.new_rate}%: ${cf.new_total?.toLocaleString()}</p>
              <p className="font-bold">Savings: ${cf.savings?.toLocaleString()}</p>
            </div>
          )}
        </div>
      )}

      <div className="mt-10 rounded-xl border border-zinc-800 bg-zinc-900 p-6">
        <h2 className="text-xl font-semibold mb-1">Can I trust this analysis?</h2>
        <p className="text-sm text-zinc-400 mb-4">
          Every analysis produces a tamper-evident receipt. If anyone alters a single decision, the hash will not match.
        </p>
        <button onClick={doVerify} disabled={verifying}
          className="bg-indigo-500 hover:bg-indigo-400 disabled:bg-zinc-700 text-white font-semibold px-5 py-2 rounded-md text-sm">
          {verifying ? 'Verifying…' : 'Verify this receipt'}
        </button>
        {verify && (
          <div className={`mt-4 rounded-md border p-4 font-mono text-sm ${verify.valid ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' : 'border-red-500/40 bg-red-500/10 text-red-300'}`}>
            {verify.valid ? '✓ VALID — nothing has been altered.' : '✗ INVALID — receipt has been tampered with.'}
          </div>
        )}
      </div>

      <details className="mt-6 rounded-lg border border-zinc-800 bg-zinc-900/40 px-5 py-4">
        <summary className="cursor-pointer text-sm text-zinc-500 hover:text-zinc-300">Technical details</summary>
        <div className="mt-3 space-y-1 font-mono text-xs text-zinc-500 break-all">
          <p>Receipt ID: {r.receipt_id}</p>
          <p>Created: {r.created_at}</p>
          <p>Document hash: {r.document_hash}</p>
          <p>Self hash: {r.self_hash}</p>
          <p>Shareable verifier: /verify/{r.receipt_id}</p>
        </div>
      </details>
    </div>
  )
}
