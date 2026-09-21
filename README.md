# Jira Readonly Skills for Claude Code - Jira Data Center Integration

A read-only Claude Code skill for Jira Data Center / Server. It lets Claude look up issues, run JQL searches, inspect boards, sprints, worklogs, projects, versions, and users, without being able to change anything in Jira.

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

Get your PAT in Jira: Profile → Personal Access Tokens → Create token.

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
- When adding a function, keep it read-only (GET requests only), document it in `SKILL.md` and `REFERENCE.md`, and add tests under `test/`.

## License

MIT License
