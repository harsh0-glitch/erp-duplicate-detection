import { NavLink } from 'react-router-dom'

/**
 * Lightweight inline SVG icons — no external icon library.
 * Each takes a size prop and returns an svg element.
 */
const Icon = ({ children, size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {children}
  </svg>
)

export const IconDashboard = (p) => <Icon {...p}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></Icon>
export const IconProducts = (p) => <Icon {...p}><path d="M20 7L12 3 4 7l8 4 8-4z" /><path d="M4 7v10l8 4 8-4V7" /><path d="M12 11v10" /></Icon>
export const IconImports = (p) => <Icon {...p}><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" /><path d="M7 10l5 5 5-5" /><path d="M12 15V3" /></Icon>
export const IconDuplicates = (p) => <Icon {...p}><circle cx="9" cy="9" r="6" /><circle cx="15" cy="15" r="6" /></Icon>
export const IconReviews = (p) => <Icon {...p}><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" /></Icon>
export const IconAudit = (p) => <Icon {...p}><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><path d="M14 2v6h6" /><path d="M16 13H8" /><path d="M16 17H8" /><path d="M10 9H8" /></Icon>
export const IconCategories = (p) => <Icon {...p}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></Icon>

const navGroups = [
  {
    label: 'Workspace',
    items: [
      { to: '/dashboard', label: 'Overview', icon: IconDashboard },
      { to: '/products', label: 'Products', icon: IconProducts },
      { to: '/imports', label: 'Imports', icon: IconImports },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { to: '/duplicates', label: 'Duplicate Intelligence', icon: IconDuplicates },
      { to: '/reviews', label: 'Review History', icon: IconReviews },
    ],
  },
  {
    label: 'Governance',
    items: [
      { to: '/audit', label: 'Audit Trail', icon: IconAudit },
    ],
  },
]

const Sidebar = ({ open, onClose }) => {
  return (
    <>
      <div className={`sidebar-overlay ${open ? 'show' : ''}`} onClick={onClose} />
      <aside className={`app-sidebar ${open ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <h1>ERP Duplicate Detection</h1>
          <div className="brand-sub">Product Intelligence</div>
        </div>
        <nav className="sidebar-nav">
          {navGroups.map((group) => (
            <div key={group.label}>
              <div className="sidebar-section-label">{group.label}</div>
              {group.items.map((item) => {
                const IconComp = item.icon
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
                    onClick={onClose}
                  >
                    <IconComp size={17} />
                    {item.label}
                  </NavLink>
                )
              })}
            </div>
          ))}
          <div className="sidebar-section-label">Catalog</div>
          <NavLink
            to="/categories"
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            onClick={onClose}
          >
            <IconCategories size={17} />
            Categories
          </NavLink>
        </nav>
      </aside>
    </>
  )
}

export default Sidebar
