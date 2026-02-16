"""Linear integration tools — create, read, update Linear issues via GraphQL.

These tools avoid the OAuth login flow by using direct GraphQL API access.
"""

from __future__ import annotations

import logging

from claude_agent_sdk import tool

from app.config import settings
from app.redis_client import cache_get, cache_set

logger = logging.getLogger(__name__)

# Cache TTLs
CACHE_TTL_LINEAR_METADATA = 3600  # 1 hour for team/state metadata


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

    # Get the first team (with Redis caching)
    team_id = await cache_get("linear:team:first")
    if team_id is None:
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
                # Cache team ID for 1 hour
                await cache_set("linear:team:first", team_id, ttl=CACHE_TTL_LINEAR_METADATA)
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

    # Get state ID from name (with Redis caching)
    if state_name:
        # Try to get cached states
        states = await cache_get("linear:workflow_states")
        if states is None:
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
                    # Cache states for 1 hour
                    await cache_set("linear:workflow_states", states, ttl=CACHE_TTL_LINEAR_METADATA)
            except httpx.HTTPError as e:
                logger.exception("HTTP error fetching states")
                return {"content": [{"type": "text", "text": f"Network error: {str(e)}"}]}
            except Exception as e:
                logger.exception("Error fetching states")
                return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

        # Find matching state
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


