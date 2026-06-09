import { NavLink } from 'react-router-dom'

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="logo-icon">M</div>
        <div>
          <h1>MITS Dashboard</h1>
          <span>Analytics & Insights</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/"
          end
          className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
        >
          <span className="icon">📊</span>
          Results & Analytics
        </NavLink>

        <NavLink
          to="/students"
          className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
        >
          <span className="icon">👥</span>
          Student Profiles
        </NavLink>
      </nav>
    </aside>
  )
}
