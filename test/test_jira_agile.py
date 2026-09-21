"""Tests for jira_agile.py."""

import json
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path / 'jira-readonly-skills'))
sys.path.insert(0, str(_base_path / 'jira-readonly-skills' / 'scripts'))

from scripts.jira_agile import (
    jira_get_agile_boards,
    jira_get_board_issues,
    jira_get_sprints_from_board,
    jira_get_sprint_issues,
)


class TestJiraGetAgileBoards:
    """Tests for jira_get_agile_boards function."""

    @patch('scripts.jira_agile.get_jira_client')
    def test_get_boards_success(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            'values': [
                {'id': 1, 'name': 'Board 1', 'type': 'scrum'},
                {'id': 2, 'name': 'Board 2', 'type': 'kanban'}
            ],
            'total': 2,
            'isLast': True
        }

        result = jira_get_agile_boards()
        data = json.loads(result)

        assert len(data['boards']) == 2
        assert data['boards'][0]['name'] == 'Board 1'

    @patch('scripts.jira_agile.get_jira_client')
    def test_get_boards_with_filters(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            'values': [{'id': 1, 'name': 'Scrum Board', 'type': 'scrum'}],
            'total': 1,
            'isLast': True
        }

        result = jira_get_agile_boards(
            board_name='Scrum',
            project_key='PROJ',
            board_type='scrum'
        )
        data = json.loads(result)

        assert len(data['boards']) == 1


class TestJiraGetBoardIssues:
    """Tests for jira_get_board_issues function."""

    @patch('scripts.jira_agile.get_jira_client')
    def test_get_board_issues_success(self, mock_get_client, sample_issue_data):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            'issues': [sample_issue_data],
            'total': 1
        }

        result = jira_get_board_issues('1')
        data = json.loads(result)

        assert len(data['issues']) == 1
        assert data['board_id'] == '1'

    @patch('scripts.jira_agile.get_jira_client')
    def test_get_board_issues_missing_id(self, mock_get_client):
        mock_get_client.return_value = MagicMock()
        result = jira_get_board_issues('')
        data = json.loads(result)

        assert data['success'] is False
        assert data['error_type'] == 'ValidationError'


class TestJiraGetSprintsFromBoard:
    """Tests for jira_get_sprints_from_board function."""

    @patch('scripts.jira_agile.get_jira_client')
    def test_get_sprints_success(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            'values': [
                {
                    'id': 1,
                    'name': 'Sprint 1',
                    'state': 'active',
                    'startDate': '2024-01-01',
                    'endDate': '2024-01-14',
                    'goal': 'Complete feature X'
                }
            ],
            'isLast': True
        }

        result = jira_get_sprints_from_board('1')
        data = json.loads(result)

        assert len(data['sprints']) == 1
        assert data['sprints'][0]['name'] == 'Sprint 1'

    @patch('scripts.jira_agile.get_jira_client')
    def test_get_sprints_with_state_filter(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            'values': [],
            'isLast': True
        }

        result = jira_get_sprints_from_board('1', state='active')
        data = json.loads(result)

        assert 'sprints' in data

    @patch('scripts.jira_agile.get_jira_client')
    def test_get_sprints_missing_board_id(self, mock_get_client):
        mock_get_client.return_value = MagicMock()
        result = jira_get_sprints_from_board('')
        data = json.loads(result)

        assert data['success'] is False
        assert data['error_type'] == 'ValidationError'


class TestJiraGetSprintIssues:
    """Tests for jira_get_sprint_issues function."""

    @patch('scripts.jira_agile.get_jira_client')
    def test_get_sprint_issues_success(self, mock_get_client, sample_issue_data):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            'issues': [sample_issue_data],
            'total': 1
        }

        result = jira_get_sprint_issues('1')
        data = json.loads(result)

        assert len(data['issues']) == 1
        assert data['sprint_id'] == '1'

    @patch('scripts.jira_agile.get_jira_client')
    def test_get_sprint_issues_missing_id(self, mock_get_client):
        mock_get_client.return_value = MagicMock()
        result = jira_get_sprint_issues('')
        data = json.loads(result)

        assert data['success'] is False
        assert data['error_type'] == 'ValidationError'
