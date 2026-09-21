"""Tests for jira_projects.py."""

import json
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path / 'jira-readonly-skills'))
sys.path.insert(0, str(_base_path / 'jira-readonly-skills' / 'scripts'))

from scripts.jira_projects import (
    jira_get_all_projects,
    jira_get_project_issues,
    jira_get_project_versions,
)


class TestJiraGetAllProjects:
    """Tests for jira_get_all_projects function."""

    @patch('scripts.jira_projects.get_jira_client')
    def test_get_projects_success(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        mock_client.get.return_value = [
            {
                'id': '10000',
                'key': 'PROJ',
                'name': 'Project One',
                'projectTypeKey': 'software',
                'style': 'classic',
                'isPrivate': False
            },
            {
                'id': '10001',
                'key': 'TEST',
                'name': 'Test Project',
                'projectTypeKey': 'software',
                'style': 'next-gen',
                'isPrivate': True
            }
        ]

        result = jira_get_all_projects()
        data = json.loads(result)

        assert len(data['projects']) == 2
        assert data['projects'][0]['key'] == 'PROJ'

    @patch('scripts.jira_projects.get_jira_client')
    def test_get_projects_include_archived(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        mock_client.get.return_value = []

        result = jira_get_all_projects(include_archived=True)
        data = json.loads(result)

        assert 'projects' in data


class TestJiraGetProjectIssues:
    """Tests for jira_get_project_issues function."""

    @patch('scripts.jira_projects.get_jira_client')
    def test_get_project_issues_success(self, mock_get_client, sample_issue_data):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        mock_client.get.return_value = {
            'issues': [sample_issue_data],
            'total': 1
        }

        result = jira_get_project_issues('PROJ')
        data = json.loads(result)

        assert len(data['issues']) == 1
        assert data['project_key'] == 'PROJ'

    @patch('scripts.jira_projects.get_jira_client')
    def test_get_project_issues_with_pagination(self, mock_get_client, sample_issue_data):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        mock_client.get.return_value = {
            'issues': [sample_issue_data],
            'total': 100
        }

        result = jira_get_project_issues('PROJ', limit=10, start_at=20)
        data = json.loads(result)

        assert data['start_at'] == 20
        assert data['total'] == 100

    @patch('scripts.jira_projects.get_jira_client')
    def test_get_project_issues_missing_key(self, mock_get_client):
        mock_get_client.return_value = MagicMock()
        result = jira_get_project_issues('')
        data = json.loads(result)

        assert data['success'] is False
        assert data['error_type'] == 'ValidationError'


class TestJiraGetProjectVersions:
    """Tests for jira_get_project_versions function."""

    @patch('scripts.jira_projects.get_jira_client')
    def test_get_versions_success(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        mock_client.get.return_value = [
            {
                'id': '10000',
                'name': '1.0.0',
                'description': 'First release',
                'released': True,
                'archived': False,
                'startDate': '2024-01-01',
                'releaseDate': '2024-02-01'
            }
        ]

        result = jira_get_project_versions('PROJ')
        data = json.loads(result)

        assert len(data['versions']) == 1
        assert data['versions'][0]['name'] == '1.0.0'

    @patch('scripts.jira_projects.get_jira_client')
    def test_get_versions_missing_key(self, mock_get_client):
        mock_get_client.return_value = MagicMock()
        result = jira_get_project_versions('')
        data = json.loads(result)

        assert data['success'] is False
        assert data['error_type'] == 'ValidationError'
