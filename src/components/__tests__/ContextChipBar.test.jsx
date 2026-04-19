import { render, screen, fireEvent } from '@testing-library/react'
import ContextChipBar from '../ContextChipBar'

test('renders nothing when chips is empty', () => {
  const { container } = render(<ContextChipBar chips={[]} onRemove={() => {}} />)
  expect(container.firstChild).toBeNull()
})

test('renders one dismiss button per chip', () => {
  const chips = [
    { type: 'region', payload: {} },
    { type: 'coord', payload: { lat: 32, lon: -102 } },
  ]
  render(<ContextChipBar chips={chips} onRemove={() => {}} />)
  expect(screen.getAllByRole('button')).toHaveLength(2)
})

test('calls onRemove with the correct index when × is clicked', () => {
  const onRemove = vi.fn()
  const chips = [
    { type: 'coord', payload: { lat: 1, lon: 1 } },
    { type: 'site', payload: { name: 'A' } },
  ]
  render(<ContextChipBar chips={chips} onRemove={onRemove} />)
  fireEvent.click(screen.getAllByRole('button')[1])
  expect(onRemove).toHaveBeenCalledWith(1)
})

test('displays region label for region chip', () => {
  const chips = [{ type: 'region', payload: {} }]
  render(<ContextChipBar chips={chips} onRemove={() => {}} />)
  expect(screen.getByText(/region/i)).toBeInTheDocument()
})

test('displays coord label for coord chip', () => {
  const chips = [{ type: 'coord', payload: { lat: 32.1, lon: -102.5 } }]
  render(<ContextChipBar chips={chips} onRemove={() => {}} />)
  expect(screen.getByText(/32\.1/)).toBeInTheDocument()
})
