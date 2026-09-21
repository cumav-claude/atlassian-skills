---
name: jira-readonly-skills
description: Read-only Python utilities for Jira Data Center / Server and Xray test management. Provides read access to issues, JQL search, field definitions, workflow transitions, agile boards and sprints, issue link types, worklogs, projects, versions, user profiles, plus Xray tests, steps, test runs, test executions, test plans, requirement coverage, and a release readiness report. Use when users need to query Jira or Xray like "get a Jira issue", "search issues with JQL", "show test execution results", "which requirements are covered", or "can version 2.1 be released". No write operations are exposed.
license: Complete terms in LICENSE
---

# Jira Data Center Readonly Skills

Read-only Python utilities for Jira Data Center / Server and the Xray test management app, authenticated with a Personal Access Token (PAT). Jira calls use the Jira REST API v2, Xray calls use the Xray REST API v1.0 on the same host with the same PAT.

> **Note**: This skill only exposes read operations. It cannot create, update, transition, or delete anything in Jira.

## Configuration

Two configuration modes are supported:

### Mode 1: Environment Variables

Set these environment variables (or put them in a `.env` file next to this `SKILL.md`, see `.env.example`). This mode is used when the `credentials` parameter is not provided to skill functions.

```bash
JIRA_URL=https://jira.your-company.com
JIRA_PAT_TOKEN=your_pat_token
# Optional, defaults to false:
# JIRA_SSL_VERIFY=true
```

Generate a PAT in Jira: Profile → Personal Access Tokens → Create token.

### Mode 2: Parameter-Based (Agent Environments)

When environment variables are not available, pass credentials directly to skill functions using the `AtlassianCredentials` object.

```python
from scripts._common import AtlassianCredentials, check_available_skills
from scripts.jira_issues import jira_get_issue

credentials = AtlassianCredentials(
    jira_url="https://jira.your-company.com",
    jira_pat_token="your_pat_token",
    # jira_ssl_verify=True  (default)
)

# Check that the credentials are complete
availability = check_available_skills(credentials)
print(availability["available_services"])    # ["jira"]
print(availability["unavailable_services"])  # {} or {"jira": "Missing jira_pat_token"}

result = jira_get_issue(issue_key="PROJ-123", credentials=credentials)
```

## Core Workflow

```python
from scripts.jira_issues import jira_get_issue
from scripts.jira_search import jira_search
import json

# 1. Get a Jira issue
result = jira_get_issue(issue_key="PROJ-123")
issue = json.loads(result)
print(f"Issue: {issue['key']} - {issue['summary']}")

# 2. Search for issues
result = jira_search(
    jql="project = PROJ AND status = 'In Progress'",
    fields="summary,status,assignee",
    limit=50
)
issues = json.loads(result)
```

Every function accepts an optional `credentials=` keyword argument for Agent mode.

## Available Utilities

### Jira Issues (`scripts.jira_issues`)

```python
from scripts.jira_issues import jira_get_issue

jira_get_issue(issue_key="PROJ-123", fields=None, expand=None)
```

### Jira Search (`scripts.jira_search`)

```python
from scripts.jira_search import jira_search, jira_search_fields

# Search with JQL (paginated)
jira_search(jql="project = PROJ AND status = 'In Progress'", fields="summary,status,assignee", limit=50, start_at=0)

# Find field definitions (e.g. custom field IDs)
jira_search_fields(keyword="story points", limit=10)
```

### Jira Workflow (`scripts.jira_workflow`)

```python
from scripts.jira_workflow import jira_get_transitions

# Available status transitions for an issue (including required fields)
jira_get_transitions(issue_key="PROJ-123")
```

### Jira Agile (`scripts.jira_agile`)

```python
from scripts.jira_agile import (
    jira_get_agile_boards,
    jira_get_board_issues,
    jira_get_sprints_from_board,
    jira_get_sprint_issues
)

jira_get_agile_boards(board_name=None, project_key="PROJ", board_type=None, start_at=0, limit=50)
jira_get_board_issues(board_id="1", jql="status = 'In Progress'", fields=None, start_at=0, limit=50)
jira_get_sprints_from_board(board_id="1", state="active", start_at=0, limit=50)
jira_get_sprint_issues(sprint_id="42", fields=None, start_at=0, limit=50)
```

### Jira Links (`scripts.jira_links`)

```python
from scripts.jira_links import jira_get_link_types

jira_get_link_types()
```

### Jira Worklog (`scripts.jira_worklog`)

```python
from scripts.jira_worklog import jira_get_worklog

jira_get_worklog(issue_key="PROJ-123")
```

### Jira Projects (`scripts.jira_projects`)

