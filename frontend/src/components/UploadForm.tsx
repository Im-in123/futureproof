import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

const STAGES: Array<[number, string]> = [
  [0, 'Reading document…'],
  [10, 'Extracting clauses…'],
  [25, 'Computing consequences…'],
  [60, 'Verifying statutory sources…'],
  [90, 'Applying gate…'],
  [97, 'Emitting receipt…'],
]

export function UploadForm() {
  const [file, setFile] = useState<File | null>(null)
  const [jurisdiction, setJurisdiction] = useState('California')
  const [baseRent, setBaseRent] = useState('')
  const [busy, setBusy] = useState(false)
  const [stage, setStage] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    setBusy(true); setError(null); setStage(STAGES[0][1])
    const start = Date.now()
    const timer = setInterval(() => {
      const sec = (Date.now() - start) / 1000
      setElapsed(Math.floor(sec))
      const pct = Math.min(97, sec * 1.2)
      let label = STAGES[0][1]
      for (const [t, l] of STAGES) if (pct >= t) label = l
      setStage(label)
    }, 400)

    try {
      const res = await api.upload(file, jurisdiction, parseFloat(baseRent) || 0)
      clearInterval(timer)
      navigate(`/receipt/${res.receipt_id}`)
    } catch (err) {
      clearInterval(timer)
      setError(String(err)); setBusy(false)
    }
  }

  return (
    <div className="rounded-xl border border-indigo-500/30 bg-gradient-to-b from-indigo-500/[0.06] to-transparent p-6">
      <h2 className="text-xl font-semibold mb-1">Analyze your own contract</h2>
      <p className="text-sm text-zinc-400 mb-4">
        Upload a lease, employment offer, or insurance policy. Processing takes 1–3 minutes.
      </p>
      <form onSubmit={onSubmit} className="flex flex-wrap gap-3 items-center">
        <input type="file" accept=".pdf,.txt,.md"
          onChange={e => setFile(e.target.files?.[0] || null)}
          required disabled={busy}
          className="text-sm text-zinc-300 file:mr-3 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-zinc-800 file:text-zinc-100 file:font-medium hover:file:bg-zinc-700" />
        <select value={jurisdiction} onChange={e => setJurisdiction(e.target.value)} disabled={busy}
          className="bg-zinc-900 border border-zinc-800 text-zinc-100 px-4 py-2 rounded-md text-sm">
          <option>California</option><option>New York</option><option>Oregon</option>
          <option>Washington</option><option>Massachusetts</option><option>Colorado</option>
          <option>Illinois</option><option>New Jersey</option><option>Maryland</option>
          <option>Minnesota</option>
        </select>
        <input type="number" placeholder="Base rent (optional)" value={baseRent}
          onChange={e => setBaseRent(e.target.value)} disabled={busy}
          className="bg-zinc-900 border border-zinc-800 text-zinc-100 px-4 py-2 rounded-md text-sm w-44" />
        <button type="submit" disabled={!file || busy}
          className="bg-indigo-500 hover:bg-indigo-400 disabled:bg-zinc-700 disabled:text-zinc-500 text-white font-semibold px-5 py-2 rounded-md text-sm">
          {busy ? 'Analyzing…' : 'Analyze contract'}
        </button>
      </form>
      {busy && (
        <div className="mt-4">
          <div className="h-1 bg-zinc-800 rounded overflow-hidden">
            <div className="h-full bg-indigo-500 transition-all duration-300"
              style={{ width: `${Math.min(97, elapsed * 1.2)}%` }} />
          </div>
          <div className="flex justify-between text-xs text-zinc-400 mt-2">
            <span>{stage}</span>
            <span className="font-mono">{elapsed}s</span>
          </div>
        </div>
      )}
      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
    </div>
  )
}
