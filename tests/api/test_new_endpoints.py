import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.main import app

client = TestClient(app)


def test_regime_includes_labels():
    from backend.scoring.regime import RegimeState
    mock_regime = RegimeState(label='normal', proba=[0.8, 0.1, 0.1],
                               labels=['normal', 'stress_scarcity', 'wind_curtailment'])
    with patch('backend.main.get_cached_regime', return_value=mock_regime):
        r = client.get('/api/regime')
    assert r.status_code == 200
    data = r.json()
    assert 'labels' in data
    assert data['labels'] == ['normal', 'stress_scarcity', 'wind_curtailment']
    assert len(data['proba']) == 3


def test_heatmap_returns_geojson():
    r = client.get('/api/heatmap?layer=composite&bounds=29,-104,34,-99&zoom=8')
    assert r.status_code == 200
    data = r.json()
    assert data['type'] == 'FeatureCollection'
    assert isinstance(data['features'], list)
    for feat in data['features']:
        assert feat['type'] == 'Feature'
        assert 'score' in feat['properties']
        assert 'layer' in feat['properties']


def test_heatmap_invalid_layer_returns_empty():
    r = client.get('/api/heatmap?layer=nonexistent&bounds=29,-104,34,-99&zoom=8')
    assert r.status_code == 200
    assert r.json()['features'] == []


def test_forecast_returns_arrays():
    r = client.get('/api/forecast?node=HB_WEST&horizon=72')
    assert r.status_code == 200
    data = r.json()
    assert 'p50' in data
    assert 'node' in data
    assert 'method' in data
    assert len(data['p50']) == 72


def test_compare_returns_ranked_list():
    r = client.get('/api/compare?coords=31.9,-102.1;32.5,-101.2')
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # Should be sorted descending by composite_score
    scores = [d['composite_score'] for d in data]
    assert scores == sorted(scores, reverse=True)
    for item in data:
        assert 'lat' in item
        assert 'composite_score' in item
