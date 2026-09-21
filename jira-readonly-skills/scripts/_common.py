"""Common utilities for the Jira Data Center read-only skill.

This module provides shared functionality used by all Jira scripts:
- Configuration management (PAT token authentication)
- Read-only HTTP client for Jira REST API v2
- Error handling
- Response formatting
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

# =============================================================================
# Auto-load .env file (with override=False to respect existing env vars)
# =============================================================================
# Find .env file in parent directory (jira-readonly-skills/.env)
_env_path = Path(__file__).parent.parent / '.env'
if _env_path.exists():
    # override=False ensures existing environment variables are NOT overwritten
    # Priority: explicit config > environment variables > .env file
    load_dotenv(dotenv_path=_env_path, override=False)


# Jira Data Center / Server uses REST API v2
JIRA_API_VERSION = "2"


# =============================================================================
# Error Classes
# =============================================================================

class ConfigurationError(Exception):
    """Raised when configuration is missing or invalid."""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class NotFoundError(Exception):
    """Raised when a resource is not found."""
    pass


class APIError(Exception):
    """Raised when the Jira API returns an error."""
    pass


class NetworkError(Exception):
    """Raised when network connectivity issues occur."""
    pass


# =============================================================================
# Response Formatting
# =============================================================================

def format_error_response(error_type: str, message: str, details: str = "") -> str:
    """Format an error as a JSON response.

    Args:
        error_type: Type of error (e.g., 'AuthenticationError', 'ValidationError')
        message: Main error message
        details: Additional error details (optional)

    Returns:
        JSON string with error information
    """
    error_data: Dict[str, Any] = {
        "success": False,
        "error": message,
        "error_type": error_type
    }
    if details:
        error_data["details"] = details
    return json.dumps(error_data, ensure_ascii=False, indent=2)


def format_json_response(data: Any) -> str:
    """Format data as a JSON string with UTF-8 encoding.

    Args:
        data: Data to serialize (dict, list, or other JSON-serializable type)

    Returns:
        JSON formatted string with proper UTF-8 encoding
    """
    return json.dumps(data, ensure_ascii=False, indent=2)


# =============================================================================
# Credentials Data Class
# =============================================================================

@dataclass
class AtlassianCredentials:
    """Credentials for a Jira Data Center / Server instance.

    When deployed in an Agent environment without environment variables, pass
    this object to skill functions to provide credentials programmatically.

    Authentication uses a Personal Access Token (PAT).
    """

    jira_url: Optional[str] = None
    jira_pat_token: Optional[str] = None
    jira_ssl_verify: bool = True

    def is_jira_available(self) -> bool:
        """Check if Jira credentials are complete.

        Returns:
            True if Jira can be used, False otherwise
        """
        return bool(self.jira_url) and bool(self.jira_pat_token)

    def get_unavailable_reason(self) -> Optional[str]:
        """Explain why Jira is unavailable, if it is.

        Returns:
            Reason string, or None if Jira is available
        """
        if not self.jira_url:
            return "Missing jira_url"
        if not self.jira_pat_token:
            return "Missing jira_pat_token"
        return None


# =============================================================================
# Configuration
# =============================================================================

class AtlassianConfig:
    """Configuration for Jira Data Center API authentication."""

    def __init__(
        self,
        url: str,
        pat_token: Optional[str] = None,
        ssl_verify: bool = True
    ):
        """Initialize configuration.

        Args:
            url: Base URL for the Jira instance
            pat_token: Personal Access Token for Data Center authentication
            ssl_verify: Whether to verify SSL certificates (default: True)
        """
        self.url = url.rstrip('/') if url else ""
        self.pat_token = pat_token
        self.ssl_verify = ssl_verify

    @classmethod
    def from_env(cls, prefix: str = "JIRA") -> "AtlassianConfig":
        """Load configuration from environment variables.

        Args:
            prefix: Prefix for environment variables (default: 'JIRA')

        Returns:
            AtlassianConfig instance with values from environment

        Raises:
            ConfigurationError: If required environment variables are missing
        """
        url = os.getenv(f"{prefix}_URL")
        pat_token = os.getenv(f"{prefix}_PAT_TOKEN")
        ssl_verify_str = os.getenv(f"{prefix}_SSL_VERIFY", "false").lower()
        ssl_verify = ssl_verify_str in ("true", "1", "yes")

        config = cls(
            url=url or "",
            pat_token=pat_token,
            ssl_verify=ssl_verify
        )
        config._validate(prefix)
        return config

    @classmethod
    def from_credentials(cls, credentials: AtlassianCredentials) -> "AtlassianConfig":
        """Create configuration from an AtlassianCredentials object.

        Args:
            credentials: AtlassianCredentials instance

        Returns:
            AtlassianConfig instance

        Raises:
            ConfigurationError: If credentials are incomplete
        """
        if not credentials.is_jira_available():
            raise ConfigurationError(
                "Jira credentials not provided or incomplete. "
                "Please provide jira_url and jira_pat_token."
            )
        return cls(
            url=credentials.jira_url or "",
            pat_token=credentials.jira_pat_token,
            ssl_verify=credentials.jira_ssl_verify
        )

    def _validate(self, prefix: str) -> None:
        """Validate configuration."""
        if not self.url:
            raise ConfigurationError(
                f"Missing required configuration: {prefix}_URL. "
                f"Please set this environment variable."
            )
        if not self.pat_token:
            raise ConfigurationError(
                f"Missing authentication credentials for {prefix}. "
                f"Please provide {prefix}_PAT_TOKEN (Personal Access Token)."
            )

    def get_auth_header(self) -> dict:
        """Get the Authorization header for PAT authentication."""
        if not self.pat_token:
            raise ConfigurationError("Cannot generate auth header: missing PAT token.")
        return {"Authorization": f"Bearer {self.pat_token}"}


# =============================================================================
# HTTP Client
# =============================================================================

class AtlassianClient:
    """Read-only HTTP client for Jira Data Center API requests."""

    def __init__(self, config: AtlassianConfig):
        """Initialize the client with configuration.

        Args:
            config: AtlassianConfig instance with URL and credentials
        """
        self.config = config
        self.api_version = JIRA_API_VERSION
        self.ssl_verify = config.ssl_verify
        self.session = requests.Session()
        self.session.headers.update(config.get_auth_header())
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def api_path(self, endpoint: str) -> str:
        """Build API path with the correct version.

        Args:
            endpoint: API endpoint (e.g., '/issue/PROJ-123')

        Returns:
            Full API path (e.g., '/rest/api/2/issue/PROJ-123')
        """
        endpoint = endpoint.lstrip('/')
        return f"/rest/api/{self.api_version}/{endpoint}"

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Perform a GET request."""
        url = f"{self.config.url}{path}"
        try:
            response = self.session.get(url, params=params, timeout=30, verify=self.ssl_verify)
            self._handle_error(response)
            return response.json() if response.content else {}
        except requests.exceptions.Timeout:
            raise NetworkError("Request timed out")
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"Connection failed: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error: {str(e)}")

    def _handle_error(self, response: requests.Response) -> None:
        """Handle HTTP error responses."""
        if response.status_code < 400:
            return

        error_message = ""
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                error_message = (
                    error_data.get("errorMessages", [""])[0] if "errorMessages" in error_data
                    else error_data.get("message", "")
                    or error_data.get("error", "")
                )
        except Exception:
            error_message = response.text or response.reason

        if response.status_code == 401:
            raise AuthenticationError(f"Authentication failed: {error_message}")
        elif response.status_code == 400:
            raise ValidationError(f"Invalid request: {error_message}")
        elif response.status_code == 404:
            raise NotFoundError(f"Resource not found: {error_message}")
        elif response.status_code == 403:
            raise AuthenticationError(f"Access forbidden: {error_message}")
        else:
            raise APIError(f"API error ({response.status_code}): {error_message}")


