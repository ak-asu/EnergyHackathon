import { render, screen, fireEvent } from '@testing-library/react'
import OptimizeConfigDialog from '../OptimizeConfigDialog'
import { DEFAULT_CONFIG } from '../../hooks/useOptimizeConfig'

test('renders nothing when open is false', () => {
  render(<OptimizeConfigDialog open={false} config={DEFAULT_CONFIG} onApply={() => {}} onReset={() => {}} onClose={() => {}} />)
  expect(screen.queryByText('Optimization Config')).not.toBeInTheDocument()
})

test('renders dialog when open is true', () => {
  render(<OptimizeConfigDialog open={true} config={DEFAULT_CONFIG} onApply={() => {}} onReset={() => {}} onClose={() => {}} />)
  expect(screen.getByText('Optimization Config')).toBeInTheDocument()
})

test('calls onApply when Apply clicked', () => {
  const onApply = vi.fn()
  render(<OptimizeConfigDialog open={true} config={DEFAULT_CONFIG} onApply={onApply} onReset={() => {}} onClose={() => {}} />)
  fireEvent.click(screen.getByText('Apply'))
  expect(onApply).toHaveBeenCalledTimes(1)
})

test('calls onReset when Reset clicked', () => {
  const onReset = vi.fn()
  render(<OptimizeConfigDialog open={true} config={DEFAULT_CONFIG} onApply={() => {}} onReset={onReset} onClose={() => {}} />)
  fireEvent.click(screen.getByText('Reset'))
  expect(onReset).toHaveBeenCalledTimes(1)
})

test('calls onClose when × button clicked', () => {
  const onClose = vi.fn()
  render(<OptimizeConfigDialog open={true} config={DEFAULT_CONFIG} onApply={() => {}} onReset={() => {}} onClose={onClose} />)
  fireEvent.click(screen.getByText('✕'))
  expect(onClose).toHaveBeenCalledTimes(1)
})
