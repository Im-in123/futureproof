export function RateBar({ rate, cap }: { rate: number | null; cap: number | null }) {
  if (rate === null || cap === null || cap <= 0) return null
  const scaleMax = cap * 2
  const capPos = (cap / scaleMax) * 100
  const ratePos = Math.min(100, (rate / scaleMax) * 100)
  const overflow = rate > cap
  const redWidth = overflow ? ratePos - capPos : 0
  const greenWidth = overflow ? capPos : ratePos

  return (
    <div className="mt-3">
      <div className="flex justify-between text-[10px] text-zinc-500 font-mono mb-1">
        <span>0%</span>
        <span className="text-zinc-100">cap {cap.toFixed(0)}%</span>
        <span>{scaleMax.toFixed(0)}%</span>
      </div>
      <div className="relative h-2 bg-zinc-800 rounded overflow-visible">
        {overflow ? (
          <>
            <div className="absolute left-0 top-0 h-full rounded-l bg-gradient-to-r from-emerald-800 to-emerald-500"
              style={{ width: `${capPos}%` }} />
            <div className="absolute top-0 h-full bg-gradient-to-r from-emerald-500 to-red-500"
              style={{ left: `${capPos}%`, width: `${redWidth}%` }} />
          </>
        ) : (
          <div className="absolute left-0 top-0 h-full rounded bg-gradient-to-r from-emerald-800 to-emerald-500"
            style={{ width: `${greenWidth}%` }} />
        )}
        <div className="absolute top-[-4px] h-[calc(100%+8px)] w-[2px] bg-white shadow-[0_0_4px_rgba(255,255,255,0.5)]"
          style={{ left: `${capPos}%` }} />
      </div>
      <div className="flex justify-between text-[11px] font-mono mt-1.5">
        <span className="text-zinc-400">clause rate</span>
        <span className={overflow ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
          {rate.toFixed(1)}% {overflow ? '— exceeds cap' : '— within cap'}
        </span>
      </div>
    </div>
  )
}
