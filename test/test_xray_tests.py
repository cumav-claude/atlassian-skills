"""Tests for xray_tests.py."""

import json
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path / 'jira-readonly-skills'))
sys.path.insert(0, str(_base_path / 'jira-readonly-skills' / 'scripts'))

from scripts.xray_tests import (
    xray_get_tests,
    xray_get_test_steps,
    xray_get_test_preconditions,
    xray_get_test_sets,
    xray_get_test_plans,
    xray_get_test_executions,
    xray_get_test_runs,
    xray_get_test_set_tests,
)


def _client(mock_get_client):
    client = MagicMock()
    mock_get_client.return_value = client
    client.xray_path = lambda x: f'/rest/raven/1.0/api/{x}'
    return client


class TestXrayGetTests:

    @patch('scripts.xray_tests.get_jira_client')
    def test_by_keys(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = [
            {'key': 'T-1', 'type': 'Manual', 'status': 'TODO', 'definition': ''},
            {'key': 'T-2', 'type': 'Cucumber', 'status': 'PASS', 'definition': 'Given ...'},
        ]
        data = json.loads(xray_get_tests(keys='T-1,T-2'))
        assert data['count'] == 2
        assert data['tests'][1]['definition'] == 'Given ...'
        client.get.assert_called_once_with('/rest/raven/1.0/api/test', params={'keys': 'T-1;T-2'})

    @patch('scripts.xray_tests.get_jira_client')
    def test_by_jql(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = []
        data = json.loads(xray_get_tests(jql='project = P'))
        assert data['count'] == 0
        client.get.assert_called_once_with('/rest/raven/1.0/api/test', params={'jql': 'project = P'})

    @patch('scripts.xray_tests.get_jira_client')
    def test_requires_selector(self, mock_get_client):
        _client(mock_get_client)
        data = json.loads(xray_get_tests())
        assert data['error_type'] == 'ValidationError'


class TestXrayGetTestSteps:

    @patch('scripts.xray_tests.get_jira_client')
    def test_steps_flattened(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = [
            {'id': 1, 'index': 1, 'step': {'raw': 'Open app', 'rendered': '<p>Open app</p>'},
             'data': {'raw': ''}, 'result': {'raw': 'App opens'}, 'attachments': [{'id': 9}]},
        ]
        data = json.loads(xray_get_test_steps('T-1'))
        assert data['count'] == 1
        step = data['steps'][0]
        assert step['step'] == 'Open app'
        assert step['result'] == 'App opens'
        assert step['attachment_count'] == 1
        client.get.assert_called_once_with('/rest/raven/1.0/api/test/T-1/step')

    @patch('scripts.xray_tests.get_jira_client')
    def test_missing_key(self, mock_get_client):
        _client(mock_get_client)
        assert json.loads(xray_get_test_steps(''))['error_type'] == 'ValidationError'


class TestXrayTestLinks:

    @patch('scripts.xray_tests.get_jira_client')
    def test_preconditions(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = [{'key': 'PC-1', 'type': 'Manual', 'condition': {'raw': 'Logged in'}}]
        data = json.loads(xray_get_test_preconditions('T-1'))
        assert data['preconditions'][0]['condition'] == 'Logged in'

    @patch('scripts.xray_tests.get_jira_client')
    def test_sets_plans_executions(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = [{'id': 1, 'key': 'X-1', 'summary': 'S'}]
        assert json.loads(xray_get_test_sets('T-1'))['test_sets'][0]['key'] == 'X-1'
        assert json.loads(xray_get_test_plans('T-1'))['test_plans'][0]['key'] == 'X-1'
        assert json.loads(xray_get_test_executions('T-1'))['test_executions'][0]['key'] == 'X-1'
        paths = [c.args[0] for c in client.get.call_args_list]
        assert paths == [
            '/rest/raven/1.0/api/test/T-1/testsets',
            '/rest/raven/1.0/api/test/T-1/testplans',
            '/rest/raven/1.0/api/test/T-1/testexecutions',
        ]


class TestXrayGetTestRuns:

    @patch('scripts.xray_tests.get_jira_client')
    def test_runs(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = [{
            'id': 5, 'status': 'FAIL', 'testKey': 'T-1', 'testExecKey': 'TE-1',
            'executedBy': 'jdoe', 'finishedOn': '2024-01-02T10:00:00+00:00',
            'defects': [{'id': 1, 'key': 'BUG-1', 'summary': 'Broken', 'status': 'Open'}],
            'evidences': [{'id': 1}, {'id': 2}],
        }]
        data = json.loads(xray_get_test_runs('T-1', test_environments='staging'))
        run = data['runs'][0]
        assert run['status'] == 'FAIL'
        assert run['defects'][0]['key'] == 'BUG-1'
        assert run['evidence_count'] == 2
        client.get.assert_called_once_with(
            '/rest/raven/1.0/api/test/T-1/testruns', params={'testEnvironments': 'staging'}
        )


class TestXrayGetTestSetTests:

    @patch('scripts.xray_tests.get_jira_client')
    def test_paginates(self, mock_get_client):
        client = _client(mock_get_client)
        page1 = [{'id': i, 'key': f'T-{i}', 'rank': i} for i in range(100)]
        page2 = [{'id': 100, 'key': 'T-100', 'rank': 100}]
        client.get.side_effect = [page1, page2]
        data = json.loads(xray_get_test_set_tests('TS-1'))
        assert data['count'] == 101
        assert client.get.call_count == 2
        assert client.get.call_args_list[1].kwargs['params']['page'] == 2

    @patch('scripts.xray_tests.get_jira_client')
    def test_limit(self, mock_get_client):
        client = _client(mock_get_client)
        client.get.return_value = [{'id': i, 'key': f'T-{i}'} for i in range(100)]
        data = json.loads(xray_get_test_set_tests('TS-1', limit=3))
        assert data['count'] == 3
        assert client.get.call_count == 1
