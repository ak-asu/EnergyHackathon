import pytest
from backend.main import OptimizeRequest


def test_optimize_request_accepts_all_filter_fields():
    req = OptimizeRequest(
        bounds={"sw": {"lat": 31.5, "lon": -103.0}, "ne": {"lat": 33.0, "lon": -101.0}},
        max_sites=2,
        min_composite=0.75,
        gas_price_max=3.0,
        power_cost_max=70.0,
        acres_min=500,
        market_filter=["ERCOT"],
    )
    assert req.max_sites == 2
    assert req.min_composite == 0.75
    assert req.gas_price_max == 3.0
    assert req.market_filter == ["ERCOT"]


def test_optimize_request_defaults():
    req = OptimizeRequest(
        bounds={"sw": {"lat": 31.5, "lon": -103.0}, "ne": {"lat": 33.0, "lon": -101.0}},
    )
    assert req.max_sites == 3
    assert req.min_composite == 0.0
    assert req.gas_price_max is None
    assert req.market_filter == []