```python
from scripts.jira_projects import (
    jira_get_all_projects,
    jira_get_project_issues,
    jira_get_project_versions
)

jira_get_all_projects(include_archived=False)
jira_get_project_issues(project_key="PROJ", limit=100, start_at=0)
jira_get_project_versions(project_key="PROJ")
```

### Jira Users (`scripts.jira_users`)

```python
from scripts.jira_users import jira_get_user_profile

# Lookup by username, email address, or display name
jira_get_user_profile(user_identifier="jdoe")
```

### Xray Tests (`scripts.xray_tests`)

```python
from scripts.xray_tests import (
    xray_get_tests, xray_get_test_steps, xray_get_test_preconditions,
    xray_get_test_sets, xray_get_test_plans, xray_get_test_executions,
    xray_get_test_runs, xray_get_test_set_tests
)

xray_get_tests(keys="TEST-1,TEST-2")          # or jql="...", or filter_id=123
xray_get_test_steps(test_key="TEST-1")        # manual step definitions
xray_get_test_preconditions(test_key="TEST-1")
xray_get_test_sets(test_key="TEST-1")         # sets containing the test
xray_get_test_plans(test_key="TEST-1")        # plans containing the test
xray_get_test_executions(test_key="TEST-1")   # executions containing the test
xray_get_test_runs(test_key="TEST-1", test_environments=None)  # all runs across executions
xray_get_test_set_tests(test_set_key="TS-1", limit=None)
```

### Xray Executions and Runs (`scripts.xray_executions`)

```python
from scripts.xray_executions import (
    xray_get_test_execution_tests, xray_get_test_run, xray_get_test_run_steps,
    xray_get_test_statuses, xray_get_test_step_statuses
)

# Tests in an execution with status, executed by, dates, defects, plus status counts
xray_get_test_execution_tests(test_exec_key="TE-5", detailed=True, limit=None)

# One run: by run id, or by execution + test
xray_get_test_run(run_id=123)
xray_get_test_run(test_exec_key="TE-5", test_key="TEST-1")

# Step-level results of a run (status, actual result, defects per step)
xray_get_test_run_steps(run_id=123)

# Configured statuses (including custom ones)
xray_get_test_statuses()
xray_get_test_step_statuses()
```

### Xray Test Plans (`scripts.xray_plans`)

```python
from scripts.xray_plans import xray_get_test_plan_tests, xray_get_test_plan_executions

xray_get_test_plan_tests(test_plan_key="TP-1", limit=None)          # latest status per test + counts
xray_get_test_plan_executions(test_plan_key="TP-1", include_archived=False)
```

### Xray Requirement Coverage (`scripts.xray_coverage`)

These use the JQL functions Xray registers in Jira.

```python
from scripts.xray_coverage import (
    xray_get_requirement_tests, xray_get_test_requirements,
    xray_get_test_plan_requirements, xray_get_requirements_by_status
)

xray_get_requirement_tests(requirement_key="PROJ-42")     # tests covering a story
xray_get_test_requirements(test_key="TEST-1")             # stories a test covers
xray_get_test_plan_requirements(test_plan_key="TP-1")     # stories covered by a plan

# Requirements by Xray coverage status: OK, NOK, NOTRUN, UNCOVERED, UNKNOWN
xray_get_requirements_by_status(status="NOK", project_key="PROJ", version="2.1")
xray_get_requirements_by_status(status="UNCOVERED", test_plan_key="TP-1")
```

### Xray Release Report (`scripts.xray_release_report`)

Answers "what can be released and what cannot". Requirements are grouped with their covering tests nested, each with the latest run status, who executed it, and linked defects.

```python
from scripts.xray_release_report import xray_release_report

# Scope: a test plan, a fixVersion, or both. With both, stories that carry the
# fixVersion but are not covered by any test in the plan are flagged.
xray_release_report(test_plan_key="TP-1", fix_version="2.1", project_key="PROJ")

# Options
xray_release_report(
    test_plan_key="TP-1",
    fix_version="2.1",
    project_key="PROJ",
    requirement_jql=None,              # custom requirement scope, overrides fix_version
    rule="all_pass",                   # or "no_fail": only FAIL blocks, others warn
    passing_statuses="PASS",           # comma-separated
    failing_statuses="FAIL",
    coverage_link_type="Tests",        # Jira issue link type Xray uses for coverage
    include_archived_executions=False,
    lookup_runs_outside_plan=True,     # one request per test not in the plan
    max_requirements=500,
)
```

