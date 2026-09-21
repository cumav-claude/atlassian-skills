"""Tests for xray_executions.py."""

import json
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path / 'jira-readonly-skills'))
sys.path.insert(0, str(_base_path / 'jira-readonly-skills' / 'scripts'))

from scripts.xray_executions import (
    xray_get_test_execution_tests,
    xray_get_test_run,
    xray_get_test_run_steps,
    xray_get_test_statuses,
    xray_get_test_step_statuses,
)


def _client(mock_get_client):
    client = MagicMock()
    mock_get_client.return_value = client
    client.xray_path = lambda x: f'/rest/raven/1.0/api/{x}'
    return client


class TestXrayGetTestExecutionTests:

    @patch('scripts.xray_executions.get_jira_client')
    def test_detailed_with_counts(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = [
            {'id': 1, 'key': 'T-1', 'rank': 1, 'status': 'PASS', 'executedBy': 'jdoe',
             'finishedOn': '2024-01-01T10:00:00+00:00', 'defects': [], 'evidences': []},
            {'id': 2, 'key': 'T-2', 'rank': 2, 'status': 'FAIL', 'executedBy': 'jdoe',
             'defects': [{'id': 7, 'key': 'BUG-7', 'summary': 'x', 'status': 'Open'}]},
            {'id': 3, 'key': 'T-3', 'rank': 3, 'status': 'TODO'},
        ]
        data = json.loads(xray_get_test_execution_tests('TE-1'))
        assert data['count'] == 3
        assert data['status_counts'] == {'PASS': 1, 'FAIL': 1, 'TODO': 1}
        assert data['runs'][1]['defects'][0]['key'] == 'BUG-7'
        call = client.get.call_args_list[0]
        assert call.args[0] == '/rest/raven/1.0/api/testexec/TE-1/test'
        assert call.kwargs['params']['detailed'] == 'true'
        assert call.kwargs['params']['page'] == 1

    @patch('scripts.xray_executions.get_jira_client')
    def test_missing_key(self, mock_get_client):
        _client(mock_get_client)
        assert json.loads(xray_get_test_execution_tests(''))['error_type'] == 'ValidationError'


class TestXrayGetTestRun:

    @patch('scripts.xray_executions.get_jira_client')
    def test_by_id(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = {'id': 5, 'status': 'PASS', 'testKey': 'T-1', 'testExecKey': 'TE-1',
                                   'comment': {'raw': 'ok'}}
        data = json.loads(xray_get_test_run(run_id=5))
        assert data['status'] == 'PASS'
        assert data['comment'] == 'ok'
        client.get.assert_called_once_with('/rest/raven/1.0/api/testrun/5')

    @patch('scripts.xray_executions.get_jira_client')
    def test_by_exec_and_test(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = {'id': 5, 'status': 'PASS'}
        json.loads(xray_get_test_run(test_exec_key='TE-1', test_key='T-1'))
        client.get.assert_called_once_with(
            '/rest/raven/1.0/api/testrun',
            params={'testExecIssueKey': 'TE-1', 'testIssueKey': 'T-1'}
        )

    @patch('scripts.xray_executions.get_jira_client')
    def test_requires_selector(self, mock_get_client):
        _client(mock_get_client)
        assert json.loads(xray_get_test_run(test_key='T-1'))['error_type'] == 'ValidationError'


class TestXrayGetTestRunSteps:

    @patch('scripts.xray_executions.get_jira_client')
    def test_steps(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = [
            {'id': 1, 'index': 1, 'status': 'FAIL', 'step': {'raw': 'Click'},
             'result': {'raw': 'Opens'}, 'actualResult': {'raw': 'Crash'},
             'defects': [{'key': 'BUG-1'}], 'evidences': [{'id': 1}]},
        ]
        data = json.loads(xray_get_test_run_steps(1))
        step = data['steps'][0]
        assert step['status'] == 'FAIL'
        assert step['expected_result'] == 'Opens'
        assert step['actual_result'] == 'Crash'
        assert step['defects'][0]['key'] == 'BUG-1'
        assert step['evidence_count'] == 1


class TestXrayStatuses:

    @patch('scripts.xray_executions.get_jira_client')
    def test_test_statuses(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = [{'id': 1, 'name': 'PASS', 'final': True, 'requirementStatusName': 'OK'}]
        data = json.loads(xray_get_test_statuses())
        assert data['statuses'][0]['requirement_status'] == 'OK'
        client.get.assert_called_once_with('/rest/raven/1.0/api/settings/teststatuses')

    @patch('scripts.xray_executions.get_jira_client')
    def test_step_statuses(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = [{'id': 2, 'name': 'SKIP', 'testStatusId': 3}]
        data = json.loads(xray_get_test_step_statuses())
        assert data['statuses'][0]['test_status_id'] == 3
