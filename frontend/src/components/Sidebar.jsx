import { NavLink } from 'react-router-dom'
import './Sidebar.css'

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>SwasthiQ</h2>
        <p>EOD Reporting</p>
      </div>
      <nav className="sidebar-nav">
        <NavLink to="/reconciliation" end className={({ isActive }) => 
          `nav-link ${isActive ? 'active' : ''}`}>
          EOD Reconciliation
        </NavLink>
        <NavLink to="/analytics" end className={({ isActive }) => 
          `nav-link ${isActive ? 'active' : ''}`}>
          Analytics
        </NavLink>
        <NavLink to="/narrative" end className={({ isActive }) => 
          `nav-link ${isActive ? 'active' : ''}`}>
          AI Narrative Summary
        </NavLink>
      </nav>
    </aside>
  )
}
