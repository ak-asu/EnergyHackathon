import { NavLink } from 'react-router-dom'
import { DOCS_NAV } from './pages/index.js'

export default function DocsSidebar() {
  return (
    <aside className="docs-sidebar">
      <div className="docs-sidebar-title">Documentation</div>
      <ul className="docs-nav">
        {DOCS_NAV.map(({ key, label }) => (
          <li key={key}>
            <NavLink
              to={`/docs/${key}`}
              className={({ isActive }) =>
                isActive ? 'docs-nav-link docs-nav-link--active' : 'docs-nav-link'
              }
            >
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </aside>
  )
}
