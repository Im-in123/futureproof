import { useEffect, useState } from 'react'
import { api } from '../api'
import type { Receipt } from '../types'
import { Badge } from '../components/Badge'

export function Compare() {
  const [receipts, setReceipts] = useState<Receipt[]>([])
  const [a, setA] = useState('')
  const [b, setB] = useState('')

  useEffect(() => { api.receipts(20).then(r => setReceipts(r.receipts)) }, [])

  const ra = receipts.find(r => r.receipt_id === a)
  const rb = receipts.find(r => r.receipt_id === b)

  function illegal(r: Receipt) {
    return r.events.filter(e => e.gate.decision === 'REMOVE')
      .reduce((sum, e) => sum + (e.event.dollar_amount || 0), 0)
  }

  let verdict = ''
  let vcolor = '#f59e0b'
  let diff = 0
  if (ra && rb) {
    const ai = illegal(ra), bi = illegal(rb)
    if (ai < bi) { verdict = `Lease A is safer — blocks $${ai.toLocaleString()} illegal vs B's $${bi.toLocaleString()}`; diff = bi - ai; vcolor = '#22c55e' }
    else if (bi < ai) { verdict = `Lease B is safer — blocks $${bi.toLocaleString()} illegal vs A's $${ai.toLocaleString()}`; diff = ai - bi; vcolor = '#22c55e' }
    else { verdict = 'Both leases have equal illegal exposure'; vcolor = '#f59e0b' }
  }

  return (
    <div>
      <h1 className="text-3xl font-extrabold tracking-tight mb-2">Compare two leases</h1>
      <p className="text-zinc-400 mb-6">Which contract is safer to sign?</p>

      <div className="flex flex-wrap gap-3 mb-8 p-5 bg-zinc-900 border border-zinc-800 rounded-xl">
        <select value={a} onChange={e => setA(e.target.value)}
          className="bg-zinc-950 border border-zinc-800 text-zinc-100 px-4 py-2 rounded-md text-sm flex-1 min-w-[200px]">
          <option value="">Lease A…</option>
          {receipts.map(r => <option key={r.receipt_id} value={r.receipt_id}>{r._summary.title} — ${r._summary.impact.toLocaleString(undefined, { maximumFractionDigits: 0 })}</option>)}
        </select>
        <select value={b} onChange={e => setB(e.target.value)}
          className="bg-zinc-950 border border-zinc-800 text-zinc-100 px-4 py-2 rounded-md text-sm flex-1 min-w-[200px]">
          <option value="">Lease B…</option>
          {receipts.map(r => <option key={r.receipt_id} value={r.receipt_id}>{r._summary.title} — ${r._summary.impact.toLocaleString(undefined, { maximumFractionDigits: 0 })}</option>)}
        </select>
      </div>

      {ra && rb && (
        <>
          <div className="rounded-xl p-5 mb-6" style={{ background: `${vcolor}12`, border: `1px solid ${vcolor}40` }}>
            <div className="text-lg font-semibold" style={{ color: vcolor }}>{verdict}</div>
            {diff > 0 && <div className="text-zinc-400 text-sm mt-1">Choosing the safer lease saves ${diff.toLocaleString()}</div>}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[{ r: ra, label: 'Lease A' }, { r: rb, label: 'Lease B' }].map(({ r, label }) => {
              const s = r._summary
              return (
                <div key={r.receipt_id} className="rounded-xl p-6 border" style={{ borderColor: `${s.color}40`, background: '#18181b' }}>
                  <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">{label}</div>
                  <Badge label={s.badge} color={s.color} />
                  <h3 className="text-lg font-bold mt-2 mb-3">{s.title}</h3>
                  <div className="font-mono text-3xl font-extrabold" style={{ color: s.color }}>${s.impact.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                  <div className="text-xs text-zinc-500 mt-1">total potential cost</div>
                  <div className="mt-4 pt-4 border-t border-zinc-800">
                    <div className="font-mono text-red-400 text-lg font-bold">${illegal(r).toLocaleString()}</div>
                    <div className="text-xs text-zinc-500">illegal, blocked by gate</div>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