# =============================================================================
# Helper Functions
# =============================================================================

def get_jira_client(credentials: Optional[AtlassianCredentials] = None) -> AtlassianClient:
    """Get configured Jira client.

    Args:
        credentials: Optional AtlassianCredentials object. If not provided,
                    configuration will be loaded from environment variables.

    Returns:
        Configured AtlassianClient instance

    Raises:
        ConfigurationError: If configuration is missing or invalid
    """
    if credentials:
        config = AtlassianConfig.from_credentials(credentials)
    else:
        config = AtlassianConfig.from_env('JIRA')
    return AtlassianClient(config)


def check_available_skills(credentials: AtlassianCredentials) -> Dict[str, Any]:
    """Check whether the Jira skill is usable with the provided credentials.

    Args:
        credentials: AtlassianCredentials object

    Returns:
        Dictionary with availability information:
        {
            "available_services": ["jira"],
            "unavailable_services": {}
        }
        or, when credentials are incomplete:
        {
            "available_services": [],
            "unavailable_services": {"jira": "Missing jira_pat_token"}
        }
    """
    reason = credentials.get_unavailable_reason()
    if reason is None:
        return {"available_services": ["jira"], "unavailable_services": {}}
    return {"available_services": [], "unavailable_services": {"jira": reason}}


def simplify_issue(issue_data: Dict[str, Any]) -> Dict[str, Any]:
    """Simplify issue data to essential fields.

    Args:
        issue_data: Raw issue data from Jira API

    Returns:
        Simplified issue dictionary with essential fields
    """
    fields = issue_data.get('fields', {})

    assignee = fields.get('assignee')
    assignee_email = assignee.get('emailAddress', '') if assignee else None

    reporter = fields.get('reporter')
    reporter_email = reporter.get('emailAddress', '') if reporter else None

    status = fields.get('status', {})
    issue_type = fields.get('issuetype', {})
    priority = fields.get('priority', {})

    simplified = {
        'key': issue_data.get('key', ''),
        'id': issue_data.get('id', ''),
        'summary': fields.get('summary', ''),
        'description': fields.get('description', ''),
        'status': status.get('name', '') if status else '',
        'issue_type': issue_type.get('name', '') if issue_type else '',
        'priority': priority.get('name', '') if priority else '',
        'assignee': assignee_email,
        'reporter': reporter_email,
        'created': fields.get('created', ''),
        'updated': fields.get('updated', ''),
        'labels': fields.get('labels', []),
        'components': [c.get('name', '') for c in fields.get('components', [])],
    }

    custom_fields = {}
    for key, value in fields.items():
        if key.startswith('customfield_'):
            custom_fields[key] = value
    if custom_fields:
        simplified['custom_fields'] = custom_fields

    return simplified
