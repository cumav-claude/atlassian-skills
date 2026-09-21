"""Tests for xray_release_report.py."""

import json
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path / 'jira-readonly-skills'))
sys.path.insert(0, str(_base_path / 'jira-readonly-skills' / 'scripts'))

from scripts.xray_release_report import xray_release_report, _parse_timestamp


def _link(test_key, summary='test', link_type='Tests', direction='inwardIssue', itype='Test'):
    return {
        'type': {'name': link_type, 'inward': 'is tested by', 'outward': 'tests'},
        direction: {'key': test_key, 'fields': {'summary': summary, 'issuetype': {'name': itype}}},
    }


def _req(key, summary, itype='Story', versions=('1.0',), links=()):
    return {
        'key': key, 'id': '1',
        'fields': {
            'summary': summary, 'status': {'name': 'Done'}, 'issuetype': {'name': itype},
            'priority': {'name': 'High'},
            'fixVersions': [{'name': v} for v in versions],
            'issuelinks': list(links),
        }
    }


def _search(issues):
    return {'issues': issues, 'total': len(issues), 'startAt': 0}


class Router:
    """Route mocked GET calls by path so the report can hit several endpoints."""

    def __init__(self):
        self.routes = {}
        self.calls = []

    def add(self, path, response, when=None):
        self.routes.setdefault(path, []).append((when, response))

    def __call__(self, path, params=None):
        self.calls.append((path, params))
        for when, response in self.routes.get(path, []):
            if when is None or when(params or {}):
                return response
        raise AssertionError(f'unexpected GET {path} {params}')


def _client(mock_get_client):
    client = MagicMock()
    mock_get_client.return_value = client
    client.api_path = lambda x: f'/rest/api/2/{x}'
    client.xray_path = lambda x: f'/rest/raven/1.0/api/{x}'
    router = Router()
    client.get.side_effect = router
    return client, router


def _jql_contains(text):
    return lambda p: text in p.get('jql', '')


class TestParseTimestamp:

    def test_formats(self):
        assert _parse_timestamp('2024-01-02T10:00:00+00:00') > 0
        assert _parse_timestamp('2024-01-02T10:00:00+0000') > 0
        assert _parse_timestamp('2024-01-02T10:00:00Z') > 0
        assert _parse_timestamp('garbage') == 0.0
        assert _parse_timestamp(None) == 0.0
        assert _parse_timestamp('2024-01-02T10:00:00+00:00') < _parse_timestamp('2024-01-03T10:00:00+00:00')


