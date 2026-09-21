---
name: jira-readonly-skills
description: Read-only Python utilities for Jira Data Center / Server. Provides read access to issues, JQL search, field definitions, workflow transitions, agile boards and sprints, issue link types, worklogs, projects, versions, and user profiles. Use when users need to query Jira like "get a Jira issue", "search issues with JQL", "list sprints on a board", or "show worklog for an issue". No write operations are exposed.
license: Complete terms in LICENSE
---

# Jira Data Center Readonly Skills

Read-only Python utilities for Jira Data Center / Server, authenticated with a Personal Access Token (PAT) and using the Jira REST API v2.

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
- **Read-Only Access**: Query and retrieve Jira data without modification
- **Token Efficiency**: Small surface area keeps LLM context lean
- **Safety**: The HTTP client only implements GET, so accidental writes are impossible
- **Consistency**: Unified error handling and response format

It does NOT provide:
- Write operations (create, update, transition, delete)
- Jira Cloud support (API token / basic auth, REST API v3)
- Confluence or Bitbucket access
- Direct API access (use the provided functions instead)

**Best practices**:
- Always check return values for errors
- Use JQL for efficient searching
- Use `jira_search_fields` to discover custom field IDs before querying them

## Dependencies

```bash
pip install -r requirements.txt
```