@tool(
    "get_linear_issue_by_id",
    "Get a single Linear issue with full details including comments, relations, and history",
    {
        "issue_id": str,  # Issue ID or identifier (e.g., "VEL-123")
    },
)
async def get_linear_issue_by_id(args: dict) -> dict:
    """Get detailed information about a single Linear issue."""
    import httpx

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    issue_id = args.get("issue_id")
    if not issue_id:
        return {"content": [{"type": "text", "text": "issue_id is required"}]}

    # GraphQL query for full issue details
    query = """
    query GetIssue($id: String!) {
      issue(id: $id) {
        id
        identifier
        title
        description
        state { name type }
        priority
        estimate
        assignee { name email }
        creator { name email }
        createdAt
        updatedAt
        url
        comments { nodes { body createdAt user { name } } }
        relations { nodes { type relatedIssue { identifier title } } }
        parent { identifier title }
        children { nodes { identifier title } }
      }
    }
    """

    variables = {"id": issue_id}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": query, "variables": variables},
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

            issue = data.get("data", {}).get("issue")
            if not issue:
                return {"content": [{"type": "text", "text": f"Issue {issue_id} not found"}]}

            # Format as detailed markdown
            result = f"# [{issue['identifier']}]({issue['url']}) {issue['title']}\n\n"
            result += f"**State:** {issue['state']['name']} ({issue['state']['type']})\n"
            result += f"**Priority:** {issue.get('priority', 'None')}\n"
            result += f"**Estimate:** {issue.get('estimate', 'None')} points\n"

            if issue.get("assignee"):
                result += f"**Assigned to:** {issue['assignee']['name']} ({issue['assignee']['email']})\n"
            if issue.get("creator"):
                result += f"**Created by:** {issue['creator']['name']}\n"

            result += f"\n## Description\n{issue.get('description', 'No description')}\n\n"

            # Parent/children
            if issue.get("parent"):
                result += f"**Parent:** [{issue['parent']['identifier']}] {issue['parent']['title']}\n"
            if issue.get("children", {}).get("nodes"):
                result += "**Children:**\n"
                for child in issue['children']['nodes']:
                    result += f"- [{child['identifier']}] {child['title']}\n"
                result += "\n"

            # Relations (blockers/blocked by)
            if issue.get("relations", {}).get("nodes"):
                result += "## Relations\n"
                for rel in issue['relations']['nodes']:
                    related = rel['relatedIssue']
                    result += f"- **{rel['type']}:** [{related['identifier']}] {related['title']}\n"
                result += "\n"

            # Comments
            if issue.get("comments", {}).get("nodes"):
                result += f"## Comments ({len(issue['comments']['nodes'])})\n"
                for comment in issue['comments']['nodes'][:5]:  # Show first 5
                    result += f"\n**{comment['user']['name']}** ({comment['createdAt'][:10]}):\n"
                    result += f"{comment['body'][:200]}\n"

            return {"content": [{"type": "text", "text": result}]}
    except Exception as e:
        logger.exception("Error fetching Linear issue by ID")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool(
    "search_linear_issues_advanced",
    "Advanced search for Linear issues with filtering by assignee, labels, project, milestone, estimate, date ranges",
    {
        "query": str,  # Text search query (optional)
        "assignee_email": str,  # Filter by assignee email (optional)
        "state_type": str,  # Filter by state type: backlog, unstarted, started, completed, canceled (optional)
        "priority": int,  # Filter by priority 1-4 (optional)
        "has_estimate": bool,  # Filter issues with/without estimate (optional)
        "limit": int,  # Max results (default 20)
    },
)
async def search_linear_issues_advanced(args: dict) -> dict:
    """Advanced search for Linear issues with multiple filters."""
    import httpx

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    query_text = args.get("query", "")
    assignee_email = args.get("assignee_email")
    state_type = args.get("state_type")
    priority = args.get("priority")
    has_estimate = args.get("has_estimate")
    limit = args.get("limit", 20)

    # Build filter object
    filters = []
    if state_type:
        filters.append(f'state: {{ type: {{ eq: "{state_type}" }} }}')
    if priority:
        filters.append(f'priority: {{ eq: {priority} }}')
    if has_estimate is not None:
        if has_estimate:
            filters.append('estimate: { gt: 0 }')
        else:
            filters.append('estimate: { null: true }')

    # Get assignee ID from email if provided
    assignee_id = None
    if assignee_email:
        users_query = f"""
        query {{
          users(filter: {{ email: {{ eq: "{assignee_email}" }} }}) {{
            nodes {{ id }}
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
                    assignee_id = users[0]["id"]
                    filters.append(f'assignee: {{ id: {{ eq: "{assignee_id}" }} }}')
        except Exception as e:
            logger.warning(f"Error fetching user: {e}")

    filter_clause = ""
    if filters:
        filter_clause = f', filter: {{ {", ".join(filters)} }}'

    # Build main query
    query = f"""
    query {{
      issues(first: {limit}{filter_clause}) {{
        nodes {{
          identifier
          title
          state {{ name }}
          priority
          estimate
          assignee {{ name }}
          createdAt
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
                        {"type": "text", "text": f"Linear API error: {data['errors']}"}
                    ]
                }

            issues = data.get("data", {}).get("issues", {}).get("nodes", [])

            # Filter by text query if provided (client-side filtering)
            if query_text:
                issues = [
                    issue for issue in issues
                    if query_text.lower() in issue['title'].lower()
                ]

            if not issues:
                return {"content": [{"type": "text", "text": "No issues found matching filters"}]}

            # Format results
            result = f"# Search Results ({len(issues)} issues)\n\n"
            for issue in issues:
                result += f"## [{issue['identifier']}]({issue['url']}) {issue['title']}\n"
                result += f"- **State:** {issue['state']['name']}\n"
                result += f"- **Priority:** {issue.get('priority', 'None')}\n"
                result += f"- **Estimate:** {issue.get('estimate', 'None')} pts\n"
                if issue.get("assignee"):
                    result += f"- **Assignee:** {issue['assignee']['name']}\n"
                result += "\n"

            return {"content": [{"type": "text", "text": result}]}
    except Exception as e:
        logger.exception("Error searching Linear issues")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool(
    "add_linear_comment",
    "Add a comment to a Linear issue for agent notes or updates",
    {
        "issue_id": str,  # Issue ID or identifier (e.g., "VEL-123")
        "comment": str,  # Comment text
    },
)
async def add_linear_comment(args: dict) -> dict:
    """Add a comment to a Linear issue."""
    import httpx

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    issue_id = args.get("issue_id")
    comment_text = args.get("comment")

    if not issue_id or not comment_text:
        return {"content": [{"type": "text", "text": "issue_id and comment are required"}]}

    mutation = """
    mutation CreateComment($issueId: String!, $body: String!) {
      commentCreate(input: { issueId: $issueId, body: $body }) {
        success
        comment {
          id
          body
          createdAt
        }
      }
    }
    """

    variables = {"issueId": issue_id, "body": comment_text}

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

            result = data.get("data", {}).get("commentCreate", {})
            if result.get("success"):
                comment = result.get("comment", {})
                return {"content": [{"type": "text", "text": f"✅ Comment added to issue {issue_id}"}]}
            else:
                return {"content": [{"type": "text", "text": "Failed to add comment"}]}
    except Exception as e:
        logger.exception("Error adding Linear comment")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool(
    "get_linear_project_status",
    "Get project or milestone progress metrics including completion percentage and issue breakdown",
    {
        "project_name": str,  # Project or milestone name (optional, returns all if not specified)
    },
)
async def get_linear_project_status(args: dict) -> dict:
    """Get progress metrics for Linear projects/milestones."""
    import httpx

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    project_name = args.get("project_name")

    # Query projects with issue counts
    query = """
    query {
      projects {
        nodes {
          id
          name
          state
          progress
          startDate
          targetDate
          issues {
            nodes {
              state { type }
            }
          }
        }
      }
    }
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
                        {"type": "text", "text": f"Linear API error: {data['errors']}"}
                    ]
                }

            projects = data.get("data", {}).get("projects", {}).get("nodes", [])

            # Filter by project name if provided
            if project_name:
                projects = [p for p in projects if project_name.lower() in p['name'].lower()]

            if not projects:
                return {"content": [{"type": "text", "text": "No projects found"}]}

            # Format results
            result = f"# Project Status ({len(projects)} projects)\n\n"
            for project in projects:
                result += f"## {project['name']}\n"
                result += f"**State:** {project['state']}\n"
                result += f"**Progress:** {project.get('progress', 0):.0f}%\n"
                if project.get("startDate"):
                    result += f"**Start Date:** {project['startDate']}\n"
                if project.get("targetDate"):
                    result += f"**Target Date:** {project['targetDate']}\n"

                # Count issues by state
                issues = project.get("issues", {}).get("nodes", [])
                total = len(issues)
                completed = sum(1 for i in issues if i['state']['type'] == 'completed')
                in_progress = sum(1 for i in issues if i['state']['type'] == 'started')
                backlog = sum(1 for i in issues if i['state']['type'] in ['backlog', 'unstarted'])

                result += f"\n**Issues:** {total} total\n"
                result += f"- ✅ Completed: {completed}\n"
                result += f"- 🔄 In Progress: {in_progress}\n"
                result += f"- 📋 Backlog: {backlog}\n\n"

            return {"content": [{"type": "text", "text": result}]}
    except Exception as e:
        logger.exception("Error fetching project status")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool(
    "bulk_update_linear_issues",
    "Update multiple Linear issues at once for sprint planning",
    {
        "issue_ids": str,  # Comma-separated issue IDs or identifiers
        "priority": int,  # New priority for all issues (optional)
        "state_name": str,  # New state name (e.g., "In Progress") (optional)
        "estimate": int,  # New estimate in points (optional)
    },
)
async def bulk_update_linear_issues(args: dict) -> dict:
    """Bulk update multiple Linear issues."""
    import httpx

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    issue_ids_str = args.get("issue_ids", "")
    if not issue_ids_str:
        return {"content": [{"type": "text", "text": "issue_ids is required (comma-separated)"}]}

    issue_ids = [id.strip() for id in issue_ids_str.split(",")]
    priority = args.get("priority")
    state_name = args.get("state_name")
    estimate = args.get("estimate")

    # Build update input
    input_obj = {}
    if priority is not None:
        input_obj["priority"] = priority
    if estimate is not None:
        input_obj["estimate"] = estimate

    # Get state ID if state_name provided
    if state_name:
        states = await cache_get("linear:workflow_states")
        if states is None:
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
                    await cache_set("linear:workflow_states", states, ttl=CACHE_TTL_LINEAR_METADATA)
            except Exception as e:
                return {"content": [{"type": "text", "text": f"Error fetching states: {e}"}]}

        matching_state = next(
            (s for s in states if s["name"].lower() == state_name.lower()), None
        )
        if matching_state:
            input_obj["stateId"] = matching_state["id"]
        else:
            return {"content": [{"type": "text", "text": f"State '{state_name}' not found"}]}

    if not input_obj:
        return {"content": [{"type": "text", "text": "No updates specified"}]}

    # Update each issue
    updated = []
    failed = []

    mutation = """
    mutation UpdateIssue($issueId: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $issueId, input: $input) {
        success
        issue { identifier }
      }
    }
    """

    try:
        async with httpx.AsyncClient() as client:
            for issue_id in issue_ids:
                variables = {"issueId": issue_id, "input": input_obj}
                response = await client.post(
                    "https://api.linear.app/graphql",
                    json={"query": mutation, "variables": variables},
                    headers={"Authorization": settings.linear_api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    failed.append(issue_id)
                else:
                    result = data.get("data", {}).get("issueUpdate", {})
                    if result.get("success"):
                        updated.append(issue_id)
                    else:
                        failed.append(issue_id)

        # Format results
        result_text = f"# Bulk Update Complete\n\n"
        result_text += f"✅ Updated: {len(updated)} issues\n"
        if updated:
            result_text += f"   - {', '.join(updated)}\n"
        if failed:
            result_text += f"\n❌ Failed: {len(failed)} issues\n"
            result_text += f"   - {', '.join(failed)}\n"

        return {"content": [{"type": "text", "text": result_text}]}
    except Exception as e:
        logger.exception("Error bulk updating issues")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool(
    "calculate_sprint_velocity",
    "Analyze completed issues per sprint to calculate team velocity and trend",
    {
        "num_sprints": int,  # Number of past sprints to analyze (default 3)
    },
)
async def calculate_sprint_velocity(args: dict) -> dict:
    """Calculate sprint velocity based on completed issues."""
    import httpx
    from datetime import datetime, timedelta

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    num_sprints = args.get("num_sprints", 3)

    # Query completed issues from the last num_sprints * 2 weeks
    days_back = num_sprints * 14  # Assume 2-week sprints
    cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()

    query = f"""
    query {{
      issues(
        filter: {{
          state: {{ type: {{ eq: "completed" }} }}
          completedAt: {{ gte: "{cutoff_date}" }}
        }}
      ) {{
        nodes {{
          identifier
          estimate
          completedAt
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
                        {"type": "text", "text": f"Linear API error: {data['errors']}"}
                    ]
                }

            issues = data.get("data", {}).get("issues", {}).get("nodes", [])

            if not issues:
                return {"content": [{"type": "text", "text": "No completed issues found in the time range"}]}

            # Group issues by 2-week sprints
            sprints = {}
            for issue in issues:
                if not issue.get("estimate"):
                    continue  # Skip unestimated issues

                completed_date = datetime.fromisoformat(issue["completedAt"].replace("Z", "+00:00"))
                # Calculate sprint number (every 2 weeks from now)
                days_ago = (datetime.now().astimezone() - completed_date).days
                sprint_num = days_ago // 14

                if sprint_num not in sprints:
                    sprints[sprint_num] = {"points": 0, "count": 0, "issues": []}

                sprints[sprint_num]["points"] += issue["estimate"]
                sprints[sprint_num]["count"] += 1
                sprints[sprint_num]["issues"].append(issue["identifier"])

            # Calculate average velocity
            if not sprints:
                return {"content": [{"type": "text", "text": "No estimated issues found"}]}

            avg_points = sum(s["points"] for s in sprints.values()) / len(sprints)
            avg_count = sum(s["count"] for s in sprints.values()) / len(sprints)

            # Determine trend
            sorted_sprints = sorted(sprints.items())
            if len(sorted_sprints) >= 2:
                recent_velocity = sorted_sprints[0][1]["points"]
                older_velocity = sum(s[1]["points"] for s in sorted_sprints[1:]) / (len(sorted_sprints) - 1)
                trend = "📈 Increasing" if recent_velocity > older_velocity else "📉 Decreasing" if recent_velocity < older_velocity else "➡️ Stable"
            else:
                trend = "➡️ Stable (insufficient data)"

            # Format results
            result = f"# Sprint Velocity Analysis\n\n"
            result += f"**Average Velocity:** {avg_points:.1f} points/sprint\n"
            result += f"**Average Issues:** {avg_count:.1f} issues/sprint\n"
            result += f"**Trend:** {trend}\n\n"

            result += "## Sprint Breakdown\n"
            for sprint_num, sprint_data in sorted(sprints.items()):
                sprint_label = "Current Sprint" if sprint_num == 0 else f"{sprint_num * 2} weeks ago"
                result += f"\n**{sprint_label}:**\n"
                result += f"- Points: {sprint_data['points']}\n"
                result += f"- Issues: {sprint_data['count']}\n"
                result += f"- Completed: {', '.join(sprint_data['issues'][:5])}\n"

            return {"content": [{"type": "text", "text": result}]}
    except Exception as e:
        logger.exception("Error calculating sprint velocity")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool(
    "get_issue_dependencies",
    "Map issue dependencies and blockers to identify critical path",
    {
        "issue_id": str,  # Issue ID or identifier to analyze
        "depth": int,  # How many levels deep to traverse (default 2)
    },
)
async def get_issue_dependencies(args: dict) -> dict:
    """Analyze issue dependencies and blockers."""
    import httpx

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    issue_id = args.get("issue_id")
    depth = args.get("depth", 2)

    if not issue_id:
        return {"content": [{"type": "text", "text": "issue_id is required"}]}

    # Recursive query to get dependencies
    query = """
    query GetIssueDependencies($id: String!) {
      issue(id: $id) {
        identifier
        title
        state { name }
        relations {
          nodes {
            type
            relatedIssue {
              identifier
              title
              state { name }
            }
          }
        }
        parent { identifier title state { name } }
        children { nodes { identifier title state { name } } }
      }
    }
    """

    visited = set()
    blockers = []
    blocked_by = []
    related = []

    async def fetch_issue_deps(issue_id_to_fetch, current_depth=0):
        if current_depth >= depth or issue_id_to_fetch in visited:
            return
        visited.add(issue_id_to_fetch)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.linear.app/graphql",
                    json={"query": query, "variables": {"id": issue_id_to_fetch}},
                    headers={"Authorization": settings.linear_api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    return

                issue = data.get("data", {}).get("issue")
                if not issue:
                    return

                # Process relations
                for relation in issue.get("relations", {}).get("nodes", []):
                    rel_type = relation["type"]
                    rel_issue = relation["relatedIssue"]
                    entry = {
                        "id": rel_issue["identifier"],
                        "title": rel_issue["title"],
                        "state": rel_issue["state"]["name"],
                    }

                    if rel_type == "blocks":
                        blockers.append(entry)
                    elif rel_type == "blocked_by":
                        blocked_by.append(entry)
                    else:
                        related.append(entry)

                    # Recursively fetch dependencies
                    if current_depth < depth - 1:
                        await fetch_issue_deps(rel_issue["identifier"], current_depth + 1)

        except Exception as e:
            logger.warning(f"Error fetching dependencies for {issue_id_to_fetch}: {e}")

    try:
        # Start recursive fetch
        await fetch_issue_deps(issue_id)

        # Format results
        result = f"# Dependency Analysis for {issue_id}\n\n"

        if blockers:
            result += f"## 🚫 Blocking ({len(blockers)} issues)\n"
            for blocker in blockers:
                result += f"- [{blocker['id']}] {blocker['title']} ({blocker['state']})\n"
            result += "\n"

        if blocked_by:
            result += f"## ⛔ Blocked By ({len(blocked_by)} issues)\n"
            for blocked in blocked_by:
                status_icon = "✅" if "completed" in blocked['state'].lower() else "❌"
                result += f"- {status_icon} [{blocked['id']}] {blocked['title']} ({blocked['state']})\n"
            result += "\n"

        if related:
            result += f"## 🔗 Related ({len(related)} issues)\n"
            for rel in related:
                result += f"- [{rel['id']}] {rel['title']} ({rel['state']})\n"
            result += "\n"

        if not blockers and not blocked_by and not related:
            result += "✅ No dependencies or blockers found\n"

        return {"content": [{"type": "text", "text": result}]}
    except Exception as e:
        logger.exception("Error analyzing dependencies")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}
