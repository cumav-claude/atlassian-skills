# Jira Readonly Skills API Reference

Detailed usage examples for the read-only Jira Data Center / Server and Xray operations.

## Configuration Modes

All functions support two configuration modes:

### Mode 1: Environment Variables

```python
# Set environment variables first (or use a .env file)
# JIRA_URL=https://jira.company.com
# JIRA_PAT_TOKEN=your_pat_token

from scripts.jira_issues import jira_get_issue

# Uses environment variables automatically
result = jira_get_issue("PROJ-123")
```

### Mode 2: Parameter-Based (Agent Mode)

```python
from scripts._common import AtlassianCredentials, check_available_skills
from scripts.jira_issues import jira_get_issue

credentials = AtlassianCredentials(
    jira_url="https://jira.company.com",
    jira_pat_token="your_pat_token"
)

availability = check_available_skills(credentials)
print(availability["available_services"])  # ["jira"]

result = jira_get_issue("PROJ-123", credentials=credentials)
```

**Note:** All examples below can use either mode. For Agent mode, add `credentials=credentials` as the last argument to any function call.

## Examples

### Search for Issues

```python
from scripts.jira_search import jira_search

result = jira_search("project = MYPROJ AND status = 'In Progress'", limit=10)

# Search with specific fields and pagination
result = jira_search(
    jql="assignee = currentUser() AND status != Done",
    fields="summary,status,priority",
    limit=20,
    start_at=20
)
```

### Get Available Fields

```python
from scripts.jira_search import jira_search_fields

# All fields
result = jira_search_fields()

# Find a custom field ID by name
result = jira_search_fields(keyword="story points")
```

### Get Issue Details

```python
from scripts.jira_issues import jira_get_issue

result = jira_get_issue("MYPROJ-123")

# Only specific fields
result = jira_get_issue("MYPROJ-123", fields="summary,status,assignee,priority")

# Expand changelog
result = jira_get_issue("MYPROJ-123", expand="changelog")
```

### Get Available Transitions

```python
from scripts.jira_workflow import jira_get_transitions

transitions = jira_get_transitions("MYPROJ-123")
```

### Get Worklog Entries

```python
from scripts.jira_worklog import jira_get_worklog

result = jira_get_worklog("MYPROJ-123")
```

### Get Link Types

```python
from scripts.jira_links import jira_get_link_types

result = jira_get_link_types()
```

### Get Projects and Versions

```python
from scripts.jira_projects import (
    jira_get_all_projects,
    jira_get_project_issues,
    jira_get_project_versions
)

projects = jira_get_all_projects()
projects = jira_get_all_projects(include_archived=True)

issues = jira_get_project_issues("MYPROJ", limit=50)

versions = jira_get_project_versions("MYPROJ")
```

### Get User Profile

```python
from scripts.jira_users import jira_get_user_profile

# By username
result = jira_get_user_profile("jdoe")

# By email address or display name (falls back to user search)
result = jira_get_user_profile("jdoe@example.com")
result = jira_get_user_profile("Jane Doe")
```

### Agile Boards and Sprints

```python
from scripts.jira_agile import (
    jira_get_agile_boards,
    jira_get_board_issues,
    jira_get_sprints_from_board,
    jira_get_sprint_issues
)

boards = jira_get_agile_boards(project_key="MYPROJ")
boards = jira_get_agile_boards(board_type="scrum")

issues = jira_get_board_issues(board_id="123", limit=50)
issues = jira_get_board_issues(board_id="123", jql="status = 'In Progress'")

sprints = jira_get_sprints_from_board(board_id="123", state="active")

sprint_issues = jira_get_sprint_issues(sprint_id="456", limit=50)
```

## Xray Examples

Xray calls use the same URL and PAT. No extra configuration is needed.

### Inspect a Test

```python
from scripts.xray_tests import xray_get_tests, xray_get_test_steps, xray_get_test_runs

# Definition, type, and status
result = xray_get_tests(keys="TEST-1")

# Manual steps with expected results
result = xray_get_test_steps("TEST-1")

# Every run of the test, across executions
result = xray_get_test_runs("TEST-1")
result = xray_get_test_runs("TEST-1", test_environments="staging")
```

### Execution Results

```python
from scripts.xray_executions import (
    xray_get_test_execution_tests, xray_get_test_run, xray_get_test_run_steps
)

# All tests in an execution with status, executed by, defects, and status counts
result = xray_get_test_execution_tests("TE-5")

# Drill into a failing run
run = xray_get_test_run(test_exec_key="TE-5", test_key="TEST-7")
steps = xray_get_test_run_steps(run_id=123)   # step statuses, actual results, defects
```

### Test Plans

```python
from scripts.xray_plans import xray_get_test_plan_tests, xray_get_test_plan_executions

# Latest status per test in the plan, with counts
result = xray_get_test_plan_tests("TP-1")

# Executions belonging to the plan
result = xray_get_test_plan_executions("TP-1")
```

### Requirement Coverage

```python
from scripts.xray_coverage import (
    xray_get_requirement_tests, xray_get_test_plan_requirements, xray_get_requirements_by_status
)

# Tests covering a story
result = xray_get_requirement_tests("PROJ-42")

# Stories covered by a plan
result = xray_get_test_plan_requirements("TP-1")

# Coverage gaps for a version
uncovered = xray_get_requirements_by_status("UNCOVERED", project_key="PROJ", version="2.1")
failing = xray_get_requirements_by_status("NOK", project_key="PROJ", version="2.1")
not_run = xray_get_requirements_by_status("NOTRUN", test_plan_key="TP-1")
```

### Release Readiness Report