class TestReleaseReportWithPlanAndVersion:

    @patch('scripts.xray_release_report.get_jira_client')
    def test_full_report(self, mock_get_client):
        client, router = _client(mock_get_client)

        # Requirements with fixVersion 1.0: REQ-1 (in plan), REQ-2 (missed by plan),
        # REQ-3 (uncovered), plus a Test issue that must be ignored.
        router.add('/rest/api/2/search', _search([
            _req('REQ-1', 'Login', links=[_link('T-1', 'login ok'), _link('T-2', 'login bad pw')]),
            _req('REQ-2', 'Logout', links=[_link('T-9', 'logout', direction='outwardIssue')]),
            _req('REQ-3', 'Reset password'),
            _req('T-1', 'a test', itype='Test'),
        ]), when=_jql_contains('fixVersion'))
        # Requirements covered by the plan: REQ-1 and REQ-4 (not in the version)
        router.add('/rest/api/2/search', _search([
            _req('REQ-1', 'Login', links=[_link('T-1', 'login ok'), _link('T-2', 'login bad pw')]),
            _req('REQ-4', 'Old story', versions=('0.9',), links=[_link('T-3', 'old')]),
        ]), when=_jql_contains('testPlanRequirements'))

        router.add('/rest/raven/1.0/api/testplan/TP-1/test', [
            {'id': 1, 'key': 'T-1', 'latestStatus': 'PASS'},
            {'id': 2, 'key': 'T-2', 'latestStatus': 'FAIL'},
            {'id': 3, 'key': 'T-3', 'latestStatus': 'TODO'},
            {'id': 4, 'key': 'T-4', 'latestStatus': 'PASS'},
        ])
        router.add('/rest/raven/1.0/api/testplan/TP-1/testexecution', [
            {'id': 10, 'key': 'TE-1', 'summary': 'first', 'archived': False},
            {'id': 11, 'key': 'TE-2', 'summary': 'rerun', 'archived': False},
            {'id': 12, 'key': 'TE-0', 'summary': 'archived', 'archived': True},
        ])
        router.add('/rest/raven/1.0/api/testexec/TE-1/test', [
            {'id': 100, 'key': 'T-1', 'status': 'FAIL', 'executedBy': 'jdoe',
             'finishedOn': '2024-01-01T10:00:00+00:00',
             'defects': [{'id': 1, 'key': 'BUG-1', 'summary': 'old bug', 'status': 'Closed'}]},
            {'id': 101, 'key': 'T-2', 'status': 'FAIL', 'executedBy': 'jdoe',
             'finishedOn': '2024-01-01T11:00:00+00:00',
             'defects': [{'id': 2, 'key': 'BUG-2', 'summary': 'pw check', 'status': 'Open'}]},
            {'id': 102, 'key': 'T-4', 'status': 'PASS', 'executedBy': 'jdoe',
             'finishedOn': '2024-01-01T12:00:00+00:00'},
        ])
        router.add('/rest/raven/1.0/api/testexec/TE-2/test', [
            {'id': 200, 'key': 'T-1', 'status': 'PASS', 'executedBy': 'asmith',
             'finishedOn': '2024-01-02T10:00:00+00:00'},
        ])
        # T-9 is outside the plan: latest run looked up directly
        router.add('/rest/raven/1.0/api/test/T-9/testruns', [
            {'id': 300, 'status': 'PASS', 'testExecKey': 'TE-7', 'executedBy': 'bob',
             'finishedOn': '2023-12-01T10:00:00+00:00'},
            {'id': 301, 'status': 'ABORTED', 'testExecKey': 'TE-8', 'executedBy': 'bob',
             'finishedOn': '2023-12-05T10:00:00+00:00'},
        ])

        data = json.loads(xray_release_report(test_plan_key='TP-1', fix_version='1.0', project_key='P'))
        assert data.get('success', True), data

        # Archived execution must not be queried
        assert not any(p == '/rest/raven/1.0/api/testexec/TE-0/test' for p, _ in router.calls)

        by_key = {r['key']: r for r in data['requirements']}
        assert set(by_key) == {'REQ-1', 'REQ-2', 'REQ-3', 'REQ-4'}

        # REQ-1: T-1 latest run is the PASS from TE-2, T-2 still FAIL -> blocked
        req1 = by_key['REQ-1']
        assert req1['in_release_scope'] and req1['in_test_plan']
        assert req1['releasable'] is False
        assert req1['blockers'] == ['T-2 is FAIL']
        t1 = next(t for t in req1['tests'] if t['key'] == 'T-1')
        assert t1['status'] == 'PASS'
        assert t1['execution_key'] == 'TE-2'
        assert t1['executed_by'] == 'asmith'
        assert t1['in_test_plan'] is True
        t2 = next(t for t in req1['tests'] if t['key'] == 'T-2')
        assert t2['defects'][0]['key'] == 'BUG-2'

        # REQ-2: missed by plan, its test outside the plan is ABORTED (latest)
        req2 = by_key['REQ-2']
        assert req2['in_release_scope'] and not req2['in_test_plan']
        assert req2['warnings'][0].startswith('MISSED BY TEST PLAN')
        assert req2['releasable'] is False
        assert req2['blockers'] == ['T-9 is ABORTED']
        assert req2['tests'][0]['in_test_plan'] is False

        # REQ-3: no tests
        req3 = by_key['REQ-3']
        assert req3['releasable'] is False
        assert req3['blockers'] == ['UNCOVERED: no tests linked']
        assert req3['warnings'][0].startswith('MISSED BY TEST PLAN')

        # REQ-4: only in the plan, its test had no run -> plan status TODO
        req4 = by_key['REQ-4']
        assert not req4['in_release_scope'] and req4['in_test_plan']
        assert req4['tests'][0]['status'] == 'TODO'
        assert req4['releasable'] is False

        # Plan test T-4 covers no requirement in scope
        assert [t['key'] for t in data['tests_without_requirement']] == ['T-4']
        assert data['tests_without_requirement'][0]['status'] == 'PASS'

        summary = data['summary']
        assert summary['requirements'] == 4
        assert summary['releasable'] == 0
        assert summary['uncovered'] == 1
        assert summary['missed_by_test_plan'] == 2  # REQ-2 and uncovered REQ-3
        assert summary['plan_tests_without_requirement'] == 1
        assert summary['test_status_counts'] == {'PASS': 1, 'FAIL': 1, 'ABORTED': 1, 'TODO': 1}

        # Non-releasable first, then by key
        assert [r['releasable'] for r in data['requirements']] == [False, False, False, False]

    @patch('scripts.xray_release_report.get_jira_client')
    def test_releasable_requirement(self, mock_get_client):
        client, router = _client(mock_get_client)
        router.add('/rest/api/2/search', _search([
            _req('REQ-1', 'Login', links=[_link('T-1'), _link('T-2')]),
        ]), when=_jql_contains('testPlanRequirements'))
        router.add('/rest/raven/1.0/api/testplan/TP-1/test', [
            {'id': 1, 'key': 'T-1', 'latestStatus': 'PASS'},
            {'id': 2, 'key': 'T-2', 'latestStatus': 'PASS'},
        ])
        router.add('/rest/raven/1.0/api/testplan/TP-1/testexecution', [
            {'id': 10, 'key': 'TE-1', 'archived': False},
        ])
        router.add('/rest/raven/1.0/api/testexec/TE-1/test', [
            {'id': 1, 'key': 'T-1', 'status': 'PASS'},
            {'id': 2, 'key': 'T-2', 'status': 'PASS'},
        ])
        data = json.loads(xray_release_report(test_plan_key='TP-1'))
        req = data['requirements'][0]
        assert req['releasable'] is True
        assert req['blockers'] == []
        assert req['warnings'] == []
        assert data['summary']['releasable'] == 1
        assert data['summary']['missed_by_test_plan'] == 0


