"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add both jira-readonly-skills and scripts directories to path for proper imports
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path / 'jira-readonly-skills'))
sys.path.insert(0, str(_base_path / 'jira-readonly-skills' / 'scripts'))


@pytest.fixture
def mock_jira_client():
    """Create a mock Jira client."""
    with patch('_common.get_jira_client') as mock:
        client = MagicMock()
        mock.return_value = client
        client.api_path = lambda x: f'/rest/api/2/{x}'
        yield client


@pytest.fixture
def sample_issue_data():
    """Sample Jira issue data."""
    return {
        'key': 'PROJ-123',
        'id': '10001',
        'fields': {
            'summary': 'Test Issue',
            'description': 'Test description',
            'status': {'name': 'Open'},
            'issuetype': {'name': 'Task'},
            'priority': {'name': 'Medium'},
            'assignee': {'emailAddress': 'assignee@example.com'},
            'reporter': {'emailAddress': 'reporter@example.com'},
            'created': '2024-01-01T00:00:00.000+0000',
            'updated': '2024-01-02T00:00:00.000+0000',
            'labels': ['test'],
            'components': [{'name': 'Backend'}]
        }
    }
