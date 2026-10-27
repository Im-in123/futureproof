import type { Receipt, CounterfactualResult, VerifyResult, CorpusResult } from './types'

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(await r.text() || r.statusText)
  return r.json()
}

export const api = {
  receipts: (limit = 20) =>
    fetch(`/api/receipts?limit=${limit}`).then(r => j<{ receipts: Receipt[] }>(r)),
  receipt: (id: string) => fetch(`/api/receipt/${id}`).then(r => j<Receipt>(r)),
  verify: (id: string) => fetch(`/api/verify/${id}`).then(r => j<VerifyResult>(r)),
  counterfactual: (id: string, rate: number) =>
    fetch(`/api/counterfactual/${id}?new_rate=${rate}`).then(r => j<CounterfactualResult>(r)),
  corpus: () => fetch('/api/corpus').then(r => j<CorpusResult>(r)),
  upload: (file: File, jurisdiction: string, baseRent: number) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('jurisdiction', jurisdiction)
    fd.append('base_rent', String(baseRent))
    return fetch('/api/upload', { method: 'POST', body: fd })
      .then(r => j<{ receipt_id: string }>(r))
  },
}