class TestReleaseReportRules:

    def _setup(self, mock_get_client, statuses):
        client, router = _client(mock_get_client)
        router.add('/rest/api/2/search', _search([
            _req('REQ-1', 'Login', links=[_link(k) for k in statuses]),
        ]), when=_jql_contains('testPlanRequirements'))
        router.add('/rest/raven/1.0/api/testplan/TP-1/test', [
            {'id': i, 'key': k, 'latestStatus': s} for i, (k, s) in enumerate(statuses.items())
        ])
        router.add('/rest/raven/1.0/api/testplan/TP-1/testexecution', [])
        return router

    @patch('scripts.xray_release_report.get_jira_client')
    def test_no_fail_rule_warns_on_todo(self, mock_get_client):
        self._setup(mock_get_client, {'T-1': 'PASS', 'T-2': 'TODO'})
        data = json.loads(xray_release_report(test_plan_key='TP-1', rule='no_fail'))
        req = data['requirements'][0]
        assert req['releasable'] is True
        assert req['warnings'] == ['T-2 is TODO']

    @patch('scripts.xray_release_report.get_jira_client')
    def test_no_fail_rule_blocks_on_fail(self, mock_get_client):
        self._setup(mock_get_client, {'T-1': 'PASS', 'T-2': 'FAIL'})
        data = json.loads(xray_release_report(test_plan_key='TP-1', rule='no_fail'))
        assert data['requirements'][0]['blockers'] == ['T-2 is FAIL']

    @patch('scripts.xray_release_report.get_jira_client')
    def test_custom_passing_statuses(self, mock_get_client):
        self._setup(mock_get_client, {'T-1': 'PASS', 'T-2': 'PASSED WITH REMARKS'})
        data = json.loads(xray_release_report(
            test_plan_key='TP-1', passing_statuses='PASS, passed with remarks'
        ))
        assert data['requirements'][0]['releasable'] is True

    @patch('scripts.xray_release_report.get_jira_client')
    def test_invalid_rule(self, mock_get_client):
        _client(mock_get_client)
        assert json.loads(xray_release_report(test_plan_key='TP-1', rule='x'))['error_type'] == 'ValidationError'

    @patch('scripts.xray_release_report.get_jira_client')
    def test_requires_scope(self, mock_get_client):
        _client(mock_get_client)
        assert json.loads(xray_release_report())['error_type'] == 'ValidationError'


class TestReleaseReportVersionOnly:

    @patch('scripts.xray_release_report.get_jira_client')
    def test_version_only_uses_test_runs(self, mock_get_client):
        client, router = _client(mock_get_client)
        router.add('/rest/api/2/search', _search([
            _req('REQ-1', 'Login', links=[_link('T-1'), _link('T-1')]),  # duplicate link
        ]), when=_jql_contains('fixVersion = "1.0"'))
        router.add('/rest/raven/1.0/api/test/T-1/testruns', [
            {'id': 1, 'status': 'PASS', 'testExecKey': 'TE-1', 'finishedOn': '2024-01-01T10:00:00+00:00'},
        ])
        data = json.loads(xray_release_report(fix_version='1.0'))
        req = data['requirements'][0]
        assert req['releasable'] is True
        assert req['in_test_plan'] is False
        assert req['warnings'] == []  # no plan given, so no "missed" warning
        assert data['summary']['missed_by_test_plan'] == 0
        assert data['summary']['tests_evaluated'] == 1
        # Only one lookup despite the duplicate link
        assert sum(1 for p, _ in router.calls if p.endswith('/testruns')) == 1

    @patch('scripts.xray_release_report.get_jira_client')
    def test_no_lookup_outside_plan(self, mock_get_client):
        client, router = _client(mock_get_client)
        router.add('/rest/api/2/search', _search([
            _req('REQ-1', 'Login', links=[_link('T-1')]),
        ]), when=_jql_contains('fixVersion'))
        data = json.loads(xray_release_report(fix_version='1.0', lookup_runs_outside_plan=False))
        assert data['requirements'][0]['tests'][0]['status'] == 'NOT EXECUTED'
        assert data['requirements'][0]['blockers'] == ['T-1 is NOT EXECUTED']

    @patch('scripts.xray_release_report.get_jira_client')
    def test_custom_requirement_jql_and_link_type(self, mock_get_client):
        client, router = _client(mock_get_client)
        router.add('/rest/api/2/search', _search([
            _req('REQ-1', 'Login', links=[_link('T-1', link_type='Coverage'), _link('T-2', link_type='Blocks')]),
        ]), when=_jql_contains('labels = release'))
        router.add('/rest/raven/1.0/api/test/T-1/testruns', [])
        data = json.loads(xray_release_report(
            requirement_jql='labels = release', coverage_link_type='coverage'
        ))
        tests = data['requirements'][0]['tests']
        assert [t['key'] for t in tests] == ['T-1']
        assert tests[0]['status'] == 'NOT EXECUTED'
