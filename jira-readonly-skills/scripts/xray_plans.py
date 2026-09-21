"""Xray test plan tools (Xray for Jira Data Center / Server).

Tools:
    - xray_get_test_plan_tests: Tests in a test plan with their latest status
    - xray_get_test_plan_executions: Test executions belonging to a test plan
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


def get_plan_tests(client: Any, test_plan_key: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Raw helper: tests in a plan with latest status (used by the release report too)."""
    items = paginate_xray(client, client.xray_path(f'testplan/{test_plan_key}/test'), max_items=limit)
    return [
        {'id': t.get('id', ''), 'key': t.get('key', ''), 'latest_status': t.get('latestStatus', '')}
        for t in items
    ]


def get_plan_executions(client: Any, test_plan_key: str) -> List[Dict[str, Any]]:
    """Raw helper: executions of a plan (used by the release report too)."""
    response = client.get(client.xray_path(f'testplan/{test_plan_key}/testexecution'))
    return [
        {
            'id': e.get('id', ''),
            'key': e.get('key', ''),
            'summary': e.get('summary', ''),
            'environments': e.get('environments', []) or [],
            'archived': e.get('archived', False),
        }
        for e in (response or [])
    ]


@skill_function
def xray_get_test_plan_tests(
    test_plan_key: str,
    limit: Optional[int] = None,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the tests in a test plan with their latest status within the plan.

    Args:
        test_plan_key: Test Plan issue key (e.g., 'TP-1')
        limit: Maximum number of tests to return (default: all)
        credentials: Optional AtlassianCredentials for Agent environments

    Returns:
        JSON string with tests, latest status per test, and status counts or error
    """
    client = get_jira_client(credentials)
    if not test_plan_key:
        raise ValidationError('test_plan_key is required')

    tests = get_plan_tests(client, test_plan_key, limit)

    status_counts: Dict[str, int] = {}
    for test in tests:
        status = test['latest_status'] or 'UNKNOWN'
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        'test_plan_key': test_plan_key,
        'tests': tests,
        'count': len(tests),
        'status_counts': status_counts,
    }


@skill_function
def xray_get_test_plan_executions(
    test_plan_key: str,
    include_archived: bool = False,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the test executions that belong to a test plan.

    Args:
        test_plan_key: Test Plan issue key
        include_archived: Include archived executions (default: False)
        credentials: Optional AtlassianCredentials for Agent environments
    """
    client = get_jira_client(credentials)
    if not test_plan_key:
        raise ValidationError('test_plan_key is required')

    executions = get_plan_executions(client, test_plan_key)
    if not include_archived:
        executions = [e for e in executions if not e['archived']]

    return {
        'test_plan_key': test_plan_key,
        'test_executions': executions,
        'count': len(executions),
    }
