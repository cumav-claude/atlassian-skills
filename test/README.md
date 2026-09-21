# Jira Readonly Skills Test Suite

This directory contains test coverage for all read-only Jira methods and the shared utilities.

## Test Coverage

**76 test cases** covering **13 methods** plus the common module:

### Jira Methods (42 tests)
- Issue retrieval (1 method, 3 tests)
- Agile boards and sprints (4 methods, 9 tests)
- Issue link types (1 method, 1 test)
- Projects and versions (3 methods, 7 tests)
- Search and field definitions (2 methods, 10 tests)
- User profile lookup (1 method, 6 tests)
- Workflow transitions (1 method, 3 tests)
- Worklogs (1 method, 3 tests)

### Common Module (34 tests)
- Configuration management (`AtlassianConfig`, environment and PAT handling)
- Read-only HTTP client (`AtlassianClient`, GET only, error mapping)
- Parameter-based credentials (`AtlassianCredentials`, `check_available_skills`)
- Helper functions (response formatting, issue simplification)

| Category | Files | Methods | Tests |
|----------|-------|---------|-------|
| Jira | 8 | 13 | 42 |
| Common | 2 | - | 34 |
| **Total** | **10** | **13** | **76** |

## Installation

```bash
pip install -r test/requirements.txt
```

## Running Tests

### Run All Tests
```bash
pytest test/ -v
```

### Run Specific Module Tests
```bash
# Jira method tests
pytest test/test_jira_*.py -v

# Common module tests
pytest test/test_common.py test/test_credentials.py -v
```

### Run Specific Test File
```bash
pytest test/test_jira_issues.py -v
```

### Run Specific Test Class or Method
```bash
# Run specific test class
pytest test/test_jira_issues.py::TestJiraGetIssue -v

# Run specific test method
pytest test/test_jira_issues.py::TestJiraGetIssue::test_get_issue_success -v
```

## How the Tests Work

All tests mock the Jira client, so no Jira instance or network access is needed. Each test patches `get_jira_client` in the module under test and asserts on the request parameters and the flattened JSON response.

The scripts import `_common` as a top-level module (via `sys.path`), so tests that need to raise the skill's exception classes must import them from `_common`, not `scripts._common`, or the `except` clauses in the scripts will not match.
