export type Decision = 'ACCEPT' | 'DOWNGRADE' | 'REMOVE' | 'NO_EVIDENCE'
export type Verdict = 'VERIFIED' | 'CONTRADICTED' | 'INSUFFICIENT' | 'NO_EVIDENCE'

export interface ReceiptEvent {
  event: {
    event_id: string
    clause_id: string
    trigger_date: string
    dollar_amount: number | null
    dollar_formula: string | null
    dollar_basis: string
    rate_pct: number | null
    probability: number
    probability_basis: string
    description: string
    is_one_time?: boolean
  }
  tavily: {
    verdict: Verdict
    source_url: string | null
    source_tier: string
    snippet: string | null
    published_date: string | null
    jurisdiction_match: boolean
    legal_rate_pct: number | null
  }
  gate: {
    decision: Decision
    rules_fired: string[]
    reason: string
  }
}

export interface ReceiptSummary {
  counts: { ACCEPT: number; DOWNGRADE: number; REMOVE: number; NO_EVIDENCE: number }
  total: number
  impact: number
  kind: string
  title: string
  blurb: string
  color: string
  badge: string
}

export interface Receipt {
  receipt_id: string
  created_at: string
  document_hash: string
  previous_receipt_hash: string | null
  self_hash: string
  events: ReceiptEvent[]
  model_metadata: {
    jurisdiction?: string
    cost?: {
      model_calls: Array<{ model: string; in: number; out: number; cost_usd: number; latency_s: number }>
      tavily_calls: number
      total_cost_usd: number
      latency_seconds: number
      pricing_note: string
    }
  }
  _summary: ReceiptSummary
}

export interface CounterfactualResult {
  legal_cap: number
  avg_rate: number
  new_rate: number
  original_total: number
  new_total: number
  savings: number
  summary: string
}

export interface VerifyResult {
  receipt_id: string
  valid: boolean
  stored_hash: string
  recomputed_hash: string
}

export interface CorpusResult {
  product: { total: number; passed: number; accuracy: number }
  raw: { total: number; passed: number; accuracy: number }
  by_category: Record<string, { total: number; passed: number; product_total: number; product_passed: number }>
  failures: Array<{
    name: string; jurisdiction: string; rate: number
    expected: string; actual: string; failure_kind?: string; note?: string
  }>
  results: Array<{
    name: string; jurisdiction: string; rate: number
    expected: string; actual: string; passed: boolean; failure_kind?: string; note: string
  }>
  run_at: string
}
