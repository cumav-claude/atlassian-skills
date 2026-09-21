"""Xray test tools (Xray for Jira Data Center / Server).

Tools:
    - xray_get_tests: Export tests by keys, JQL, or saved filter
    - xray_get_test_steps: Get the manual step definitions of a test
    - xray_get_test_preconditions: Get pre-conditions linked to a test
    - xray_get_test_sets: Get test sets containing a test
    - xray_get_test_plans: Get test plans containing a test
    - xray_get_test_executions: Get test executions containing a test
    - xray_get_test_runs: Get all runs of a test across executions
    - xray_get_test_set_tests: Get tests in a test set
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from typing import Any, Dict, List, Optional

from _common import (
    AtlassianCredentials,
    get_jira_client,
    paginate_xray,
    skill_function,
    ValidationError,
)


def _text(value: Any) -> str:
    """Extract the raw text from an Xray {raw, rendered} object or plain string."""
    if isinstance(value, dict):
        return value.get('raw', '') or ''
    return value or ''


def _simplify_defect(defect: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': defect.get('id', ''),
        'key': defect.get('key', ''),
        'summary': defect.get('summary', ''),
        'status': defect.get('status', ''),
    }


def simplify_test_run(run: Dict[str, Any]) -> Dict[str, Any]:
    """Simplify a test run (as returned by /test/{key}/testruns or /testrun)."""
    return {
        'id': run.get('id', ''),
        'test_key': run.get('testKey', ''),
        'test_exec_key': run.get('testExecKey', ''),
        'status': run.get('status', ''),
        'assignee': run.get('assignee', ''),
        'executed_by': run.get('executedBy', ''),
        'started_on': run.get('startedOn', ''),
        'finished_on': run.get('finishedOn', ''),
        'duration': run.get('duration', ''),
        'comment': _text(run.get('comment', '')),
        'environments': run.get('environments', run.get('testEnvironments', [])) or [],
        'defects': [_simplify_defect(d) for d in run.get('defects', []) or []],
        'evidence_count': len(run.get('evidences', []) or []),
    }


def _simplify_test(test: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'key': test.get('key', ''),
        'type': test.get('type', ''),
        'status': test.get('status', ''),
        'reporter': test.get('reporter', ''),
        'assignee': test.get('assignee', ''),
        'precondition': test.get('precondition', ''),
        'definition': test.get('definition', ''),
    }


def _simplify_step(step: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': step.get('id', ''),
        'index': step.get('index', ''),
        'step': _text(step.get('step')),
        'data': _text(step.get('data')),
        'result': _text(step.get('result')),
        'attachment_count': len(step.get('attachments', []) or []),
    }


def _simplify_linked_issue(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': item.get('id', ''),
        'key': item.get('key', ''),
        'summary': item.get('summary', ''),
    }


@skill_function
def xray_get_tests(
    keys: Optional[str] = None,
    jql: Optional[str] = None,
    filter_id: Optional[int] = None,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Export Xray tests by keys, JQL, or saved filter.

    Args:
        keys: Semicolon- or comma-separated test keys (e.g., 'TEST-1;TEST-2')
        jql: JQL selecting test issues
        filter_id: Saved filter ID selecting test issues
        credentials: Optional AtlassianCredentials for Agent environments

    Returns:
        JSON string with list of tests (type, status, definition) or error
    """
    client = get_jira_client(credentials)
    if not (keys or jql or filter_id):
        raise ValidationError('One of keys, jql, or filter_id is required')

    params: Dict[str, Any] = {}
    if keys:
        params['keys'] = keys.replace(',', ';')
    if jql:
        params['jql'] = jql
    if filter_id:
        params['filter'] = filter_id

    response = client.get(client.xray_path('test'), params=params)
    tests = [_simplify_test(t) for t in (response or [])]
    return {'tests': tests, 'count': len(tests)}


