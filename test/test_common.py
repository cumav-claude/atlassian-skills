"""Tests for _common.py utilities."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
_base_path = Path(__file__).parent.parent
sys.path.insert(0, str(_base_path / 'jira-readonly-skills'))
sys.path.insert(0, str(_base_path / 'jira-readonly-skills' / 'scripts'))

from scripts._common import (
    format_error_response,
    format_json_response,
    simplify_issue,
    AtlassianConfig,
    AtlassianClient,
    ConfigurationError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    APIError,
    NetworkError,
)


class TestFormatErrorResponse:
    """Tests for format_error_response function."""

    def test_basic_error(self):
        result = format_error_response("TestError", "Test message")
        data = json.loads(result)
        assert data['success'] is False
        assert data['error'] == "Test message"
        assert data['error_type'] == "TestError"

    def test_error_with_details(self):
        result = format_error_response("TestError", "Test message", "Extra details")
        data = json.loads(result)
        assert data['details'] == "Extra details"

    def test_unicode_support(self):
        result = format_error_response("TestError", "测试消息")
        data = json.loads(result)
        assert data['error'] == "测试消息"


class TestFormatJsonResponse:
    """Tests for format_json_response function."""

    def test_dict_response(self):
        result = format_json_response({'key': 'value'})
        data = json.loads(result)
        assert data['key'] == 'value'

    def test_list_response(self):
        result = format_json_response([1, 2, 3])
        data = json.loads(result)
        assert data == [1, 2, 3]

    def test_unicode_support(self):
        result = format_json_response({'message': '中文测试'})
        data = json.loads(result)
        assert data['message'] == '中文测试'


class TestSimplifyIssue:
    """Tests for simplify_issue function."""

    def test_basic_simplification(self, sample_issue_data):
        result = simplify_issue(sample_issue_data)
        assert result['key'] == 'PROJ-123'
        assert result['summary'] == 'Test Issue'
        assert result['status'] == 'Open'
        assert result['issue_type'] == 'Task'

    def test_assignee_extraction(self, sample_issue_data):
        result = simplify_issue(sample_issue_data)
        assert result['assignee'] == 'assignee@example.com'

    def test_missing_assignee(self, sample_issue_data):
        sample_issue_data['fields']['assignee'] = None
        result = simplify_issue(sample_issue_data)
        assert result['assignee'] is None

    def test_components_extraction(self, sample_issue_data):
        result = simplify_issue(sample_issue_data)
        assert 'Backend' in result['components']


class TestAtlassianConfig:
    """Tests for AtlassianConfig class."""

    def test_pat_token_stored(self):
        config = AtlassianConfig(
            url='https://jira.example.com',
            pat_token='test-token'
        )
        assert config.pat_token == 'test-token'
        assert config.ssl_verify is True

    def test_missing_pat_token_auth_header_raises(self):
        config = AtlassianConfig(url='https://jira.example.com')
        with pytest.raises(ConfigurationError):
            config.get_auth_header()

    def test_url_trailing_slash_removed(self):
        config = AtlassianConfig(
            url='https://jira.example.com/',
            pat_token='test-token'
        )
        assert config.url == 'https://jira.example.com'

    def test_get_auth_header_pat(self):
        config = AtlassianConfig(
            url='https://jira.example.com',
            pat_token='test-token'
        )
        header = config.get_auth_header()
        assert header['Authorization'] == 'Bearer test-token'

    @patch.dict(os.environ, {
        'TEST_URL': 'https://test.example.com',
        'TEST_PAT_TOKEN': 'test-pat'
    })
    def test_from_env(self):
        config = AtlassianConfig.from_env('TEST')
        assert config.url == 'https://test.example.com'
        assert config.pat_token == 'test-pat'

    @patch.dict(os.environ, {
        'TEST_URL': 'https://test.example.com',
        'TEST_PAT_TOKEN': 'test-pat',
        'TEST_SSL_VERIFY': 'true'
    })
    def test_from_env_ssl_verify(self):
        config = AtlassianConfig.from_env('TEST')
        assert config.ssl_verify is True

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_missing_url(self):
        with pytest.raises(ConfigurationError):
            AtlassianConfig.from_env('MISSING')

    @patch.dict(os.environ, {'TEST_URL': 'https://test.example.com'}, clear=True)
    def test_from_env_missing_pat_token(self):
        with pytest.raises(ConfigurationError):
            AtlassianConfig.from_env('TEST')


class TestAtlassianClient:
    """Tests for AtlassianClient class."""

    def test_api_path(self):
        config = AtlassianConfig(
            url='https://jira.example.com',
            pat_token='token'
        )
        client = AtlassianClient(config)
        assert client.api_path('issue/TEST-1') == '/rest/api/2/issue/TEST-1'

    def test_api_version_is_v2(self):
        config = AtlassianConfig(
            url='https://jira.example.com',
            pat_token='token'
        )
        client = AtlassianClient(config)
        assert client.api_version == '2'

    def test_client_is_read_only(self):
        config = AtlassianConfig(
            url='https://jira.example.com',
            pat_token='token'
        )
        client = AtlassianClient(config)
        for method in ('post', 'put', 'delete', 'patch'):
            assert not hasattr(client, method)

    def test_api_path_strips_leading_slash(self):
        config = AtlassianConfig(
            url='https://jira.example.com',
            pat_token='token'
        )
        client = AtlassianClient(config)
        assert client.api_path('/issue/TEST-1') == '/rest/api/2/issue/TEST-1'

    @patch('requests.Session')
    def test_get_request(self, mock_session_class):
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'key': 'value'}
        mock_response.content = b'{"key": "value"}'
        mock_session.get.return_value = mock_response

        config = AtlassianConfig(
            url='https://jira.example.com',
            pat_token='token'
        )
        client = AtlassianClient(config)
        result = client.get('/test')
        assert result == {'key': 'value'}

    @patch('requests.Session')
    def test_handle_401_error(self, mock_session_class):
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {'message': 'Unauthorized'}
        mock_session.get.return_value = mock_response

        config = AtlassianConfig(
            url='https://jira.example.com',
            pat_token='token'
        )
        client = AtlassianClient(config)
        with pytest.raises(AuthenticationError):
            client.get('/test')

    @patch('requests.Session')
    def test_handle_404_error(self, mock_session_class):
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {'message': 'Not found'}
        mock_session.get.return_value = mock_response

        config = AtlassianConfig(
            url='https://jira.example.com',
            pat_token='token'
        )
        client = AtlassianClient(config)
        with pytest.raises(NotFoundError):
            client.get('/test')
