"""Tests for jira_links.py."""

import json
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path / 'jira-readonly-skills'))
sys.path.insert(0, str(_base_path / 'jira-readonly-skills' / 'scripts'))

from scripts.jira_links import (
    jira_get_link_types,
)


class TestJiraGetLinkTypes:
    """Tests for jira_get_link_types function."""

    @patch('scripts.jira_links.get_jira_client')
    def test_get_link_types_success(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.api_path = lambda x: f'/rest/api/2/{x}'
        mock_client.get.return_value = {
            'issueLinkTypes': [
                {
                    'id': '10000',
                    'name': 'Blocks',
                    'inward': 'is blocked by',
                    'outward': 'blocks'
                },
                {
                    'id': '10001',
                    'name': 'Duplicate',
                    'inward': 'is duplicated by',
                    'outward': 'duplicates'
                }
            ]
        }

        result = jira_get_link_types()
        data = json.loads(result)

        assert len(data['link_types']) == 2
        assert data['link_types'][0]['name'] == 'Blocks'