@skill_function
def xray_get_test_steps(
    test_key: str,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the manual step definitions of an Xray test.

    Args:
        test_key: Test issue key (e.g., 'TEST-1')
        credentials: Optional AtlassianCredentials for Agent environments

    Returns:
        JSON string with ordered steps (step, data, expected result) or error
    """
    client = get_jira_client(credentials)
    if not test_key:
        raise ValidationError('test_key is required')

    response = client.get(client.xray_path(f'test/{test_key}/step'))
    steps = [_simplify_step(s) for s in (response or [])]
    return {'test_key': test_key, 'steps': steps, 'count': len(steps)}


@skill_function
def xray_get_test_preconditions(
    test_key: str,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get pre-conditions linked to an Xray test."""
    client = get_jira_client(credentials)
    if not test_key:
        raise ValidationError('test_key is required')

    response = client.get(client.xray_path(f'test/{test_key}/preconditions'))
    preconditions = [
        {
            'key': p.get('key', ''),
            'type': p.get('type', ''),
            'condition': _text(p.get('condition')),
        }
        for p in (response or [])
    ]
    return {'test_key': test_key, 'preconditions': preconditions, 'count': len(preconditions)}


@skill_function
def xray_get_test_sets(
    test_key: str,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the test sets that contain an Xray test."""
    client = get_jira_client(credentials)
    if not test_key:
        raise ValidationError('test_key is required')

    response = client.get(client.xray_path(f'test/{test_key}/testsets'))
    test_sets = [_simplify_linked_issue(i) for i in (response or [])]
    return {'test_key': test_key, 'test_sets': test_sets, 'count': len(test_sets)}


@skill_function
def xray_get_test_plans(
    test_key: str,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the test plans that contain an Xray test."""
    client = get_jira_client(credentials)
    if not test_key:
        raise ValidationError('test_key is required')

    response = client.get(client.xray_path(f'test/{test_key}/testplans'))
    test_plans = [_simplify_linked_issue(i) for i in (response or [])]
    return {'test_key': test_key, 'test_plans': test_plans, 'count': len(test_plans)}


@skill_function
def xray_get_test_executions(
    test_key: str,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the test executions that contain an Xray test."""
    client = get_jira_client(credentials)
    if not test_key:
        raise ValidationError('test_key is required')

    response = client.get(client.xray_path(f'test/{test_key}/testexecutions'))
    executions = [_simplify_linked_issue(i) for i in (response or [])]
    return {'test_key': test_key, 'test_executions': executions, 'count': len(executions)}


@skill_function
def xray_get_test_runs(
    test_key: str,
    test_environments: Optional[str] = None,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get all runs of an Xray test across its test executions.

    Args:
        test_key: Test issue key
        test_environments: Comma-separated environment names to filter by (optional)
        credentials: Optional AtlassianCredentials for Agent environments

    Returns:
        JSON string with runs (status, execution key, executed by, defects) or error
    """
    client = get_jira_client(credentials)
    if not test_key:
        raise ValidationError('test_key is required')

    params: Dict[str, Any] = {}
    if test_environments:
        params['testEnvironments'] = test_environments

    response = client.get(client.xray_path(f'test/{test_key}/testruns'), params=params)
    runs = [simplify_test_run(r) for r in (response or [])]
    return {'test_key': test_key, 'runs': runs, 'count': len(runs)}


@skill_function
def xray_get_test_set_tests(
    test_set_key: str,
    limit: Optional[int] = None,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the tests in an Xray test set.

    Args:
        test_set_key: Test Set issue key
        limit: Maximum number of tests to return (default: all)
        credentials: Optional AtlassianCredentials for Agent environments
    """
    client = get_jira_client(credentials)
    if not test_set_key:
        raise ValidationError('test_set_key is required')

    items = paginate_xray(
        client,
        client.xray_path(f'testset/{test_set_key}/test'),
        params={'testDefinition': 'false'},
        max_items=limit
    )
    tests: List[Dict[str, Any]] = [
        {'id': t.get('id', ''), 'key': t.get('key', ''), 'rank': t.get('rank', '')}
        for t in items
    ]
    return {'test_set_key': test_set_key, 'tests': tests, 'count': len(tests)}
