import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import DocsPage from '../DocsPage'

vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    run: vi.fn().mockResolvedValue(undefined),
  },
}))

vi.mock('../../components/Navbar', () => ({
  default: () => <nav data-testid="navbar" />,
}))

function renderPage(page) {
  return render(
    <MemoryRouter initialEntries={[`/docs/${page}`]}>
      <Routes>
        <Route path="/docs/:page" element={<DocsPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('DocsPage', () => {
  it('renders the navbar', () => {
    renderPage('overview')
    expect(screen.getByTestId('navbar')).toBeInTheDocument()
  })

  it('renders overview page content', () => {
    renderPage('overview')
    expect(screen.getByText(/What is COLLIDE/i)).toBeInTheDocument()
  })

  it('shows not-found message for unknown page key', () => {
    renderPage('notapage')
    expect(screen.getByText(/not found/i)).toBeInTheDocument()
  })

  it('renders the sidebar', () => {
    renderPage('overview')
    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Schema')).toBeInTheDocument()
  })
})
