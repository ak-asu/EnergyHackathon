import { useParams } from 'react-router-dom'
import Navbar from '../components/Navbar'
import DocsLayout from './DocsLayout'
import DocsContent from './DocsContent'
import { DOCS_PAGES } from './pages/index.js'

export default function DocsPage() {
  const { page } = useParams()
  const doc = DOCS_PAGES[page]

  return (
    <>
      <Navbar />
      <DocsLayout>
        {doc
          ? <DocsContent markdown={doc.content} />
          : <div className="docs-not-found">Page "{page}" not found.</div>
        }
      </DocsLayout>
    </>
  )
}
