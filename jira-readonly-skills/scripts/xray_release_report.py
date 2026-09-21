"""Release readiness report built on Xray (Jira Data Center / Server).

Tools:
    - xray_release_report: Per-requirement release verdict with covering tests nested

Scope is a Test Plan, a fixVersion, or both. With both, requirements that carry
the fixVersion but are not covered by any test in the plan are flagged as
missed by the plan.
"""

import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from typing import Any, Dict, List, Optional, Set, Tuple

from _common import (
    AtlassianCredentials,
    get_jira_client,
    paginate_xray,
    search_all_issues,
    skill_function,
    ValidationError,
)
from xray_plans import get_plan_tests, get_plan_executions
from xray_tests import _simplify_defect

RULES = ('all_pass', 'no_fail')

# Issue types Xray creates; never treated as requirements
XRAY_ISSUE_TYPES = {
    'test', 'test set', 'test plan', 'test execution',
    'pre-condition', 'precondition', 'sub test execution', 'sub-test execution',
}

NOT_EXECUTED = 'NOT EXECUTED'
_REQ_FIELDS = 'summary,status,issuetype,priority,fixVersions,issuelinks'


def _jql_string(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def _parse_timestamp(value: Any) -> float:
    """Best-effort parse of an Xray date string into a sortable number."""
    if not value or not isinstance(value, str):
        return 0.0
    text = value.strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    # Normalize "+0000" to "+00:00" for fromisoformat
    if len(text) >= 5 and text[-5] in '+-' and text[-4:].isdigit():
        text = text[:-2] + ':' + text[-2:]
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0


def _run_sort_key(run: Dict[str, Any]) -> Tuple[float, float, int]:
    try:
        run_id = int(run.get('run_id') or 0)
    except (TypeError, ValueError):
        run_id = 0
    return (
        _parse_timestamp(run.get('finished_on')),
        _parse_timestamp(run.get('started_on')),
        run_id,
    )


def _newer(current: Optional[Dict[str, Any]], candidate: Dict[str, Any]) -> Dict[str, Any]:
    if current is None:
        return candidate
    return candidate if _run_sort_key(candidate) > _run_sort_key(current) else current


def _run_from_execution(exec_key: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'run_id': raw.get('id', ''),
        'status': raw.get('status', '') or NOT_EXECUTED,
        'execution_key': exec_key,
        'executed_by': raw.get('executedBy', ''),
        'started_on': raw.get('startedOn', ''),
        'finished_on': raw.get('finishedOn', ''),
        'defects': [_simplify_defect(d) for d in raw.get('defects', []) or []],
    }


def _run_from_test_runs(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'run_id': raw.get('id', ''),
        'status': raw.get('status', '') or NOT_EXECUTED,
        'execution_key': raw.get('testExecKey', ''),
        'executed_by': raw.get('executedBy', ''),
        'started_on': raw.get('startedOn', ''),
        'finished_on': raw.get('finishedOn', ''),
        'defects': [_simplify_defect(d) for d in raw.get('defects', []) or []],
    }


def _no_run(status: str = NOT_EXECUTED) -> Dict[str, Any]:
    return {
        'run_id': '',
        'status': status,
        'execution_key': '',
        'executed_by': '',
        'started_on': '',
        'finished_on': '',
        'defects': [],
    }


def _is_xray_type(issue: Dict[str, Any]) -> bool:
    name = (issue.get('fields', {}).get('issuetype') or {}).get('name', '')
    return name.strip().lower() in XRAY_ISSUE_TYPES


def _covering_tests(issue: Dict[str, Any], link_type: str) -> List[Dict[str, Any]]:
    """Tests linked to a requirement through the Xray coverage issue link type."""
    tests: List[Dict[str, Any]] = []
    wanted = link_type.strip().lower()
    for link in issue.get('fields', {}).get('issuelinks', []) or []:
        type_name = (link.get('type') or {}).get('name', '').strip().lower()
        if type_name != wanted:
            continue
        linked = link.get('inwardIssue') or link.get('outwardIssue') or {}
        if not linked.get('key'):
            continue
        linked_fields = linked.get('fields', {}) or {}
        linked_type = (linked_fields.get('issuetype') or {}).get('name', '')
        if linked_type and linked_type.strip().lower() != 'test':
            continue
        tests.append({
            'key': linked['key'],
            'summary': linked_fields.get('summary', ''),
        })
    tests.sort(key=lambda t: t['key'])
    return tests


def _collect_requirements(
    client: Any,
    test_plan_key: Optional[str],
    fix_version: Optional[str],
    project_key: Optional[str],
    requirement_jql: Optional[str],
    max_requirements: int,
) -> Dict[str, Dict[str, Any]]:
    """Return requirement key -> {issue, in_release_scope, in_test_plan}."""
    requirements: Dict[str, Dict[str, Any]] = {}

    def add(issues: List[Dict[str, Any]], flag: str) -> None:
        for issue in issues:
            if _is_xray_type(issue):
                continue
            entry = requirements.setdefault(issue['key'], {
                'issue': issue, 'in_release_scope': False, 'in_test_plan': False
            })
            entry[flag] = True

    scope_jql = requirement_jql
    if not scope_jql and fix_version:
        scope_jql = f'fixVersion = {_jql_string(fix_version)}'
        if project_key:
            scope_jql += f' AND project = {_jql_string(project_key)}'
    if scope_jql:
        add(search_all_issues(client, scope_jql, _REQ_FIELDS, max_issues=max_requirements), 'in_release_scope')

    if test_plan_key:
        plan_jql = f'issue in testPlanRequirements({_jql_string(test_plan_key)})'
        if project_key:
            plan_jql += f' AND project = {_jql_string(project_key)}'
        add(search_all_issues(client, plan_jql, _REQ_FIELDS, max_issues=max_requirements), 'in_test_plan')

    return requirements


def _collect_plan_runs(
    client: Any,
    test_plan_key: str,
    include_archived: bool,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """Latest run per test across the plan's executions, plus the plan's latest statuses."""
    plan_status: Dict[str, str] = {
        t['key']: t['latest_status'] for t in get_plan_tests(client, test_plan_key)
    }
    latest: Dict[str, Dict[str, Any]] = {}
    for execution in get_plan_executions(client, test_plan_key):
        if execution['archived'] and not include_archived:
            continue
        raw_runs = paginate_xray(
            client,
            client.xray_path(f"testexec/{execution['key']}/test"),
            params={'detailed': 'true'},
        )
        for raw in raw_runs:
            key = raw.get('key')
            if not key:
                continue
            latest[key] = _newer(latest.get(key), _run_from_execution(execution['key'], raw))
    return latest, plan_status


def _latest_run_outside_plan(client: Any, test_key: str) -> Dict[str, Any]:
    raw_runs = client.get(client.xray_path(f'test/{test_key}/testruns')) or []
    latest: Optional[Dict[str, Any]] = None
    for raw in raw_runs:
        latest = _newer(latest, _run_from_test_runs(raw))
    return latest or _no_run()


def _verdict(
    tests: List[Dict[str, Any]],
    rule: str,
    passing: Set[str],
    failing: Set[str],
) -> Tuple[bool, List[str], List[str]]:
    blockers: List[str] = []
    warnings: List[str] = []
    if not tests:
        return False, ['UNCOVERED: no tests linked'], warnings
    for test in tests:
        status = (test['status'] or NOT_EXECUTED).upper()
        if status in passing:
            continue
        message = f"{test['key']} is {status}"
        if rule == 'all_pass':
            blockers.append(message)
        elif status in failing:
            blockers.append(message)
        else:
            warnings.append(message)
    return not blockers, blockers, warnings


@skill_function
def xray_release_report(
    test_plan_key: Optional[str] = None,
    fix_version: Optional[str] = None,
    project_key: Optional[str] = None,
    requirement_jql: Optional[str] = None,
    rule: str = 'all_pass',
    passing_statuses: str = 'PASS',
    failing_statuses: str = 'FAIL',
    coverage_link_type: str = 'Tests',
    include_archived_executions: bool = False,
    lookup_runs_outside_plan: bool = True,
    max_requirements: int = 500,
    credentials: Optional[AtlassianCredentials] = None
) -> Dict[str, Any]:
    """Build a release readiness report: which requirements can ship and which cannot.

    Scope is a test plan, a fixVersion (optionally restricted to a project), a
    custom requirement JQL, or a combination. With a test plan plus a
    fixVersion, requirements with the fixVersion that no plan test covers are
    flagged as missed by the plan.

    Args:
        test_plan_key: Test Plan issue key. Test statuses come from the plan's executions.
        fix_version: Fix version name whose issues are the requirements in scope.
        project_key: Restrict fixVersion / plan requirement lookups to this project.
        requirement_jql: Custom JQL selecting the requirements in scope (overrides fix_version).
        rule: 'all_pass' (default): every covering test must be in passing_statuses.
              'no_fail': no covering test may be in failing_statuses; other statuses only warn.
        passing_statuses: Comma-separated statuses that count as passed (default: 'PASS').
        failing_statuses: Comma-separated statuses that count as failed (default: 'FAIL').
        coverage_link_type: Jira issue link type Xray uses for coverage (default: 'Tests').
        include_archived_executions: Consider archived executions of the plan (default: False).
        lookup_runs_outside_plan: For tests not in the plan, fetch their latest run anywhere
                                  (one request per test). Default: True.
        max_requirements: Upper bound on requirements per scope query (default: 500).
        credentials: Optional AtlassianCredentials for Agent environments.

    Returns:
        JSON string with scope, summary counts, requirements (verdict, blockers, tests nested),
        and tests in the plan that cover no requirement in scope.
    """
    client = get_jira_client(credentials)

    if not (test_plan_key or fix_version or requirement_jql):
        raise ValidationError('Provide test_plan_key, fix_version, or requirement_jql')
    if rule not in RULES:
        raise ValidationError(f"rule must be one of {', '.join(RULES)}")

    passing = {s.strip().upper() for s in passing_statuses.split(',') if s.strip()}
    failing = {s.strip().upper() for s in failing_statuses.split(',') if s.strip()}

    requirements = _collect_requirements(
        client, test_plan_key, fix_version, project_key, requirement_jql, max_requirements
    )

    plan_runs: Dict[str, Dict[str, Any]] = {}
    plan_status: Dict[str, str] = {}
    if test_plan_key:
        plan_runs, plan_status = _collect_plan_runs(client, test_plan_key, include_archived_executions)
    plan_test_keys = set(plan_status)

    run_cache: Dict[str, Dict[str, Any]] = {}

    def run_for(test_key: str) -> Tuple[Dict[str, Any], bool]:
        in_plan = test_key in plan_test_keys
        if test_key in run_cache:
            return run_cache[test_key], in_plan
        if in_plan:
            run = plan_runs.get(test_key) or _no_run(plan_status.get(test_key) or NOT_EXECUTED)
        elif lookup_runs_outside_plan:
            run = _latest_run_outside_plan(client, test_key)
        else:
            run = _no_run()
        run_cache[test_key] = run
        return run, in_plan

    report_requirements: List[Dict[str, Any]] = []
    covered_test_keys: Set[str] = set()
    status_counts: Dict[str, int] = {}

    for key in sorted(requirements):
        entry = requirements[key]
        fields = entry['issue'].get('fields', {})
        tests: List[Dict[str, Any]] = []
        for linked in _covering_tests(entry['issue'], coverage_link_type):
            run, in_plan = run_for(linked['key'])
            covered_test_keys.add(linked['key'])
            tests.append({
                'key': linked['key'],
                'summary': linked['summary'],
                'status': run['status'],
                'in_test_plan': in_plan,
                'execution_key': run['execution_key'],
                'executed_by': run['executed_by'],
                'finished_on': run['finished_on'],
                'defects': run['defects'],
            })

        releasable, blockers, warnings = _verdict(tests, rule, passing, failing)
        if test_plan_key and entry['in_release_scope'] and not entry['in_test_plan']:
            warnings.insert(0, 'MISSED BY TEST PLAN: no test in the plan covers this requirement')

        report_requirements.append({
            'key': key,
            'summary': fields.get('summary', ''),
            'issue_type': (fields.get('issuetype') or {}).get('name', ''),
            'status': (fields.get('status') or {}).get('name', ''),
            'priority': (fields.get('priority') or {}).get('name', ''),
            'fix_versions': [v.get('name', '') for v in fields.get('fixVersions', []) or []],
            'in_release_scope': entry['in_release_scope'],
            'in_test_plan': entry['in_test_plan'],
            'releasable': releasable,
            'blockers': blockers,
            'warnings': warnings,
            'tests': tests,
        })

    for test_key, run in run_cache.items():
        status = run['status'] or NOT_EXECUTED
        status_counts[status] = status_counts.get(status, 0) + 1

    tests_without_requirement: List[Dict[str, Any]] = []
    for test_key in sorted(plan_test_keys - covered_test_keys):
        run = plan_runs.get(test_key) or _no_run(plan_status.get(test_key) or NOT_EXECUTED)
        tests_without_requirement.append({
            'key': test_key,
            'status': run['status'],
            'execution_key': run['execution_key'],
            'executed_by': run['executed_by'],
            'defects': run['defects'],
        })

    report_requirements.sort(key=lambda r: (r['releasable'], r['key']))

    releasable_count = sum(1 for r in report_requirements if r['releasable'])
    return {
        'scope': {
            'test_plan_key': test_plan_key,
            'fix_version': fix_version,
            'project_key': project_key,
            'requirement_jql': requirement_jql,
            'rule': rule,
            'passing_statuses': sorted(passing),
            'failing_statuses': sorted(failing),
        },
        'summary': {
            'requirements': len(report_requirements),
            'releasable': releasable_count,
            'not_releasable': len(report_requirements) - releasable_count,
            'uncovered': sum(1 for r in report_requirements if not r['tests']),
            'missed_by_test_plan': sum(
                1 for r in report_requirements if r['in_release_scope'] and not r['in_test_plan']
            ) if test_plan_key else 0,
            'tests_evaluated': len(run_cache),
            'test_status_counts': status_counts,
            'plan_tests_without_requirement': len(tests_without_requirement),
        },
        'requirements': report_requirements,
        'tests_without_requirement': tests_without_requirement,
    }
