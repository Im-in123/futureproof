import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Home } from './pages/Home'
import { Receipt } from './pages/Receipt'
import { Compare } from './pages/Compare'
import { Corpus } from './pages/Corpus'
import { Verify } from './pages/Verify'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/receipt/:id" element={<Receipt />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/corpus" element={<Corpus />} />
          <Route path="/verify/:id" element={<Verify />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
