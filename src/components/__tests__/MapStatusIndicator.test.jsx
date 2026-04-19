import { render, screen } from '@testing-library/react'
import MapStatusIndicator from '../MapStatusIndicator'

test('renders nothing when mapBusy is false', () => {
  const { container } = render(<MapStatusIndicator mapBusy={false} label="" />)
  expect(container.firstChild).toBeNull()
})

test('shows label when mapBusy is true', () => {
  render(<MapStatusIndicator mapBusy={true} label="Optimizing…" />)
  expect(screen.getByText('Optimizing…')).toBeInTheDocument()
})

test('shows Evaluating label', () => {
  render(<MapStatusIndicator mapBusy={true} label="Evaluating…" />)
  expect(screen.getByText('Evaluating…')).toBeInTheDocument()
})
