import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import DocsContent from '../DocsContent'

vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    run: vi.fn().mockResolvedValue(undefined),
  },
}))

describe('DocsContent', () => {
  it('renders markdown headings as HTML', () => {
    const { container } = render(<DocsContent markdown="# Hello World" />)
    expect(container.querySelector('h1').textContent).toBe('Hello World')
  })

  it('renders markdown paragraphs', () => {
    const { container } = render(<DocsContent markdown="Just a paragraph." />)
    expect(container.querySelector('p').textContent).toBe('Just a paragraph.')
  })

  it('renders GFM tables', () => {
    const md = '| A | B |\n|---|---|\n| 1 | 2 |'
    const { container } = render(<DocsContent markdown={md} />)
    expect(container.querySelector('table')).not.toBeNull()
    expect(container.querySelector('th').textContent).toBe('A')
  })

  it('renders mermaid code blocks as .mermaid elements', () => {
    const md = '```mermaid\ngraph TD\n  A --> B\n```'
    const { container } = render(<DocsContent markdown={md} />)
    expect(container.querySelector('.mermaid')).not.toBeNull()
  })

  it('renders empty string without crashing', () => {
    const { container } = render(<DocsContent markdown="" />)
    expect(container.querySelector('.docs-content')).not.toBeNull()
  })
})
