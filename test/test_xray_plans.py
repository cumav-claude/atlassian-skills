"""Tests for xray_plans.py."""

import json
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path / 'jira-readonly-skills'))
sys.path.insert(0, str(_base_path / 'jira-readonly-skills' / 'scripts'))

from scripts.xray_plans import xray_get_test_plan_tests, xray_get_test_plan_executions


def _client(mock_get_client):
    client = MagicMock()
    mock_get_client.return_value = client
    client.xray_path = lambda x: f'/rest/raven/1.0/api/{x}'
    return client


class TestXrayGetTestPlanTests:

    @patch('scripts.xray_plans.get_jira_client')
    def test_tests_with_counts(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = [
            {'id': 1, 'key': 'T-1', 'latestStatus': 'PASS'},
            {'id': 2, 'key': 'T-2', 'latestStatus': 'PASS'},
            {'id': 3, 'key': 'T-3', 'latestStatus': 'TODO'},
        ]
        data = json.loads(xray_get_test_plan_tests('TP-1'))
        assert data['count'] == 3
        assert data['status_counts'] == {'PASS': 2, 'TODO': 1}
        assert client.get.call_args.args[0] == '/rest/raven/1.0/api/testplan/TP-1/test'

    @patch('scripts.xray_plans.get_jira_client')
    def test_missing_key(self, mock_get_client):
        _client(mock_get_client)
        assert json.loads(xray_get_test_plan_tests(''))['error_type'] == 'ValidationError'


class TestXrayGetTestPlanExecutions:

    @patch('scripts.xray_plans.get_jira_client')
    def test_filters_archived(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = [
            {'id': 1, 'key': 'TE-1', 'summary': 'Run 1', 'archived': False, 'environments': ['qa']},
            {'id': 2, 'key': 'TE-2', 'summary': 'Old', 'archived': True},
        ]
        data = json.loads(xray_get_test_plan_executions('TP-1'))
        assert [e['key'] for e in data['test_executions']] == ['TE-1']
        assert data['test_executions'][0]['environments'] == ['qa']

        data = json.loads(xray_get_test_plan_executions('TP-1', include_archived=True))
        assert data['count'] == 2
        client.get.assert_called_with('/rest/raven/1.0/api/testplan/TP-1/testexecution')
