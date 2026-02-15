"""Tests for Linear integration tools."""

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.linear_tools import (
    create_linear_issue,
    list_linear_issues,
    update_linear_issue,
)


class TestCreateLinearIssue:
    """Tests for create_linear_issue tool."""

    @pytest.mark.asyncio
    async def test_create_issue_success(self):
        """Test creating a Linear issue successfully."""
        # Mock httpx responses
        mock_teams_response = MagicMock()
        mock_teams_response.json.return_value = {
            "data": {"teams": {"nodes": [{"id": "team-123", "name": "Engineering"}]}}
        }
        mock_teams_response.raise_for_status = MagicMock()

        mock_create_response = MagicMock()
        mock_create_response.json.return_value = {
            "data": {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "issue-456",
                        "identifier": "VEL-1",
                        "title": "Test Issue",
                        "url": "https://linear.app/velocity/issue/VEL-1",
                        "state": {"name": "Backlog"},
                    },
                }
            }
        }
        mock_create_response.raise_for_status = MagicMock()

        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True
            mock_settings.linear_api_key = "test-key"

            with patch("httpx.AsyncClient") as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(
                    side_effect=[mock_teams_response, mock_create_response]
                )
                mock_client.return_value = mock_context

                result = await create_linear_issue.handler(
                    {
                        "title": "Test Issue",
                        "description": "Test description",
                        "priority": 2,
                    }
                )

        assert result["content"][0]["type"] == "text"
        assert "VEL-1" in result["content"][0]["text"]
        assert "Test Issue" in result["content"][0]["text"]
        assert "✅" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_create_issue_missing_title(self):
        """Test creating issue without title returns error."""
        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True

            result = await create_linear_issue.handler({})

        assert result["content"][0]["type"] == "text"
        assert "Title is required" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_create_issue_not_configured(self):
        """Test creating issue when Linear not configured."""
        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = False

            result = await create_linear_issue.handler({"title": "Test"})

        assert result["content"][0]["type"] == "text"
        assert "not configured" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_create_issue_no_teams(self):
        """Test creating issue when no teams found."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"teams": {"nodes": []}}}
        mock_response.raise_for_status = MagicMock()

        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True
            mock_settings.linear_api_key = "test-key"

            with patch("httpx.AsyncClient") as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                mock_client.return_value = mock_context

                result = await create_linear_issue.handler({"title": "Test"})

        assert result["content"][0]["type"] == "text"
        assert "No teams found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_create_issue_api_error(self):
        """Test creating issue with API errors."""
        mock_teams_response = MagicMock()
        mock_teams_response.json.return_value = {
            "data": {"teams": {"nodes": [{"id": "team-123", "name": "Engineering"}]}}
        }
        mock_teams_response.raise_for_status = MagicMock()

        mock_error_response = MagicMock()
        mock_error_response.json.return_value = {
            "errors": [{"message": "Invalid input"}]
        }
        mock_error_response.raise_for_status = MagicMock()

        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True
            mock_settings.linear_api_key = "test-key"

            with patch("httpx.AsyncClient") as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(
                    side_effect=[mock_teams_response, mock_error_response]
                )
                mock_client.return_value = mock_context

                result = await create_linear_issue.handler({"title": "Test"})

        assert result["content"][0]["type"] == "text"
        assert "Linear API error" in result["content"][0]["text"]


class TestUpdateLinearIssue:
    """Tests for update_linear_issue tool."""

    @pytest.mark.asyncio
    async def test_update_issue_success(self):
        """Test updating a Linear issue successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "issueUpdate": {
                    "success": True,
                    "issue": {
                        "id": "issue-456",
                        "identifier": "VEL-1",
                        "title": "Updated Issue",
                        "url": "https://linear.app/velocity/issue/VEL-1",
                        "state": {"name": "In Progress"},
                        "assignee": {"name": "John Doe", "email": "john@example.com"},
                        "priority": 1,
                    },
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True
            mock_settings.linear_api_key = "test-key"

            with patch("httpx.AsyncClient") as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                mock_client.return_value = mock_context

                result = await update_linear_issue.handler(
                    {"issue_id": "VEL-1", "title": "Updated Issue", "priority": 1}
                )

        assert result["content"][0]["type"] == "text"
        assert "VEL-1" in result["content"][0]["text"]
        assert "Updated Issue" in result["content"][0]["text"]
        assert "✅" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_update_issue_missing_id(self):
        """Test updating issue without issue_id returns error."""
        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True

            result = await update_linear_issue.handler({})

        assert result["content"][0]["type"] == "text"
        assert "issue_id is required" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_update_issue_no_updates(self):
        """Test updating issue with no fields specified."""
        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True

            result = await update_linear_issue.handler({"issue_id": "VEL-1"})

        assert result["content"][0]["type"] == "text"
        assert "No updates specified" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_update_issue_with_assignee(self):
        """Test updating issue with assignee by email."""
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            "data": {
                "users": {
                    "nodes": [
                        {"id": "user-789", "name": "John Doe", "email": "john@example.com"}
                    ]
                }
            }
        }
        mock_user_response.raise_for_status = MagicMock()

        mock_update_response = MagicMock()
        mock_update_response.json.return_value = {
            "data": {
                "issueUpdate": {
                    "success": True,
                    "issue": {
                        "id": "issue-456",
                        "identifier": "VEL-1",
                        "title": "Test Issue",
                        "url": "https://linear.app/velocity/issue/VEL-1",
                        "state": {"name": "Backlog"},
                        "assignee": {"name": "John Doe", "email": "john@example.com"},
                        "priority": 0,
                    },
                }
            }
        }
        mock_update_response.raise_for_status = MagicMock()

        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True
            mock_settings.linear_api_key = "test-key"

            with patch("httpx.AsyncClient") as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(
                    side_effect=[mock_user_response, mock_update_response]
                )
                mock_client.return_value = mock_context

                result = await update_linear_issue.handler(
                    {"issue_id": "VEL-1", "assignee_email": "john@example.com"}
                )

        assert result["content"][0]["type"] == "text"
        assert "John Doe" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_update_issue_user_not_found(self):
        """Test updating issue with non-existent user."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"users": {"nodes": []}}}
        mock_response.raise_for_status = MagicMock()

        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True
            mock_settings.linear_api_key = "test-key"

            with patch("httpx.AsyncClient") as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                mock_client.return_value = mock_context

                result = await update_linear_issue.handler(
                    {"issue_id": "VEL-1", "assignee_email": "nonexistent@example.com"}
                )

        assert result["content"][0]["type"] == "text"
        assert "not found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_update_issue_with_state(self):
        """Test updating issue with state by name."""
        mock_states_response = MagicMock()
        mock_states_response.json.return_value = {
            "data": {
                "workflowStates": {
                    "nodes": [
                        {"id": "state-1", "name": "Backlog"},
                        {"id": "state-2", "name": "In Progress"},
                        {"id": "state-3", "name": "Done"},
                    ]
                }
            }
        }
        mock_states_response.raise_for_status = MagicMock()

        mock_update_response = MagicMock()
        mock_update_response.json.return_value = {
            "data": {
                "issueUpdate": {
                    "success": True,
                    "issue": {
                        "id": "issue-456",
                        "identifier": "VEL-1",
                        "title": "Test Issue",
                        "url": "https://linear.app/velocity/issue/VEL-1",
                        "state": {"name": "In Progress"},
                        "priority": 0,
                    },
                }
            }
        }
        mock_update_response.raise_for_status = MagicMock()

        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True
            mock_settings.linear_api_key = "test-key"

            with patch("httpx.AsyncClient") as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(
                    side_effect=[mock_states_response, mock_update_response]
                )
                mock_client.return_value = mock_context

                result = await update_linear_issue.handler(
                    {"issue_id": "VEL-1", "state_name": "In Progress"}
                )

        assert result["content"][0]["type"] == "text"
        assert "In Progress" in result["content"][0]["text"]


class TestListLinearIssues:
    """Tests for list_linear_issues tool."""

    @pytest.mark.asyncio
    async def test_list_issues_success(self):
        """Test listing Linear issues successfully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "issues": {
                    "nodes": [
                        {
                            "id": "issue-1",
                            "identifier": "VEL-1",
                            "title": "First Issue",
                            "description": "Description 1",
                            "state": {"name": "Backlog"},
                            "priority": 2,
                            "assignee": {"name": "John"},
                            "createdAt": "2024-01-01",
                            "updatedAt": "2024-01-02",
                            "url": "https://linear.app/velocity/issue/VEL-1",
                        },
                        {
                            "id": "issue-2",
                            "identifier": "VEL-2",
                            "title": "Second Issue",
                            "description": "Description 2",
                            "state": {"name": "In Progress"},
                            "priority": 1,
                            "assignee": None,
                            "createdAt": "2024-01-03",
                            "updatedAt": "2024-01-04",
                            "url": "https://linear.app/velocity/issue/VEL-2",
                        },
                    ]
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True
            mock_settings.linear_api_key = "test-key"

            with patch("httpx.AsyncClient") as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                mock_client.return_value = mock_context

                result = await list_linear_issues.handler({"limit": 20, "filter": "active"})

        assert result["content"][0]["type"] == "text"
        assert "VEL-1" in result["content"][0]["text"]
        assert "VEL-2" in result["content"][0]["text"]
        assert "First Issue" in result["content"][0]["text"]
        assert "Second Issue" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_list_issues_no_issues(self):
        """Test listing issues when none exist."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"issues": {"nodes": []}}}
        mock_response.raise_for_status = MagicMock()

        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True
            mock_settings.linear_api_key = "test-key"

            with patch("httpx.AsyncClient") as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                mock_client.return_value = mock_context

                result = await list_linear_issues.handler({})

        assert result["content"][0]["type"] == "text"
        assert "No issues found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_list_issues_not_configured(self):
        """Test listing issues when Linear not configured."""
        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = False

            result = await list_linear_issues.handler({})

        assert result["content"][0]["type"] == "text"
        assert "not configured" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_list_issues_api_error(self):
        """Test listing issues with API errors."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"errors": [{"message": "API error"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("app.agents.linear_tools.settings") as mock_settings:
            mock_settings.linear_configured = True
            mock_settings.linear_api_key = "test-key"

            with patch("httpx.AsyncClient") as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                mock_client.return_value = mock_context

                result = await list_linear_issues.handler({})

        assert result["content"][0]["type"] == "text"
        assert "Linear API error" in result["content"][0]["text"]
