"""Linear integration tools — create, read, update Linear issues via GraphQL.

These tools avoid the OAuth login flow by using direct GraphQL API access.
"""

from __future__ import annotations

import logging

from claude_agent_sdk import tool

from app.config import settings

logger = logging.getLogger(__name__)


@tool(
    "create_linear_issue",
    "Create a new Linear issue/ticket with title, description, priority",
    {
        "title": str,  # Issue title (required)
        "description": str,  # Issue description (optional)
        "priority": int,  # Priority 0-4: 0=No priority, 1=Urgent, 2=High, 3=Normal, 4=Low
    },
)
async def create_linear_issue(args: dict) -> dict:
    """Create a new Linear issue via GraphQL mutation."""
    import httpx

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    title = args.get("title")
    if not title:
        return {"content": [{"type": "text", "text": "Title is required"}]}

    description = args.get("description", "")
    priority = args.get("priority", 0)

    # Get the first team
    teams_query = "query { teams { nodes { id name } } }"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": teams_query},
                headers={"Authorization": settings.linear_api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            teams = data.get("data", {}).get("teams", {}).get("nodes", [])
            if not teams:
                return {"content": [{"type": "text", "text": "No teams found"}]}
            team_id = teams[0]["id"]
    except httpx.HTTPError as e:
        logger.exception("HTTP error fetching teams")
        return {"content": [{"type": "text", "text": f"Network error: {str(e)}"}]}
    except Exception as e:
        logger.exception("Error fetching teams")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

    # Use GraphQL variables to prevent injection
    mutation = """
    mutation CreateIssue($teamId: String!, $title: String!, $description: String, $priority: Int) {
      issueCreate(input: {
        teamId: $teamId
        title: $title
        description: $description
        priority: $priority
      }) {
        success
        issue {
          id
          identifier
          title
          url
          state { name }
        }
      }
    }
    """

    variables = {
        "teamId": team_id,
        "title": title,
        "description": description,
        "priority": priority,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": mutation, "variables": variables},
                headers={"Authorization": settings.linear_api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                return {
                    "content": [
                        {"type": "text", "text": f"Linear API error: {data['errors']}"}
                    ]
                }

            result = data.get("data", {}).get("issueCreate", {})
            if result.get("success"):
                issue = result.get("issue", {})
                msg = f"✅ Created issue [{issue['identifier']}]({issue['url']}): {issue['title']}\n"
                msg += f"State: {issue['state']['name']}"
                return {"content": [{"type": "text", "text": msg}]}
            else:
                return {"content": [{"type": "text", "text": "Failed to create issue"}]}
    except httpx.HTTPError as e:
        logger.exception("HTTP error creating Linear issue")
        return {"content": [{"type": "text", "text": f"Network error: {str(e)}"}]}
    except Exception as e:
        logger.exception("Error creating Linear issue")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool(
    "update_linear_issue",
    "Update an existing Linear issue - assign to engineer, change priority, update status",
    {
        "issue_id": str,  # Issue ID or identifier (e.g., "VEL-123")
        "assignee_email": str,  # Email of user to assign (optional)
        "priority": int,  # New priority 0-4 (optional)
        "state_name": str,  # New state like "In Progress", "Done" (optional)
        "title": str,  # New title (optional)
        "description": str,  # New description (optional)
    },
)
async def update_linear_issue(args: dict) -> dict:
    """Update a Linear issue via GraphQL mutation."""
    import httpx

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    issue_id = args.get("issue_id")
    if not issue_id:
        return {"content": [{"type": "text", "text": "issue_id is required"}]}

    assignee_email = args.get("assignee_email")
    priority = args.get("priority")
    state_name = args.get("state_name")
    title = args.get("title")
    description = args.get("description")

    # Build update input object
    input_obj: dict[str, any] = {}

    if title:
        input_obj["title"] = title

    if description:
        input_obj["description"] = description

    if priority is not None:
        input_obj["priority"] = priority

    # Get assignee ID from email
    if assignee_email:
        users_query = f"""
        query {{
          users(filter: {{ email: {{ eq: "{assignee_email}" }} }}) {{
            nodes {{ id name email }}
          }}
        }}
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.linear.app/graphql",
                    json={"query": users_query},
                    headers={"Authorization": settings.linear_api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                users = data.get("data", {}).get("users", {}).get("nodes", [])
                if users:
                    input_obj["assigneeId"] = users[0]["id"]
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"User with email {assignee_email} not found",
                            }
                        ]
                    }
        except httpx.HTTPError as e:
            logger.exception("HTTP error fetching user")
            return {"content": [{"type": "text", "text": f"Network error: {str(e)}"}]}
        except Exception as e:
            logger.exception("Error fetching user")
            return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

    # Get state ID from name
    if state_name:
        states_query = """
        query {
          workflowStates {
            nodes { id name }
          }
        }
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.linear.app/graphql",
                    json={"query": states_query},
                    headers={"Authorization": settings.linear_api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                states = data.get("data", {}).get("workflowStates", {}).get("nodes", [])
                matching_state = next(
                    (s for s in states if s["name"].lower() == state_name.lower()), None
                )
                if matching_state:
                    input_obj["stateId"] = matching_state["id"]
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"State '{state_name}' not found",
                            }
                        ]
                    }
        except httpx.HTTPError as e:
            logger.exception("HTTP error fetching states")
            return {"content": [{"type": "text", "text": f"Network error: {str(e)}"}]}
        except Exception as e:
            logger.exception("Error fetching states")
            return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

    if not input_obj:
        return {"content": [{"type": "text", "text": "No updates specified"}]}

    # Use GraphQL variables to prevent injection
    mutation = """
    mutation UpdateIssue($issueId: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $issueId, input: $input) {
        success
        issue {
          id
          identifier
          title
          url
          state { name }
          assignee { name email }
          priority
        }
      }
    }
    """

    variables = {
        "issueId": issue_id,
        "input": input_obj,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": mutation, "variables": variables},
                headers={"Authorization": settings.linear_api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                return {
                    "content": [
                        {"type": "text", "text": f"Linear API error: {data['errors']}"}
                    ]
                }

            result = data.get("data", {}).get("issueUpdate", {})
            if result.get("success"):
                issue = result.get("issue", {})
                msg = f"✅ Updated issue [{issue['identifier']}]({issue['url']})\n"
                msg += f"Title: {issue['title']}\n"
                msg += f"State: {issue['state']['name']}\n"
                if issue.get("assignee"):
                    msg += f"Assigned to: {issue['assignee']['name']} ({issue['assignee']['email']})\n"
                msg += f"Priority: {issue.get('priority', 0)}"
                return {"content": [{"type": "text", "text": msg}]}
            else:
                return {"content": [{"type": "text", "text": "Failed to update issue"}]}
    except httpx.HTTPError as e:
        logger.exception("HTTP error updating Linear issue")
        return {"content": [{"type": "text", "text": f"Network error: {str(e)}"}]}
    except Exception as e:
        logger.exception("Error updating Linear issue")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool(
    "list_linear_issues",
    "Get issues from Linear backlog with optional filtering",
    {
        "limit": int,  # Number of issues to return (default 20)
        "filter": str,  # Optional filter: "active", "backlog", "all" (default "active")
    },
)
async def list_linear_issues(args: dict) -> dict:
    """Query Linear issues via GraphQL API."""
    import httpx

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    limit = args.get("limit", 20)
    filter_type = args.get("filter", "active")

    # Build GraphQL query
    filter_clause = ""
    if filter_type == "active":
        filter_clause = ', filter: { state: { type: { nin: ["completed", "canceled"] } } }'
    elif filter_type == "backlog":
        filter_clause = ', filter: { state: { type: { eq: "backlog" } } }'

    query = f"""
    query {{
      issues(first: {limit}{filter_clause}) {{
        nodes {{
          id
          identifier
          title
          description
          state {{ name }}
          priority
          assignee {{ name }}
          createdAt
          updatedAt
          url
        }}
      }}
    }}
    """

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": query},
                headers={"Authorization": settings.linear_api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Linear API error: {data['errors']}",
                        }
                    ]
                }

            issues = data.get("data", {}).get("issues", {}).get("nodes", [])
            if not issues:
                return {"content": [{"type": "text", "text": "No issues found"}]}

            # Format as markdown
            result = f"# Linear Issues ({filter_type})\n\n"
            for issue in issues:
                result += f"## [{issue['identifier']}]({issue['url']}) {issue['title']}\n"
                result += f"- **State**: {issue['state']['name']}\n"
                result += f"- **Priority**: {issue.get('priority', 'None')}\n"
                if issue.get("assignee"):
                    result += f"- **Assignee**: {issue['assignee']['name']}\n"
                if issue.get("description"):
                    desc = issue["description"][:200]
                    result += f"- **Description**: {desc}...\n"
                result += "\n"

            return {"content": [{"type": "text", "text": result}]}
    except Exception as e:
        logger.exception("Error fetching Linear issues")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}
