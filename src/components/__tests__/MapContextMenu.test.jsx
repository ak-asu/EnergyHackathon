import { render, screen, fireEvent } from '@testing-library/react'
import MapContextMenu from '../MapContextMenu'

const noop = () => {}
const spaceTarget = { type: 'space', lat: 32.1, lon: -102.5 }
const siteTarget = { type: 'site', site: { lat: 32.1, lng: -102.5, name: 'Test Site' } }

test('renders nothing when open is false', () => {
  const { container } = render(
    <MapContextMenu open={false} x={100} y={100} target={spaceTarget}
      committedBounds={null} onClose={noop} onEvaluate={noop}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  expect(container.firstChild).toBeNull()
})

test('shows space options when target type is space', () => {
  render(
    <MapContextMenu open={true} x={100} y={100} target={spaceTarget}
      committedBounds={null} onClose={noop} onEvaluate={noop}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  expect(screen.getByText('Evaluate this location')).toBeInTheDocument()
  expect(screen.getByText('Add compare pin here')).toBeInTheDocument()
  expect(screen.getByText('Send location to agent')).toBeInTheDocument()
})

test('shows site options when target type is site', () => {
  render(
    <MapContextMenu open={true} x={100} y={100} target={siteTarget}
      committedBounds={null} onClose={noop} onEvaluate={noop}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  expect(screen.getByText('Evaluate site')).toBeInTheDocument()
  expect(screen.getByText('Add to compare')).toBeInTheDocument()
  expect(screen.getByText('Send to agent')).toBeInTheDocument()
})

test('hides Set as region center when no committedBounds', () => {
  render(
    <MapContextMenu open={true} x={100} y={100} target={siteTarget}
      committedBounds={null} onClose={noop} onEvaluate={noop}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  expect(screen.queryByText('Set as region center')).not.toBeInTheDocument()
})

test('shows Set as region center when committedBounds exists', () => {
  render(
    <MapContextMenu open={true} x={100} y={100} target={siteTarget}
      committedBounds={{ exists: true }} onClose={noop} onEvaluate={noop}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  expect(screen.getByText('Set as region center')).toBeInTheDocument()
})

test('calls onClose when Escape is pressed', () => {
  const onClose = vi.fn()
  render(
    <MapContextMenu open={true} x={100} y={100} target={spaceTarget}
      committedBounds={null} onClose={onClose} onEvaluate={noop}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  fireEvent.keyDown(document, { key: 'Escape' })
  expect(onClose).toHaveBeenCalledTimes(1)
})

test('calls onEvaluate and onClose when Evaluate this location clicked', () => {
  const onEvaluate = vi.fn()
  const onClose = vi.fn()
  render(
    <MapContextMenu open={true} x={100} y={100} target={spaceTarget}
      committedBounds={null} onClose={onClose} onEvaluate={onEvaluate}
      onAddCompare={noop} onSendToAgent={noop} onSetRegionCenter={noop} />
  )
  fireEvent.click(screen.getByText('Evaluate this location'))
  expect(onEvaluate).toHaveBeenCalledWith(32.1, -102.5)
  expect(onClose).toHaveBeenCalledTimes(1)
})
