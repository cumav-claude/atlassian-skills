# Jira Readonly Skills for Claude Code - Jira Data Center and Xray Integration

A read-only Claude Code skill for Jira Data Center / Server and the Xray test management app. It lets Claude look up issues, run JQL searches, inspect boards, sprints, worklogs, projects, versions, and users, and read Xray tests, executions, plans, and requirement coverage, without being able to change anything in Jira.

**Note**: This project targets Atlassian Data Center / Server only. Jira Cloud, Confluence, and Bitbucket are not supported.

## What is a Skill?

Skills are folders containing a `SKILL.md` file that teach Claude Code new capabilities. When you add this skill to your project, Claude can directly query your Jira instance.

Learn more: https://docs.anthropic.com/en/docs/claude-code/skills

## Features

- **Issues**: Get issue details, available transitions, worklog entries
- **Search**: JQL search with pagination, field definition lookup
- **Agile**: Boards, board issues, sprints, sprint issues
- **Projects**: Project list, project issues, versions
- **Users**: Profile lookup by username, email, or display name
- **Xray**: Tests and steps, execution results, test runs with step results and defects, test plans, requirement coverage
- **Release Report**: Per-story release verdict with covering tests nested, and stories a test plan missed
- **Read-Only by Construction**: The HTTP client only implements GET
- **PAT Authentication**: Personal Access Token, the Data Center standard
- **Unified Response Format**: All functions return flattened JSON structures

## Installation

1. Clone or copy the `jira-readonly-skills` folder into your project.

2. Install dependencies:

```bash
pip install -r jira-readonly-skills/requirements.txt
```

## Configuration

Create a `.env` file in `jira-readonly-skills/` (copy from `.env.example`):

```bash
JIRA_URL=https://jira.your-company.com
JIRA_PAT_TOKEN=your_pat_token

# Optional, defaults to false
# JIRA_SSL_VERIFY=true
```

Get your PAT in Jira: Profile → Personal Access Tokens → Create token. The same PAT is used for Xray.

Credentials can also be passed programmatically for agent environments without environment variables. See `jira-readonly-skills/SKILL.md` for the `AtlassianCredentials` object.

## Quick Start

Once configured, simply ask Claude to query Jira:

```
"Show me MYPROJ-123"

"Search for all in-progress issues assigned to me"

"What transitions are available for MYPROJ-123?"

"Show the worklog on MYPROJ-456"

"List the active sprints on board 10"

"Which versions does project MYPROJ have?"

"Show the results of test execution TE-5"

"Which stories in version 2.1 have no tests?"

"Can version 2.1 be released based on test plan TP-1? Write a release report."
```

## Available Functions

**jira_issues**
- `jira_get_issue` - Get issue details

**jira_search**
- `jira_search` - Search issues using JQL
- `jira_search_fields` - Search field definitions

**jira_workflow**
- `jira_get_transitions` - Get available status transitions

**jira_agile**
- `jira_get_agile_boards` - Get agile boards
- `jira_get_board_issues` - Get issues from a board
- `jira_get_sprints_from_board` - Get sprints from a board
- `jira_get_sprint_issues` - Get issues in a sprint

**jira_links**
- `jira_get_link_types` - Get available link types

**jira_worklog**
- `jira_get_worklog` - Get worklog entries

**jira_projects**
- `jira_get_all_projects` - Get all projects
- `jira_get_project_issues` - Get issues for a project
- `jira_get_project_versions` - Get versions for a project

**jira_users**
- `jira_get_user_profile` - Get user profile

**xray_tests**
- `xray_get_tests` - Export tests by keys, JQL, or filter
- `xray_get_test_steps` - Manual step definitions of a test
- `xray_get_test_preconditions` - Pre-conditions of a test
- `xray_get_test_sets` - Test sets containing a test
- `xray_get_test_plans` - Test plans containing a test
- `xray_get_test_executions` - Test executions containing a test
- `xray_get_test_runs` - All runs of a test
- `xray_get_test_set_tests` - Tests in a test set

**xray_executions**
- `xray_get_test_execution_tests` - Tests in an execution with run status and defects
- `xray_get_test_run` - One test run
- `xray_get_test_run_steps` - Step-level results of a run
- `xray_get_test_statuses` - Configured test statuses
- `xray_get_test_step_statuses` - Configured step statuses

**xray_plans**
- `xray_get_test_plan_tests` - Tests in a plan with latest status
- `xray_get_test_plan_executions` - Executions of a plan

**xray_coverage**
- `xray_get_requirement_tests` - Tests covering a requirement
- `xray_get_test_requirements` - Requirements covered by a test
- `xray_get_test_plan_requirements` - Requirements covered by a plan
- `xray_get_requirements_by_status` - Requirements by coverage status (OK, NOK, NOTRUN, UNCOVERED)

**xray_release_report**
- `xray_release_report` - Release readiness report by test plan and/or fixVersion

See `jira-readonly-skills/REFERENCE.md` for detailed examples.

## Error Handling

All functions return JSON with a consistent error format:

```json
{
  "success": false,
  "error": "Resource not found: Issue Does Not Exist",
  "error_type": "NotFoundError"
}
```

Error types: `ConfigurationError`, `AuthenticationError`, `ValidationError`, `NotFoundError`, `APIError`, `NetworkError`

## Testing

```bash
# Install test dependencies
pip install -r test/requirements.txt

# Run all tests
pytest test/ -v

# Generate coverage report
pytest test/ --cov=jira-readonly-skills/scripts --cov-report=html
```

See [test/README.md](test/README.md) for details.

## Development

- Skill code lives in `jira-readonly-skills/scripts/`. Every module exposes read functions only and shares `_common.py` for configuration, the GET-only HTTP client, and response formatting.
- Xray modules (`xray_*.py`) use the Xray Server/DC REST API v1.0 under `/rest/raven/1.0/api/` and the Xray JQL functions. Xray Cloud is not supported.
- When adding a function, keep it read-only (GET requests only), document it in `SKILL.md` and `REFERENCE.md`, and add tests under `test/`.

## Roadmap

### TODO: Identity pseudonymization layer

Goal: the LLM never sees real usernames, emails, or display names from Jira, but JQL and lookups keep working.

Design sketch:
- A local mapping store (SQLite or JSON, outside the repo, never committed) maps each person to a random stable token such as `user_7f3a`. It records every form of that person seen in responses: username, key, email, display name. Entries are created lazily on first sight.
- **Outbound (Jira to LLM)**: structured identity fields are replaced by the token. The touch points are the shared issue simplifier (`assignee`, `reporter`), the worklog simplifier (`author`, `update_author`), the user profile simplifier, a recursive walk over `custom_fields` for user-picker fields, and the Xray run fields (`executed_by`, `assignee`) in the tests, executions, and release report modules. Free text (summary, description, comments) is left untouched.
- **Inbound (LLM to Jira)**: every function input that can carry an identity (`jql`, `user_identifier`) has known tokens string-replaced back to the real username before the request, so `assignee = user_7f3a` reaches Jira as `assignee = jdoe`.
- A small local CLI resolves tokens in the LLM's answers back to real names, since the skill cannot rewrite assistant output itself.

Known limits:
- In Claude Code the model has a shell, so the mapping file must be denied via permission settings to stay hidden.
- Names typed into the prompt by the human are visible to the LLM regardless.

## License

MIT License
