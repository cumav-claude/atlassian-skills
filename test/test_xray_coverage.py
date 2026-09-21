"""Tests for xray_coverage.py."""

import json
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path / 'jira-readonly-skills'))
sys.path.insert(0, str(_base_path / 'jira-readonly-skills' / 'scripts'))

from scripts.xray_coverage import (
    xray_get_requirement_tests,
    xray_get_test_requirements,
    xray_get_test_plan_requirements,
    xray_get_requirements_by_status,
)


def _client(mock_get_client, issues=None):
    client = MagicMock()
    mock_get_client.return_value = client
    client.api_path = lambda x: f'/rest/api/2/{x}'
    client.get.return_value = {'issues': issues or [], 'total': len(issues or []), 'startAt': 0}
    return client


def _issue(key, summary='S', itype='Test', versions=()):
    return {
        'key': key, 'id': '1',
        'fields': {
            'summary': summary, 'status': {'name': 'Open'}, 'issuetype': {'name': itype},
            'fixVersions': [{'name': v} for v in versions],
        }
    }


def _jql(client):
    return client.get.call_args.kwargs['params']['jql']


class TestRequirementTests:

    @patch('scripts.xray_coverage.get_jira_client')
    def test_requirement_tests(self, mock_get_client):
        client = _client(mock_get_client, [_issue('T-1'), _issue('T-2')])
        data = json.loads(xray_get_requirement_tests('REQ-1'))
        assert data['count'] == 2
        assert data['requirement_key'] == 'REQ-1'
        assert _jql(client) == 'issue in requirementTests("REQ-1")'

    @patch('scripts.xray_coverage.get_jira_client')
    def test_test_requirements(self, mock_get_client):
        client = _client(mock_get_client, [_issue('REQ-1', itype='Story', versions=['1.0'])])
        data = json.loads(xray_get_test_requirements('T-1'))
        assert data['issues'][0]['fix_versions'] == ['1.0']
        assert 'custom_fields' not in data['issues'][0]
        assert _jql(client) == 'issue in testRequirements("T-1")'

    @patch('scripts.xray_coverage.get_jira_client')
    def test_plan_requirements(self, mock_get_client):
        client = _client(mock_get_client)
        json.loads(xray_get_test_plan_requirements('TP-1'))
        assert _jql(client) == 'issue in testPlanRequirements("TP-1")'

    @patch('scripts.xray_coverage.get_jira_client')
    def test_missing_key(self, mock_get_client):
        _client(mock_get_client)
        assert json.loads(xray_get_requirement_tests(''))['error_type'] == 'ValidationError'


class TestRequirementsByStatus:

    @patch('scripts.xray_coverage.get_jira_client')
    def test_status_only(self, mock_get_client):
        client = _client(mock_get_client)
        data = json.loads(xray_get_requirements_by_status('nok'))
        assert data['coverage_status'] == 'NOK'
        assert _jql(client) == 'issue in requirements("NOK")'

    @patch('scripts.xray_coverage.get_jira_client')
    def test_project_and_version(self, mock_get_client):
        client = _client(mock_get_client)
        json.loads(xray_get_requirements_by_status('OK', project_key='P', version='1.0'))
        assert _jql(client) == 'issue in requirements("OK", "P", "1.0")'

    @patch('scripts.xray_coverage.get_jira_client')
    def test_version_without_project(self, mock_get_client):
        client = _client(mock_get_client)
        json.loads(xray_get_requirements_by_status('UNCOVERED', version='1.0'))
        assert _jql(client) == 'issue in requirements("UNCOVERED", "", "1.0")'

    @patch('scripts.xray_coverage.get_jira_client')
    def test_by_test_plan(self, mock_get_client):
        client = _client(mock_get_client)
        json.loads(xray_get_requirements_by_status('NOTRUN', test_plan_key='TP-1', project_key='P'))
        assert _jql(client) == 'issue in requirementsWithStatusByTestPlan("NOTRUN", "TP-1") AND project = "P"'

    @patch('scripts.xray_coverage.get_jira_client')
    def test_invalid_status(self, mock_get_client):
        _client(mock_get_client)
        assert json.loads(xray_get_requirements_by_status('MAYBE'))['error_type'] == 'ValidationError'
