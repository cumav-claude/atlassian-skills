"""Tests for AtlassianCredentials and parameter-based configuration."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'jira-readonly-skills' / 'scripts'))

import pytest
from _common import (
    AtlassianCredentials,
    AtlassianConfig,
    check_available_skills,
    ConfigurationError
)


class TestAtlassianCredentials:
    """Test AtlassianCredentials dataclass."""

    def test_jira_available_with_pat(self):
        """Test Jira is available with URL and PAT token."""
        creds = AtlassianCredentials(
            jira_url="https://jira.company.com",
            jira_pat_token="token123"
        )
        assert creds.is_jira_available() is True
        assert creds.get_unavailable_reason() is None

    def test_jira_unavailable_missing_url(self):
        """Test Jira is unavailable without URL."""
        creds = AtlassianCredentials(jira_pat_token="token123")
        assert creds.is_jira_available() is False
        assert creds.get_unavailable_reason() == "Missing jira_url"

    def test_jira_unavailable_missing_token(self):
        """Test Jira is unavailable without PAT token."""
        creds = AtlassianCredentials(jira_url="https://jira.company.com")
        assert creds.is_jira_available() is False
        assert creds.get_unavailable_reason() == "Missing jira_pat_token"

    def test_ssl_verify_defaults_true(self):
        creds = AtlassianCredentials(
            jira_url="https://jira.company.com",
            jira_pat_token="token123"
        )
        assert creds.jira_ssl_verify is True


class TestAtlassianConfigFromCredentials:
    """Test AtlassianConfig.from_credentials() method."""

    def test_from_credentials_pat(self):
        """Test creating config from credentials with PAT."""
        creds = AtlassianCredentials(
            jira_url="https://jira.company.com",
            jira_pat_token="token123"
        )
        config = AtlassianConfig.from_credentials(creds)
        assert config.url == "https://jira.company.com"
        assert config.pat_token == "token123"

    def test_from_credentials_missing(self):
        """Test error when credentials are missing."""
        creds = AtlassianCredentials()
        with pytest.raises(ConfigurationError) as exc_info:
            AtlassianConfig.from_credentials(creds)
        assert "Jira credentials not provided" in str(exc_info.value)

    def test_from_credentials_with_ssl_verify(self):
        """Test SSL verify flag is passed through."""
        creds = AtlassianCredentials(
            jira_url="https://jira.company.com",
            jira_pat_token="token123",
            jira_ssl_verify=False
        )
        config = AtlassianConfig.from_credentials(creds)
        assert config.ssl_verify is False


class TestCheckAvailableSkills:
    """Test check_available_skills() helper function."""

    def test_jira_available(self):
        creds = AtlassianCredentials(
            jira_url="https://jira.company.com",
            jira_pat_token="token1"
        )
        result = check_available_skills(creds)
        assert result["available_services"] == ["jira"]
        assert result["unavailable_services"] == {}

    def test_jira_unavailable(self):
        creds = AtlassianCredentials()
        result = check_available_skills(creds)
        assert result["available_services"] == []
        assert result["unavailable_services"] == {"jira": "Missing jira_url"}
