import { marked } from 'marked'
import mermaid from 'mermaid'
import { useEffect, useRef } from 'react'

marked.use({
  renderer: {
    code({ text, lang }) {
      if (lang === 'mermaid') return `<pre class="mermaid">${text}</pre>`
      return false
    },
  },
})

mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' })

export default function DocsContent({ markdown }) {
  const ref = useRef(null)
  const html = marked.parse(markdown || '')

  useEffect(() => {
    if (!ref.current) return
    const nodes = Array.from(ref.current.querySelectorAll('.mermaid'))
    if (nodes.length === 0) return
    mermaid.run({ nodes }).catch(() => {})
  }, [html])

  return (
    <div
      ref={ref}
      className="docs-content"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
