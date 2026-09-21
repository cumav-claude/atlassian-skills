"""Xray requirement coverage tools (Xray for Jira Data Center / Server).

These build on the JQL functions Xray registers in Jira, so they go through the
regular Jira search endpoint.

Tools:
    - xray_get_requirement_tests: Tests covering a requirement
    - xray_get_test_requirements: Requirements covered by a test
    - xray_get_test_plan_requirements: Requirements covered by the tests of a plan
    - xray_get_requirements_by_status: Requirements with a coverage status (OK, NOK, NOTRUN, UNCOVERED)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from typing import Any, Dict, List, Optional

from _common import (
    AtlassianCredentials,
    get_jira_client,
    search_all_issues,
    simplify_issue,
    skill_function,
    ValidationError,
)

COVERAGE_STATUSES = ('OK', 'NOK', 'NOTRUN', 'UNCOVERED', 'UNKNOWN')
_ISSUE_FIELDS = 'summary,status,issuetype,priority,assignee,reporter,created,updated,labels,components,fixVersions'


def _jql_string(value: str) -> str:
    """Quote a value for use inside a JQL function argument."""
    return '"' + value.replace('"', '\\"') + '"'


def _simplify_with_versions(issue: Dict[str, Any]) -> Dict[str, Any]:
    simplified = simplify_issue(issue)
    simplified.pop('custom_fields', None)
    versions = issue.get('fields', {}).get('fixVersions', []) or []
    simplified['fix_versions'] = [v.get('name', '') for v in versions]
    return simplified


def _run_search(client: Any, jql: str, max_issues: int) -> Dict[str, Any]:
    issues = search_all_issues(client, jql, _ISSUE_FIELDS, max_issues=max_issues)
    simplified = [_simplify_with_versions(i) for i in issues]
    return {'jql': jql, 'issues': simplified, 'count': len(simplified)}


@skill_function
def xray_get_requirement_tests(
    requirement_key: str,
    max_issues: int = 500,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the tests that cover a requirement (story, bug, epic, ...).

    Args:
        requirement_key: Requirement issue key (e.g., 'PROJ-42')
        max_issues: Upper bound on returned tests (default: 500)
        credentials: Optional AtlassianCredentials for Agent environments
    """
    client = get_jira_client(credentials)
    if not requirement_key:
        raise ValidationError('requirement_key is required')
    jql = f'issue in requirementTests({_jql_string(requirement_key)})'
    result = _run_search(client, jql, max_issues)
    result['requirement_key'] = requirement_key
    return result


@skill_function
def xray_get_test_requirements(
    test_key: str,
    max_issues: int = 500,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the requirements covered by a test."""
    client = get_jira_client(credentials)
    if not test_key:
        raise ValidationError('test_key is required')
    jql = f'issue in testRequirements({_jql_string(test_key)})'
    result = _run_search(client, jql, max_issues)
    result['test_key'] = test_key
    return result


@skill_function
def xray_get_test_plan_requirements(
    test_plan_key: str,
    max_issues: int = 1000,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get the requirements covered by the tests in a test plan."""
    client = get_jira_client(credentials)
    if not test_plan_key:
        raise ValidationError('test_plan_key is required')
    jql = f'issue in testPlanRequirements({_jql_string(test_plan_key)})'
    result = _run_search(client, jql, max_issues)
    result['test_plan_key'] = test_plan_key
    return result


@skill_function
def xray_get_requirements_by_status(
    status: str,
    project_key: Optional[str] = None,
    version: Optional[str] = None,
    test_plan_key: Optional[str] = None,
    test_environment: Optional[str] = None,
    max_issues: int = 1000,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Get requirements with a given Xray coverage status.

    Uses the Xray JQL function requirements(status, project, version, environment),
    or requirementsWithStatusByTestPlan(status, plan, environment) when a
    test plan key is given.

    Args:
        status: Coverage status: OK, NOK, NOTRUN, UNCOVERED, or UNKNOWN
        project_key: Restrict to a project (optional)
        version: Fix version name to evaluate coverage against (optional)
        test_plan_key: Evaluate coverage within this test plan (optional)
        test_environment: Test environment name (optional)
        max_issues: Upper bound on returned requirements (default: 1000)
        credentials: Optional AtlassianCredentials for Agent environments
    """
    client = get_jira_client(credentials)
    status_upper = (status or '').upper()
    if status_upper not in COVERAGE_STATUSES:
        raise ValidationError(f'status must be one of {", ".join(COVERAGE_STATUSES)}')

    if test_plan_key:
        args: List[str] = [_jql_string(status_upper), _jql_string(test_plan_key)]
        if test_environment:
            args.append(_jql_string(test_environment))
        jql = f'issue in requirementsWithStatusByTestPlan({", ".join(args)})'
        if project_key:
            jql += f' AND project = {_jql_string(project_key)}'
    else:
        args = [_jql_string(status_upper)]
        if project_key or version or test_environment:
            args.append(_jql_string(project_key) if project_key else '""')
        if version or test_environment:
            args.append(_jql_string(version) if version else '""')
        if test_environment:
            args.append(_jql_string(test_environment))
        jql = f'issue in requirements({", ".join(args)})'

    result = _run_search(client, jql, max_issues)
    result['coverage_status'] = status_upper
    return result