```python
from scripts.xray_release_report import xray_release_report
import json

# Plan plus version: flags stories in 2.1 that the plan does not cover
report = json.loads(xray_release_report(test_plan_key="TP-1", fix_version="2.1", project_key="PROJ"))

print(report["summary"])
for req in report["requirements"]:
    verdict = "RELEASABLE" if req["releasable"] else "BLOCKED"
    print(f"{req['key']} {req['summary']}: {verdict}")
    for blocker in req["blockers"]:
        print(f"  - {blocker}")
    for warning in req["warnings"]:
        print(f"  ! {warning}")

# Plan only
xray_release_report(test_plan_key="TP-1")

# Version only (test status = latest run anywhere)
xray_release_report(fix_version="2.1", project_key="PROJ")

# Custom requirement scope and a lenient rule
xray_release_report(
    test_plan_key="TP-1",
    requirement_jql='project = PROJ AND labels = "release-2.1"',
    rule="no_fail",
)

# Custom statuses (for instances with extra Xray statuses)
xray_release_report(test_plan_key="TP-1", passing_statuses="PASS,PASSED WITH REMARKS")
```

Notes:
- Coverage is read from the Jira issue link type Xray uses (`Tests` by default). Change `coverage_link_type` if your instance renamed it.
- Archived executions of the plan are ignored unless `include_archived_executions=True`.
- Tests outside the plan cost one request each. Set `lookup_runs_outside_plan=False` to skip them; they then show as `NOT EXECUTED`.

### Xray JQL Functions

Usable directly with `jira_search`:

```
issue in testPlanTests("TP-1")                 # tests in a plan
issue in testPlanTests("TP-1", "FAIL")         # failing tests in a plan
issue in testExecutionTests("TE-5", "TODO")    # not yet run in an execution
issue in requirementTests("PROJ-42")           # tests covering a story
issue in testRequirements("TEST-1")            # stories a test covers
issue in testPlanRequirements("TP-1")          # stories covered by a plan
issue in requirements("NOK", "PROJ", "2.1")    # stories failing coverage for a version
issue in requirements("UNCOVERED", "PROJ")     # stories with no tests
issue in testsWithoutTestExecution()           # tests never executed
issue in defectsCreatedDuringTestExecution("TE-5")
```

## JQL Query Examples

Common JQL patterns for searching Jira issues:

```
# Issues assigned to current user
assignee = currentUser()

# Open issues in a project
project = MYPROJ AND status != Done

# High priority bugs
project = MYPROJ AND issuetype = Bug AND priority = High

# Issues updated in last 7 days
updated >= -7d

# Issues in current sprint
sprint in openSprints()

# Unassigned issues
assignee is EMPTY

# Issues with specific label
labels = "backend"

# Issues created by specific user
reporter = "jdoe"

# Combined query
project = MYPROJ AND status = "In Progress" AND assignee = currentUser() ORDER BY priority DESC
```

## Response Format

### Success Response

```json
{
  "key": "MYPROJ-123",
  "summary": "Issue title",
  "status": "In Progress",
  "assignee": "user@example.com"
}
```

### Error Response

```json
{
  "success": false,
  "error": "Resource not found: Issue Does Not Exist",
  "error_type": "NotFoundError"
}
```

### Paginated Response

```json
{
  "issues": [...],
  "total": 150,
  "start_at": 0,
  "max_results": 10,
  "is_last": false
}
```

### Transitions Response

```json
{
  "issue_key": "MYPROJ-123",
  "count": 2,
  "transitions": [
    {
      "id": "21",
      "name": "In Progress",
      "to_status": "In Progress",
      "to_status_id": "3",
      "has_screen": false
    },
    {
      "id": "31",
      "name": "Done",
      "to_status": "Done",
      "to_status_id": "10001",
      "has_screen": true,
      "required_fields": [
        {"id": "resolution", "name": "Resolution", "required": true, "schema": {"type": "resolution"}}
      ]
    }
  ]
}
```

### Worklog Response

```json
{
  "issue_key": "MYPROJ-123",
  "count": 1,
  "worklogs": [
    {
      "id": "10000",
      "comment": "Investigated the bug",
      "created": "2024-01-15T10:30:00.000+0000",
      "updated": "2024-01-15T10:30:00.000+0000",
      "started": "2024-01-15T09:00:00.000+0000",
      "time_spent": "1h 30m",
      "time_spent_seconds": 5400,
      "author": "Jane Doe",
      "update_author": "Jane Doe"
    }
  ]
}
```

## Agent Mode Complete Example

When deploying in Agent environments without environment variables:

```python
from scripts._common import AtlassianCredentials, check_available_skills
from scripts.jira_issues import jira_get_issue
from scripts.jira_search import jira_search
import json

# Step 1: Create credentials object
credentials = AtlassianCredentials(
    jira_url="https://jira.company.com",
    jira_pat_token="jira_pat_here"
)

# Step 2: Check that Jira is usable
availability = check_available_skills(credentials)
if "jira" not in availability["available_services"]:
    raise SystemExit(f"Jira unavailable: {availability['unavailable_services']}")

# Step 3: Use read-only skills with the credentials parameter
result = jira_get_issue(issue_key="PROJ-123", credentials=credentials)
issue = json.loads(result)

if issue.get("success", True):
    print(f"Issue: {issue['key']} - {issue['summary']}")

    result = jira_search(
        jql="project = PROJ AND status = 'In Progress'",
        limit=10,
        credentials=credentials
    )
    search_results = json.loads(result)
    print(f"Found {search_results['total']} issues")
else:
    print(f"Error: {issue['error']}")
```

## Credentials Object Reference

```python
AtlassianCredentials(
    jira_url: Optional[str] = None,        # Base URL of the Jira Data Center instance
    jira_pat_token: Optional[str] = None,  # Personal Access Token
    jira_ssl_verify: bool = True           # Verify TLS certificates
)
```
