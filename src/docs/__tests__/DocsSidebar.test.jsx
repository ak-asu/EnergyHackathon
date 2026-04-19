import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import DocsSidebar from '../DocsSidebar'

function renderSidebar(page = 'overview') {
  return render(
    <MemoryRouter initialEntries={[`/docs/${page}`]}>
      <Routes>
        <Route path="/docs/:page" element={<DocsSidebar />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('DocsSidebar', () => {
  it('renders all 6 navigation items', () => {
    renderSidebar()
    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Architecture')).toBeInTheDocument()
    expect(screen.getByText('How It Works')).toBeInTheDocument()
    expect(screen.getByText('Features')).toBeInTheDocument()
    expect(screen.getByText('Data')).toBeInTheDocument()
    expect(screen.getByText('Schema')).toBeInTheDocument()
  })

  it('marks the active page link', () => {
    renderSidebar('architecture')
    const activeLink = screen.getByText('Architecture').closest('a')
    expect(activeLink).toHaveClass('docs-nav-link--active')
  })

  it('does not mark inactive links as active', () => {
    renderSidebar('architecture')
    const overviewLink = screen.getByText('Overview').closest('a')
    expect(overviewLink).not.toHaveClass('docs-nav-link--active')
  })
})
