"""ERCOT real-time data via gridstatus.io API.

Fetches: LMP at key hubs, fuel mix (wind%/solar%/gas%), interconnection queue count.
Falls back to static values if API key not set or request fails.
"""
import httpx
from datetime import datetime, timezone

_FALLBACK = {
    'lmp': {'HB_WEST': 42.0, 'HB_NORTH': 40.0, 'HB_SOUTH': 43.0, 'HB_BUSAVG': 41.5},
    'fuel_mix': {'wind': 0.28, 'solar': 0.08, 'gas': 0.48, 'nuclear': 0.11, 'other': 0.05},
    'queue_count': 892,
}

BASE = "https://api.gridstatus.io/v1"


async def fetch_ercot_lmp(api_key: str) -> dict[str, float]:
    """Return real-time LMP $/MWh for ERCOT hubs. Falls back to static values."""
    if not api_key:
        return _FALLBACK['lmp']
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"{BASE}/ercot/fuel_mix",
                headers={"x-api-key": api_key},
            )
            r.raise_for_status()
            row = r.json().get("data", [{}])[-1] if r.json().get("data") else {}
            return {
                'HB_WEST':   float(row.get('lmp_hb_west',   _FALLBACK['lmp']['HB_WEST'])),
                'HB_NORTH':  float(row.get('lmp_hb_north',  _FALLBACK['lmp']['HB_NORTH'])),
                'HB_SOUTH':  float(row.get('lmp_hb_south',  _FALLBACK['lmp']['HB_SOUTH'])),
                'HB_BUSAVG': float(row.get('lmp_hb_busavg', _FALLBACK['lmp']['HB_BUSAVG'])),
            }
    except Exception:
        return _FALLBACK['lmp']


async def fetch_ercot_fuel_mix(api_key: str) -> dict[str, float]:
    """Return current ERCOT fuel mix fractions (sum ≈ 1.0). Falls back to static."""
    if not api_key:
        return _FALLBACK['fuel_mix']
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"{BASE}/ercot/fuel_mix",
                headers={"x-api-key": api_key},
                params={"limit": 1},
            )
            r.raise_for_status()
            data = r.json().get("data", [])
            if not data:
                return _FALLBACK['fuel_mix']
            row = data[-1]
            total = max(float(row.get('total_mw', 1)), 1)
            return {
                'wind':    round(float(row.get('wind_mw',    0)) / total, 4),
                'solar':   round(float(row.get('solar_mw',   0)) / total, 4),
                'gas':     round(float(row.get('gas_mw',     0)) / total, 4),
                'nuclear': round(float(row.get('nuclear_mw', 0)) / total, 4),
                'other':   round(float(row.get('other_mw',   0)) / total, 4),
            }
    except Exception:
        return _FALLBACK['fuel_mix']


async def fetch_ercot_snapshot(api_key: str) -> dict:
    """Fetch LMP + fuel mix in one call. Used by regime classifier + feature extractor."""
    import asyncio
    lmp, fuel = await asyncio.gather(
        fetch_ercot_lmp(api_key),
        fetch_ercot_fuel_mix(api_key),
    )
    return {
        'lmp': lmp,
        'fuel_mix': fuel,
        'fetched_at_utc': datetime.now(timezone.utc).isoformat(),
    }
