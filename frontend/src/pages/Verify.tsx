import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import type { VerifyResult } from '../types'

export function Verify() {
  const { id } = useParams<{ id: string }>()
  const [v, setV] = useState<VerifyResult | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    api.verify(id).then(setV).catch(e => setErr(String(e)))
  }, [id])

  if (err) return <p className="text-red-400">{err}</p>
  if (!v) return <p className="text-zinc-500">Verifying…</p>

  const c = v.valid ? '#22c55e' : '#ef4444'

  return (
    <div>
      <Link to="/" className="text-sm text-zinc-500 hover:text-zinc-100 inline-block mb-6">← All analyses</Link>
      <h1 className="text-3xl font-extrabold tracking-tight mb-2">Receipt verification</h1>
      <p className="text-zinc-400 mb-8">Any third party can verify this analysis without trusting the app.</p>

      <div className="rounded-xl p-8 border" style={{ background: `${c}12`, borderColor: `${c}40` }}>
        <span className="inline-block px-2.5 py-1 rounded text-[10px] font-bold tracking-wider font-mono"
          style={{ background: `${c}22`, color: c }}>
          {v.valid ? '✓ VALID' : '✗ INVALID'}
        </span>
        <h2 className="text-xl font-bold mt-3 mb-2">Receipt {v.receipt_id}</h2>
        <p style={{ color: c }}>
          {v.valid ? 'The cryptographic hash of this receipt matches its contents. Nothing has been altered.'
                   : 'The hash does not match. This receipt has been tampered with.'}
        </p>
      </div>

      <div className="mt-6 rounded-lg border border-zinc-800 bg-zinc-900/40 p-5 font-mono text-xs text-zinc-500 space-y-1 break-all">
        <p>Stored: {v.stored_hash}</p>
        <p>Recomputed: {v.recomputed_hash}</p>
      </div>
    </div>
  )
}
