"""Tests for jira_users.py."""

import json
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path / 'jira-readonly-skills'))
sys.path.insert(0, str(_base_path / 'jira-readonly-skills' / 'scripts'))

from scripts.jira_users import jira_get_user_profile
from _common import NotFoundError, APIError


SAMPLE_USER = {
    'name': 'testuser',
    'key': 'JIRAUSER10000',
    'displayName': 'Test User',
    'emailAddress': 'test@example.com',
    'active': True,
    'timeZone': 'UTC',
    'locale': 'en_US'
}


class TestJiraGetUserProfile:
    """Tests for jira_get_user_profile function."""

    @patch('scripts.jira_users.get_jira_client')
    def test_get_user_by_username(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        mock_client.get.return_value = dict(SAMPLE_USER)

        result = jira_get_user_profile('testuser')
        data = json.loads(result)

        assert data['username'] == 'testuser'
        assert data['key'] == 'JIRAUSER10000'
        assert data['display_name'] == 'Test User'
        assert data['email'] == 'test@example.com'
        assert data['active'] is True
        # Verify the Data Center username parameter was used
        mock_client.get.assert_called_once_with(
            '/rest/api/2/user',
            params={'username': 'testuser'}
        )

    @patch('scripts.jira_users.get_jira_client')
    def test_get_user_by_email_via_search(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        # Exact lookup fails, search succeeds
        mock_client.get.side_effect = [
            NotFoundError('not found'),
            [dict(SAMPLE_USER)],
        ]

        result = jira_get_user_profile('test@example.com')
        data = json.loads(result)

        assert data['email'] == 'test@example.com'
        mock_client.get.assert_called_with(
            '/rest/api/2/user/search',
            params={'username': 'test@example.com', 'maxResults': 1}
        )

    @patch('scripts.jira_users.get_jira_client')
    def test_get_user_via_picker(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        # Exact lookup and search fail, picker finds a match, then exact lookup
        mock_client.get.side_effect = [
            NotFoundError('not found'),
            [],
            {'users': [{'name': 'testuser', 'displayName': 'Test User'}]},
            dict(SAMPLE_USER),
        ]

        result = jira_get_user_profile('Test User')
        data = json.loads(result)

        assert data['username'] == 'testuser'
        assert mock_client.get.call_count == 4
        mock_client.get.assert_called_with(
            '/rest/api/2/user',
            params={'username': 'testuser'}
        )

    @patch('scripts.jira_users.get_jira_client')
    def test_get_user_missing_identifier(self, mock_get_client):
        mock_get_client.return_value = MagicMock()
        result = jira_get_user_profile('')
        data = json.loads(result)

        assert data['success'] is False
        assert data['error_type'] == 'ValidationError'

    @patch('scripts.jira_users.get_jira_client')
    def test_get_user_not_found(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        # All lookup methods return empty results
        mock_client.get.side_effect = [
            {},  # Exact lookup returns empty dict
            [],  # Search returns empty list
            {'users': []}  # Picker returns no users
        ]

        result = jira_get_user_profile('nonexistent')
        data = json.loads(result)

        assert data['success'] is False
        assert data['error_type'] == 'NotFoundError'

    @patch('scripts.jira_users.get_jira_client')
    def test_get_user_api_errors_fall_through(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        mock_client.get.side_effect = [
            APIError('boom'),
            APIError('boom'),
            APIError('boom'),
        ]

        result = jira_get_user_profile('someone')
        data = json.loads(result)

        assert data['success'] is False
        assert data['error_type'] == 'NotFoundError'
