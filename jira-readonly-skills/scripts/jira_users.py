"""Jira user tools.

Tools:
    - jira_get_user_profile: Get user profile by identifier
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from typing import Any, Dict, Optional

from _common import (
    AtlassianCredentials,
    get_jira_client,
    format_json_response,
    format_error_response,
    ConfigurationError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    APIError,
    NetworkError,
)


def _simplify_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Simplify user data to essential fields."""
    return {
        'username': user_data.get('name', ''),
        'key': user_data.get('key', ''),
        'display_name': user_data.get('displayName', ''),
        'email': user_data.get('emailAddress', ''),
        'active': user_data.get('active', False),
        'timezone': user_data.get('timeZone', ''),
        'locale': user_data.get('locale', '')
    }


def jira_get_user_profile(
    user_identifier: str,
    credentials: Optional[AtlassianCredentials] = None
) -> str:
    """Get a Jira Data Center user profile by identifier.

    Lookup order:
    1. Exact username lookup (GET /user?username=...)
    2. User search by username, display name, or email (GET /user/search?username=...)
    3. User picker (GET /user/picker?query=...), then exact lookup of the top match

    Args:
        user_identifier: Username, email address, or display name
        credentials: Optional AtlassianCredentials for Agent environments.
                    If not provided, uses environment variables.

    Returns:
        JSON string with user profile data or error information
    """
    try:
        client = get_jira_client(credentials)

        if not user_identifier:
            raise ValidationError('user_identifier is required')

        user_data = None

        # Method 1: Exact username lookup
        try:
            params = {'username': user_identifier}
            user_data = client.get(client.api_path('user'), params=params)
        except (NotFoundError, APIError, ValidationError):
            pass

        # Method 2: User search (matches username, display name, and email)
        if not user_data:
            try:
                params = {'username': user_identifier, 'maxResults': 1}
                response = client.get(client.api_path('user/search'), params=params)
                if response and len(response) > 0:
                    user_data = response[0]
            except (NotFoundError, APIError, ValidationError):
                pass

        # Method 3: User picker, then fetch the full profile of the top match
        if not user_data:
            try:
                params = {'query': user_identifier, 'maxResults': 1}
                response = client.get(client.api_path('user/picker'), params=params)
                users = response.get('users', [])
                if users and users[0].get('name'):
                    params = {'username': users[0].get('name')}
                    user_data = client.get(client.api_path('user'), params=params)
            except (NotFoundError, APIError, ValidationError):
                pass

        if not user_data:
            raise NotFoundError(f'User not found: {user_identifier}')

        simplified = _simplify_user(user_data)
        return format_json_response(simplified)

    except ConfigurationError as e:
        return format_error_response('ConfigurationError', str(e))
    except AuthenticationError as e:
        return format_error_response('AuthenticationError', str(e))
    except ValidationError as e:
        return format_error_response('ValidationError', str(e))
    except NotFoundError as e:
        return format_error_response('NotFoundError', str(e))
    except (APIError, NetworkError) as e:
        return format_error_response(type(e).__name__, str(e))
    except Exception as e:
        return format_error_response('UnexpectedError', f'Unexpected error: {str(e)}')
