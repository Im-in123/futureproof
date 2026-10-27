import { Link, Outlet, useLocation } from 'react-router-dom'

export function Layout() {
  const { pathname } = useLocation()
  const link = (to: string, label: string) =>
    <Link to={to} className={`text-sm transition-colors ${pathname === to ? 'text-zinc-100' : 'text-zinc-500 hover:text-zinc-200'}`}>{label}</Link>

  return (
    <div className="min-h-screen bg-zinc-950">
      <nav className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="font-extrabold tracking-tight text-lg">
            Future<span className="text-indigo-400">Proof</span>
          </Link>
          <div className="flex gap-6 items-center">
            {link('/', 'Home')}
            {link('/compare', 'Compare')}
            {link('/corpus', 'Corpus')}
          </div>
        </div>
      </nav>
      <main className="max-w-5xl mx-auto px-6 py-12">
        <Outlet />
      </main>
    </div>
  )
}
