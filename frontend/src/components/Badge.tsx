export function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span className="inline-block px-2.5 py-1 rounded-md text-[10px] font-bold tracking-wider font-mono"
      style={{ background: `${color}22`, color }}>
      {label}
    </span>
  )
}