Rules:
- `all_pass` (default): a requirement is releasable only if it has at least one covering test and every covering test's latest status is in `passing_statuses`.
- `no_fail`: releasable if no covering test is in `failing_statuses`. Other non-passing statuses (TODO, EXECUTING, ...) are listed as warnings.
- A requirement with no covering test is never releasable (`UNCOVERED`).
- Inside a plan, a test's status is its latest run across the plan's non-archived executions. Outside a plan, it is the latest run anywhere, or `NOT EXECUTED`.

How to use it for a report: call it once, then write the narrative from `summary` (counts), the `requirements` list (non-releasable first, each with `blockers` and `warnings`), and `tests_without_requirement` (plan tests not linked to any story in scope).

## Response Data Structures

All functions return JSON strings with **flattened** data structures (not nested API responses).

### Issue Structure

```json
{
  "key": "PROJ-123",
  "id": "10001",
  "summary": "Issue title",
  "description": "Issue description",
  "status": "In Progress",
  "issue_type": "Task",
  "priority": "High",
  "assignee": "user@company.com",
  "reporter": "reporter@company.com",
  "created": "2024-01-15T10:30:00.000+0000",
  "updated": "2024-01-16T14:20:00.000+0000",
  "labels": ["backend", "urgent"],
  "components": ["API", "Auth"],
  "custom_fields": {}
}
```

### User Structure

```json
{
  "username": "jdoe",
  "key": "JIRAUSER10000",
  "display_name": "Jane Doe",
  "email": "jdoe@company.com",
  "active": true,
  "timezone": "Europe/Berlin",
  "locale": "en_US"
}
```

### Release Report Structure

```json
{
  "scope": {"test_plan_key": "TP-1", "fix_version": "2.1", "project_key": "PROJ", "rule": "all_pass",
            "passing_statuses": ["PASS"], "failing_statuses": ["FAIL"]},
  "summary": {"requirements": 12, "releasable": 9, "not_releasable": 3, "uncovered": 1,
              "missed_by_test_plan": 1, "tests_evaluated": 40,
              "test_status_counts": {"PASS": 36, "FAIL": 2, "TODO": 2},
              "plan_tests_without_requirement": 3},
  "requirements": [
    {
      "key": "PROJ-42", "summary": "Login with SSO", "issue_type": "Story", "status": "Done",
      "priority": "High", "fix_versions": ["2.1"],
      "in_release_scope": true, "in_test_plan": true,
      "releasable": false,
      "blockers": ["TEST-7 is FAIL"],
      "warnings": [],
      "tests": [
        {"key": "TEST-7", "summary": "SSO redirect", "status": "FAIL", "in_test_plan": true,
         "execution_key": "TE-5", "executed_by": "jdoe", "finished_on": "2024-05-02T10:00:00+00:00",
         "defects": [{"id": 1, "key": "BUG-3", "summary": "Redirect loop", "status": "Open"}]}
      ]
    }
  ],
  "tests_without_requirement": [
    {"key": "TEST-99", "status": "PASS", "execution_key": "TE-5", "executed_by": "jdoe", "defects": []}
  ]
}
```

> **Note**: These are simplified structures. The raw Jira API returns nested data like `{"key": "...", "fields": {"summary": "...", "status": {"name": "..."}}}`; this skill flattens it for easier use.

## Error Handling

All functions return JSON strings. Check for errors:

```python
import json

result = jira_get_issue(issue_key="PROJ-999")
data = json.loads(result)

if not data.get("success", True):
    print(f"Error: {data['error']}")
    print(f"Type: {data['error_type']}")
else:
    print(f"Issue: {data['key']}")
```

### Error Types

- `ConfigurationError` - Missing URL or PAT token
- `AuthenticationError` - Invalid or expired PAT, or insufficient permissions
- `ValidationError` - Invalid input parameters
- `NotFoundError` - Resource not found
- `APIError` - Jira API error
- `NetworkError` - Connection issues

## Philosophy

This skill provides:
- **Read-Only Access**: Query and retrieve Jira and Xray data without modification
- **Token Efficiency**: Small surface area keeps LLM context lean
- **Safety**: The HTTP client only implements GET, so accidental writes are impossible
- **Consistency**: Unified error handling and response format

It does NOT provide:
- Write operations (create, update, transition, delete)
- Jira Cloud or Xray Cloud support (API token / basic auth, REST API v3, Xray GraphQL)
- Confluence or Bitbucket access
- Direct API access (use the provided functions instead)

**Best practices**:
- Always check return values for errors
- Use JQL for efficient searching
- Use `jira_search_fields` to discover custom field IDs before querying them
- For release questions, start with `xray_release_report` instead of composing raw Xray calls
- Xray JQL functions (`testPlanTests`, `requirementTests`, `requirements("NOK")`, ...) work directly in `jira_search`

## Dependencies

```bash
pip install -r requirements.txt
```
