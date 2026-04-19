import { renderHook, act } from '@testing-library/react'
import { useOptimizeConfig, DEFAULT_CONFIG } from '../useOptimizeConfig'

test('initializes with default config', () => {
  const { result } = renderHook(() => useOptimizeConfig())
  expect(result.current.config.maxSites).toBe(3)
  expect(result.current.config.weights).toEqual([0.30, 0.35, 0.35])
  expect(result.current.config.minComposite).toBe(0.70)
})

test('updateConfig merges partial updates without touching other fields', () => {
  const { result } = renderHook(() => useOptimizeConfig())
  act(() => result.current.updateConfig({ maxSites: 5 }))
  expect(result.current.config.maxSites).toBe(5)
  expect(result.current.config.weights).toEqual([0.30, 0.35, 0.35])
})

test('resetConfig restores all defaults', () => {
  const { result } = renderHook(() => useOptimizeConfig())
  act(() => result.current.updateConfig({ maxSites: 9, minComposite: 0.90 }))
  act(() => result.current.resetConfig())
  expect(result.current.config).toEqual(DEFAULT_CONFIG)
})

test('collide:set-config event merges config', () => {
  const { result } = renderHook(() => useOptimizeConfig())
  act(() => {
    window.dispatchEvent(new CustomEvent('collide:set-config', { detail: { maxSites: 7 } }))
  })
  expect(result.current.config.maxSites).toBe(7)
})

test('collide:set-config fires collide:run-optimize', () => {
  renderHook(() => useOptimizeConfig())
  const spy = vi.fn()
  window.addEventListener('collide:run-optimize', spy)
  act(() => {
    window.dispatchEvent(new CustomEvent('collide:set-config', { detail: { maxSites: 2 } }))
  })
  expect(spy).toHaveBeenCalledTimes(1)
  window.removeEventListener('collide:run-optimize', spy)
})
