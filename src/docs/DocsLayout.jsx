import DocsSidebar from './DocsSidebar'
import './docs.css'

export default function DocsLayout({ children }) {
  return (
    <div className="docs-page">
      <div className="docs-layout">
        <DocsSidebar />
        <div className="docs-content-wrap">
          {children}
        </div>
      </div>
    </div>
  )
}
