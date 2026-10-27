import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import type { Receipt } from '../types'
import { Badge } from '../components/Badge'
import { UploadForm } from '../components/UploadForm'

export function Home() {
  const [receipts, setReceipts] = useState<Receipt[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.receipts(20).then(r => setReceipts(r.receipts)).finally(() => setLoading(false))
  }, [])

  let hero: Receipt | null = null
  for (const r of receipts) if (r._summary.counts.REMOVE > 0) { hero = r; break }
  if (!hero) for (const r of receipts) if (r._summary.counts.NO_EVIDENCE > 0) { hero = r; break }
  if (!hero && receipts.length) hero = receipts[0]

  const others = receipts.filter(r => r.receipt_id !== hero?.receipt_id).slice(0, 5)

  let heroStory: string = ''
  if (hero) {
    const s = hero._summary
    if (s.counts.REMOVE > 0) {
      const topEv = hero.events.find(e => e.gate.decision === 'REMOVE' && e.event.rate_pct)
      const rate = topEv?.event.rate_pct?.toFixed(0) || '18'
      const cap = topEv?.tavily.legal_rate_pct?.toFixed(0) || '10'
      heroStory = `A California sublease proposed an ${rate}% annual rent increase. California caps it at ${cap}%. FutureProof blocked all ${s.counts.REMOVE} events — saving the tenant $${s.impact.toLocaleString(undefined, { maximumFractionDigits: 0 })}.`
    } else if (s.counts.NO_EVIDENCE > 0) {
      heroStory = `This contract contained clauses we could not verify against any reliable legal source. Rather than guess, FutureProof says "We cannot determine" — because a tool that tells you it doesn't know is more trustworthy than one that pretends it does.`
    } else {
      heroStory = s.blurb
    }
  }

  return (
    <div>
      <div className="mb-10">
        <h1 className="text-4xl font-extrabold tracking-tight mb-2">FutureProof</h1>
        <p className="text-zinc-400 text-lg mb-2">See every hidden cost in a contract — before you sign it.</p>
        <p className="text-zinc-500 text-sm">Built for Sarah, 26, signing her first LA apartment lease. She doesn't have a lawyer. She has a browser.</p>
      </div>

      {hero && (
        <div className="mb-10 p-8 rounded-2xl border"
          style={{ background: `linear-gradient(135deg, ${hero._summary.color}12, ${hero._summary.color}04)`, borderColor: `${hero._summary.color}40` }}>
          <Badge label={hero._summary.badge} color={hero._summary.color} />
          <h2 className="text-2xl font-extrabold mt-3 mb-3 text-zinc-100">{hero._summary.title}</h2>
          <p className="text-zinc-300 text-base mb-5">{heroStory}</p>
          <div className="flex items-baseline gap-3 mb-5 flex-wrap">
            <span className="font-mono text-5xl font-extrabold leading-none" style={{ color: hero._summary.color }}>
              ${hero._summary.impact.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </span>
            <span className="text-zinc-500 text-sm">total potential cost surfaced</span>
          </div>
          <Link to={`/receipt/${hero.receipt_id}`}
            className="inline-block px-5 py-2.5 rounded-lg font-semibold text-sm text-zinc-950"
            style={{ background: hero._summary.color }}>
            See the full analysis →
          </Link>
        </div>
      )}

      <div className="mb-10"><UploadForm /></div>

      {others.length > 0 && (
        <>
          <h2 className="text-lg font-semibold text-zinc-300 mb-4">More analyses</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {others.map(r => {
              const s = r._summary
              return (
                <Link key={r.receipt_id} to={`/receipt/${r.receipt_id}`}
                  className="rounded-xl border bg-zinc-900/60 p-5 transition-all hover:bg-zinc-900 hover:-translate-y-0.5"
                  style={{ borderColor: `${s.color}30` }}>
                  <Badge label={s.badge} color={s.color} />
                  <h3 className="text-base font-bold mt-2">{s.title}</h3>
                  <div className="font-mono text-2xl font-bold mt-3">${s.impact.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                </Link>
              )
            })}
          </div>
        </>
      )}

      <p className="mt-16 text-center text-xs text-zinc-600">
        Every analysis runs Nemotron on Nebius Token Factory, verifies against Tavily, and produces a hash-chained receipt you can prove to a third party.
      </p>
    </div>
  )
}
