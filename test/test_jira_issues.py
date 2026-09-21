"""Tests for jira_issues.py."""

import json
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path / 'jira-readonly-skills'))
sys.path.insert(0, str(_base_path / 'jira-readonly-skills' / 'scripts'))

from scripts.jira_issues import (
    jira_get_issue,
)
from scripts._common import ValidationError, NotFoundError


class TestJiraGetIssue:
    """Tests for jira_get_issue function."""

    @patch('scripts.jira_issues.get_jira_client')
    def test_get_issue_success(self, mock_get_client, sample_issue_data):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        mock_client.get.return_value = sample_issue_data

        result = jira_get_issue('PROJ-123')
        data = json.loads(result)

        assert data['key'] == 'PROJ-123'
        assert data['summary'] == 'Test Issue'
        mock_client.get.assert_called_once()

    @patch('scripts.jira_issues.get_jira_client')
    def test_get_issue_with_fields(self, mock_get_client, sample_issue_data):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        mock_client.get.return_value = sample_issue_data

        result = jira_get_issue('PROJ-123', fields='summary,status')
        data = json.loads(result)

        assert data['key'] == 'PROJ-123'

    @patch('scripts.jira_issues.get_jira_client')
    def test_get_issue_not_found(self, mock_get_client):
        # Mock the client to return an error response directly
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        # Simulate 404 by returning empty/error response
        mock_client.get.return_value = None

        result = jira_get_issue('INVALID-999')
        data = json.loads(result)

        # When get returns None, simplify_issue will fail
        assert data['success'] is False
