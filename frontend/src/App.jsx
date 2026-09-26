import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Reconciliation from './pages/Reconciliation'
import Analytics from './pages/Analytics'
import Narrative from './pages/Narrative'
import './App.css'

function App() {
  return (
    <div className="app">
      <Sidebar />
      <div className="main-content">
        <Routes>
          <Route path="/reconciliation" element={<Reconciliation />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/narrative" element={<Narrative />} />
          <Route path="/" element={<Navigate to="/reconciliation" replace />} />
          <Route path="*" element={<Navigate to="/reconciliation" replace />} />
        </Routes>
      </div>
    </div>
  )
}

export default App
