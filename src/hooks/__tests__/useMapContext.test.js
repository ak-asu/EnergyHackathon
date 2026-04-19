import { renderHook, act } from '@testing-library/react'
import { useMapContext } from '../useMapContext'

test('starts with empty chips', () => {
  const { result } = renderHook(() => useMapContext())
  expect(result.current.chips).toEqual([])
})

test('addChip adds a coord chip', () => {
  const { result } = renderHook(() => useMapContext())
  act(() => result.current.addChip({ type: 'coord', payload: { lat: 32.1, lon: -102.5 } }))
  expect(result.current.chips).toHaveLength(1)
  expect(result.current.chips[0].type).toBe('coord')
})

test('addChip replaces existing region chip', () => {
  const { result } = renderHook(() => useMapContext())
  act(() => result.current.addChip({ type: 'region', payload: { label: 'A' } }))
  act(() => result.current.addChip({ type: 'region', payload: { label: 'B' } }))
  const regions = result.current.chips.filter(c => c.type === 'region')
  expect(regions).toHaveLength(1)
  expect(regions[0].payload.label).toBe('B')
})

test('site/coord chips capped at 3, oldest dropped', () => {
  const { result } = renderHook(() => useMapContext())
  for (let i = 0; i < 4; i++) {
    act(() => result.current.addChip({ type: 'coord', payload: { lat: i, lon: i } }))
  }
  const nonRegion = result.current.chips.filter(c => c.type !== 'region')
  expect(nonRegion).toHaveLength(3)
  expect(nonRegion.every(c => c.payload.lat !== 0)).toBe(true)
})

test('removeChip removes by index', () => {
  const { result } = renderHook(() => useMapContext())
  act(() => result.current.addChip({ type: 'coord', payload: { lat: 1, lon: 1 } }))
  act(() => result.current.addChip({ type: 'site', payload: { name: 'A' } }))
  act(() => result.current.removeChip(0))
  expect(result.current.chips).toHaveLength(1)
})

test('clearChips empties the array', () => {
  const { result } = renderHook(() => useMapContext())
  act(() => result.current.addChip({ type: 'coord', payload: { lat: 1, lon: 1 } }))
  act(() => result.current.clearChips())
  expect(result.current.chips).toEqual([])
})
