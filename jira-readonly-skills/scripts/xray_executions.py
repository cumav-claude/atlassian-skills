"""Xray test execution and test run tools (Xray for Jira Data Center / Server).

Tools:
    - xray_get_test_execution_tests: Tests in a test execution with their run status
    - xray_get_test_run: Details of one test run (by run ID, or execution + test key)
    - xray_get_test_run_steps: Step-level results of a test run
    - xray_get_test_statuses: Configured test run statuses
    - xray_get_test_step_statuses: Configured test step statuses
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
from xray_tests import simplify_test_run, _text, _simplify_defect


def simplify_execution_run(run: Dict[str, Any]) -> Dict[str, Any]:
    """Simplify a run entry from /testexec/{key}/test."""
    return {
        'run_id': run.get('id', ''),
        'test_key': run.get('key', ''),
        'rank': run.get('rank', ''),
        'status': run.get('status', ''),
        'assignee': run.get('assignee', ''),
        'executed_by': run.get('executedBy', ''),
        'started_on': run.get('startedOn', ''),
        'finished_on': run.get('finishedOn', ''),
        'defects': [_simplify_defect(d) for d in run.get('defects', []) or []],
        'evidence_count': len(run.get('evidences', []) or []),
    }


def _simplify_run_step(step: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': step.get('id', ''),
        'index': step.get('index', ''),
        'status': step.get('status', ''),
        'step': _text(step.get('step')),
        'data': _text(step.get('data')),
        'expected_result': _text(step.get('result')),
        'actual_result': _text(step.get('actualResult')),
        'comment': _text(step.get('comment')),
        'defects': [_simplify_defect(d) for d in step.get('defects', []) or []],
        'evidence_count': len(step.get('evidences', []) or []),
    }


@skill_function
def xray_get_test_execution_tests(
    test_exec_key: str,
    detailed: bool = True,
    limit: Optional[int] = None,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the tests in a test execution with their run status.

    Args:
        test_exec_key: Test Execution issue key (e.g., 'TE-5')
        detailed: Include executed by, dates, defects, evidence (default: True)
        limit: Maximum number of tests to return (default: all)
        credentials: Optional AtlassianCredentials for Agent environments

    Returns:
        JSON string with runs and a status count summary or error
    """
    client = get_jira_client(credentials)
    if not test_exec_key:
        raise ValidationError('test_exec_key is required')

    items = paginate_xray(
        client,
        client.xray_path(f'testexec/{test_exec_key}/test'),
        params={'detailed': 'true' if detailed else 'false'},
        max_items=limit
    )
    runs = [simplify_execution_run(r) for r in items]

    status_counts: Dict[str, int] = {}
    for run in runs:
        status = run['status'] or 'UNKNOWN'
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        'test_exec_key': test_exec_key,
        'runs': runs,
        'count': len(runs),
        'status_counts': status_counts,
    }


@skill_function
def xray_get_test_run(
    run_id: Optional[int] = None,
    test_exec_key: Optional[str] = None,
    test_key: Optional[str] = None,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get one test run, by run ID or by test execution key plus test key.

    Args:
        run_id: Numeric test run ID
        test_exec_key: Test Execution issue key (used together with test_key)
        test_key: Test issue key (used together with test_exec_key)
        credentials: Optional AtlassianCredentials for Agent environments

    Returns:
        JSON string with run details (status, executed by, defects, comment) or error
    """
    client = get_jira_client(credentials)

    if run_id is not None:
        response = client.get(client.xray_path(f'testrun/{run_id}'))
    elif test_exec_key and test_key:
        response = client.get(
            client.xray_path('testrun'),
            params={'testExecIssueKey': test_exec_key, 'testIssueKey': test_key}
        )
    else:
        raise ValidationError('Provide run_id, or both test_exec_key and test_key')

    return simplify_test_run(response or {})


@skill_function
def xray_get_test_run_steps(
    run_id: int,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the step-level results of a test run.

    Args:
        run_id: Numeric test run ID
        credentials: Optional AtlassianCredentials for Agent environments

    Returns:
        JSON string with steps (status, actual result, defects) or error
    """
    client = get_jira_client(credentials)
    if run_id is None:
        raise ValidationError('run_id is required')

    response = client.get(client.xray_path(f'testrun/{run_id}/step'))
    steps: List[Dict[str, Any]] = [_simplify_run_step(s) for s in (response or [])]
    return {'run_id': run_id, 'steps': steps, 'count': len(steps)}


@skill_function
def xray_get_test_statuses(
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the test run statuses configured in Xray (PASS, FAIL, TODO, custom ones)."""
    client = get_jira_client(credentials)
    response = client.get(client.xray_path('settings/teststatuses'))
    statuses = [
        {
            'id': s.get('id', ''),
            'name': s.get('name', ''),
            'description': s.get('description', ''),
            'final': s.get('final', False),
            'requirement_status': s.get('requirementStatusName', ''),
        }
        for s in (response or [])
    ]
    return {'statuses': statuses, 'count': len(statuses)}


@skill_function
def xray_get_test_step_statuses(
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the test step statuses configured in Xray."""
    client = get_jira_client(credentials)
    response = client.get(client.xray_path('settings/teststepstatuses'))
    statuses = [
        {
            'id': s.get('id', ''),
            'name': s.get('name', ''),
            'description': s.get('description', ''),
            'test_status_id': s.get('testStatusId', ''),
        }
        for s in (response or [])
    ]
    return {'statuses': statuses, 'count': len(statuses)}
