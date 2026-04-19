from unittest.mock import patch, MagicMock


def test_get_news_digest_returns_list():
    mock_cache = {
        "items": [{"title": "Gas prices rise", "url": "http://x.com", "snippet": "..."}],
        "fetched_at": "2026-04-18T00:00:00",
    }
    with patch('backend.agent.tools._get_news_cache', return_value=mock_cache):
        from backend.agent.tools import get_news_digest
        result = get_news_digest.invoke({})
    assert isinstance(result, list)
    assert result[0]['title'] == "Gas prices rise"


def test_get_lmp_forecast_returns_arrays():
    from backend.agent.tools import get_lmp_forecast
    result = get_lmp_forecast.invoke({'node': 'HB_WEST', 'horizon': 24})
    assert 'p50' in result
    assert 'node' in result
    assert len(result['p50']) == 24


def test_run_monte_carlo_returns_npv():
    from backend.agent.tools import run_monte_carlo
    result = run_monte_carlo.invoke({
        'gas_price': 2.0, 'lmp_p50': 42.0, 'wacc': 0.08, 'years': 20
    })
    assert 'npv_p10_m' in result
    assert 'npv_p50_m' in result
    assert 'npv_p90_m' in result


def test_web_search_returns_results_or_unavailable():
    from backend.agent.tools import web_search
    # With no Tavily key, should return unavailable message gracefully
    with patch('backend.agent.tools._get_tavily_key', return_value=None):
        result = web_search.invoke({'query': 'ERCOT gas prices'})
    assert isinstance(result, str)
    assert len(result) > 0
