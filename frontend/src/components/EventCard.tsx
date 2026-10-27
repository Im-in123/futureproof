import type { ReceiptEvent } from '../types'
import { RateBar } from './RateBar'

function getStyle(ev: ReceiptEvent): { color: string; label: string } {
  const d = ev.gate.decision
  if (d === 'ACCEPT' && ev.event.rate_pct === null) {
    return { color: '#38bdf8', label: 'LEGAL FEE' }
  }
  if (d === 'ACCEPT') return { color: '#22c55e', label: 'LEGAL' }
  if (d === 'DOWNGRADE') return { color: '#f59e0b', label: 'UNCERTAIN' }
  if (d === 'REMOVE') return { color: '#ef4444', label: 'ILLEGAL' }
  return { color: '#a1a1aa', label: 'NO EVIDENCE' }
}

function narrative(ev: ReceiptEvent): string {
  const { event: e, gate: g, tavily: t } = ev
  if (g.decision === 'NO_EVIDENCE')
    return "We couldn't find a reliable legal source for this clause. We cannot determine whether it is enforceable. Consult a lawyer before signing."
  if (g.rules_fired.includes('R6') && e.rate_pct && t.legal_rate_pct)
    return `State law caps annual rent increases at ${t.legal_rate_pct.toFixed(0)}%. This ${e.rate_pct.toFixed(0)}% increase is illegal and cannot be enforced.`
  if (g.decision === 'ACCEPT' && e.rate_pct === null)
    return "This is a one-time fee, not a rent increase. It is legal under California law, but $12,000 is a lot to pay upfront. The franchise fee is disclosed in the contract — negotiate it if you can."
  if (g.decision === 'ACCEPT') return 'This clause is legal in your jurisdiction. The cost shown is real; plan for it.'
  if (g.decision === 'DOWNGRADE') return "Couldn't verify against an authoritative source. Consult a lawyer before signing."
  if (g.decision === 'REMOVE') return t.verdict === 'CONTRADICTED'
    ? 'No legal source supports this clause. It cannot be enforced.'
    : 'This clause cannot legally fire as written.'
  return g.reason
}

export function EventCard({ ev }: { ev: ReceiptEvent }) {
  const style = getStyle(ev)
  const amt = ev.event.dollar_amount
  const amtStr = amt ? `$${amt.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '—'

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-5 hover:bg-zinc-900 transition-colors"
      style={{ borderLeftWidth: 3, borderLeftColor: style.color }}>
      <div className="grid grid-cols-[130px_1fr_auto] gap-4 items-baseline">
        <span className="font-mono text-sm text-zinc-500">{ev.event.trigger_date}</span>
        <span className="text-zinc-100 font-medium leading-snug">{ev.event.description}</span>
        <span className="font-mono text-lg font-bold" style={{ color: style.color }}>{amtStr}</span>
      </div>
      <div className="mt-2">
        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold tracking-wider font-mono"
          style={{ background: `${style.color}22`, color: style.color }}>
          {style.label}
        </span>
        <span className="ml-2 text-xs text-zinc-500 font-mono">§{ev.event.clause_id}</span>
      </div>
      <RateBar rate={ev.event.rate_pct} cap={ev.tavily.legal_rate_pct} />
      <p className="mt-3 text-sm text-zinc-400 leading-relaxed">{narrative(ev)}</p>
    </div>
  )
}
