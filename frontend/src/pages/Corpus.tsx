import { useEffect, useState } from 'react'
import { api } from '../api'
import type { CorpusResult } from '../types'

export function Corpus() {
  const [c, setC] = useState<CorpusResult | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => { api.corpus().then(setC).catch(e => setErr(String(e))) }, [])

  if (err) return <p className="text-red-400">{err}</p>
  if (!c) return <p className="text-zinc-500">Loading…</p>

  const prodPct = Math.round(c.product.accuracy * 100)
  const rawPct = Math.round(c.raw.accuracy * 100)
  const prodColor = prodPct >= 90 ? '#22c55e' : (prodPct >= 70 ? '#f59e0b' : '#ef4444')

  return (
    <div>
      <h1 className="text-3xl font-extrabold tracking-tight mb-2">Adversarial test corpus</h1>
      <p className="text-zinc-400 mb-6">
        12 labeled test cases. Every one is a live pipeline run — Nemotron extraction, Tavily verification, gate decision. Failures shown openly.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <div className="p-6 rounded-xl border" style={{ borderColor: `${prodColor}40`, background: '#18181b' }}>
          <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">Product accuracy</div>
          <div className="font-mono text-4xl font-extrabold leading-none" style={{ color: prodColor }}>
            {c.product.passed}/{c.product.total}
          </div>
          <div className="text-sm text-zinc-400 mt-2">{prodPct}% — excluding infrastructure failures</div>
        </div>
        <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900">
          <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">Raw count</div>
          <div className="font-mono text-4xl font-extrabold leading-none text-zinc-400">
            {c.raw.passed}/{c.raw.total}
          </div>
          <div className="text-sm text-zinc-400 mt-2">{rawPct}% — including rate-limit failures</div>
        </div>
      </div>

      <div className="p-5 bg-zinc-900 border border-zinc-800 rounded-xl mb-8">
        {Object.entries(c.by_category).map(([cat, s]) => {
          const pct = s.product_total ? Math.round(100 * s.product_passed / s.product_total) : 0
          const color = pct === 100 ? '#22c55e' : (pct >= 70 ? '#f59e0b' : '#ef4444')
          return (
            <div key={cat} className="flex justify-between py-2 border-b border-zinc-800 last:border-b-0">
              <span className="text-sm text-zinc-400 capitalize">{cat}</span>
              <span className="font-mono text-sm" style={{ color }}>{s.product_passed}/{s.product_total} ({pct}%)</span>
            </div>
          )
        })}
      </div>

      <h2 className="text-lg font-semibold text-zinc-300 mb-4">All cases</h2>
      <div className="rounded-lg border border-zinc-800 overflow-hidden overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-zinc-950">
            <tr className="border-b border-zinc-700">
              <th className="text-left py-2.5 px-3 text-[10px] text-zinc-500 uppercase"></th>
              <th className="text-left py-2.5 px-3 text-[10px] text-zinc-500 uppercase">Case</th>
              <th className="text-left py-2.5 px-3 text-[10px] text-zinc-500 uppercase">Jurisdiction</th>
              <th className="text-left py-2.5 px-3 text-[10px] text-zinc-500 uppercase">Rate</th>
              <th className="text-left py-2.5 px-3 text-[10px] text-zinc-500 uppercase">Expected</th>
              <th className="text-left py-2.5 px-3 text-[10px] text-zinc-500 uppercase">Actual</th>
              <th className="text-left py-2.5 px-3 text-[10px] text-zinc-500 uppercase">Note</th>
            </tr>
          </thead>
          <tbody>
            {c.results.map(r => {
              const color = r.passed ? '#22c55e' : (r.failure_kind === 'INFRA' ? '#71717a' : '#ef4444')
              const mark = r.passed ? '✓' : (r.failure_kind === 'INFRA' ? '○' : '✗')
              return (
                <tr key={r.name} className="border-b border-zinc-800">
                  <td className="py-2 px-3 font-mono text-xs" style={{ color }}>{mark}</td>
                  <td className="py-2 px-3 text-sm text-zinc-200">{r.name}</td>
                  <td className="py-2 px-3 text-xs text-zinc-400">{r.jurisdiction}</td>
                  <td className="py-2 px-3 font-mono text-xs">{r.rate}%</td>
                  <td className="py-2 px-3 font-mono text-xs text-zinc-400">{r.expected}</td>
                  <td className="py-2 px-3 font-mono text-xs" style={{ color }}>{r.actual}</td>
                  <td className="py-2 px-3 text-xs text-zinc-500">{r.note}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-6 text-xs text-zinc-600">
        Run: {new Date(c.run_at).toLocaleString()} · Every case is a real pipeline run. No mocks, no fixtures.
      </p>
    </div>
  )
}
