import json
from unittest.mock import patch, MagicMock
from backend.agent.graph import config_node


def test_config_node_extracts_max_sites():
    mock_resp = MagicMock()
    mock_resp.content = json.dumps({"max_sites": 5})

    with patch('backend.agent.graph._get_llm') as mock_llm:
        mock_llm.return_value.invoke.return_value = mock_resp
        result = config_node({
            'query': 'find 5 sites',
            'context': {},
            'intent': 'config',
            'needs_web_search': False,
            'tool_results': [],
            'citations': [],
            'final_response': '',
        })

    assert result['tool_results'][0]['config_update']['max_sites'] == 5
    assert len(result['citations']) == 1


def test_config_node_handles_invalid_llm_json():
    mock_resp = MagicMock()
    mock_resp.content = "not json"

    with patch('backend.agent.graph._get_llm') as mock_llm:
        mock_llm.return_value.invoke.return_value = mock_resp
        result = config_node({
            'query': 'change something',
            'context': {},
            'intent': 'config',
            'needs_web_search': False,
            'tool_results': [],
            'citations': [],
            'final_response': '',
        })

    assert result['tool_results'][0]['config_update'] == {}
