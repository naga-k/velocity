"""Memory tools — product context, insights, decisions, and customer feedback.

These tools provide access to persistent product knowledge and historical data.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from claude_agent_sdk import tool

logger = logging.getLogger(__name__)

# Memory directory - use env var in production, fallback to local in dev
MEMORY_DIR = Path(os.getenv("MEMORY_PATH", str(Path(__file__).resolve().parent.parent.parent / "memory")))


@tool(
    "read_product_context",
    "Load the current product context from memory",
    {},
)
async def read_product_context(args: dict) -> dict:
    """Read product-context.md from memory."""
    context_file = MEMORY_DIR / "product-context.md"
    if not context_file.exists():
        return {"content": [{"type": "text", "text": "No product context found"}]}
    content = context_file.read_text()
    return {"content": [{"type": "text", "text": content}]}


@tool(
    "save_insight",
    "Save a product insight to persistent memory",
    {
        "category": str,  # "feedback" | "decision" | "metric" | "competitive"
        "content": str,
        "sources": str,  # comma-separated source URLs
    },
)
async def save_insight(args: dict) -> dict:
    """Append an insight to the appropriate category file."""
    category = args["category"]
    if not re.match(r"^[a-zA-Z0-9_-]+$", category):
        return {"content": [{"type": "text", "text": f"Invalid category: {category}"}]}
    insights_dir = MEMORY_DIR / "insights"
    insights_dir.mkdir(parents=True, exist_ok=True)
    target = insights_dir / f"{category}.md"
    with open(target, "a") as f:
        f.write(f"\n---\n{args['content']}\nSources: {args['sources']}\n")
    return {"content": [{"type": "text", "text": f"Insight saved to {category}"}]}


@tool(
    "search_past_decisions",
    "Search historical product decisions for context on past choices",
    {
        "query": str,  # Search query (supports case-insensitive text matching)
        "limit": int,  # Max results to return (default 10)
    },
)
async def search_past_decisions(args: dict) -> dict:
    """Search decision logs in memory/decisions/ directory."""
    query = args.get("query", "").lower()
    limit = args.get("limit", 10)

    decisions_dir = MEMORY_DIR / "decisions"
    if not decisions_dir.exists():
        return {"content": [{"type": "text", "text": "No decisions directory found. Create memory/decisions/ to track product decisions."}]}

    results = []
    decision_files = list(decisions_dir.glob("*.md"))

    if not decision_files:
        return {"content": [{"type": "text", "text": "No decision logs found in memory/decisions/"}]}

    for file_path in decision_files:
        try:
            content = file_path.read_text()
            # Search for query in content (case-insensitive)
            if query in content.lower():
                # Extract a snippet around the match
                lines = content.split("\n")
                matching_lines = [line for line in lines if query in line.lower()]
                snippet = "\n".join(matching_lines[:3])  # First 3 matching lines
                results.append({
                    "file": file_path.name,
                    "snippet": snippet[:300],  # Limit snippet length
                    "full_content": content if len(results) < 3 else None,  # Full content for top 3
                })
                if len(results) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
            continue

    if not results:
        return {"content": [{"type": "text", "text": f"No decisions found matching '{query}'"}]}

    # Format results as markdown
    output = f"# Past Decisions (found {len(results)} matches for '{query}')\n\n"
    for idx, result in enumerate(results, 1):
        output += f"## {idx}. {result['file']}\n\n"
        if result.get("full_content"):
            output += f"{result['full_content']}\n\n"
        else:
            output += f"**Snippet:**\n```\n{result['snippet']}\n```\n\n"

    return {"content": [{"type": "text", "text": output}]}


@tool(
    "search_customer_feedback",
    "Search customer feedback logs for product insights and feature requests",
    {
        "query": str,  # Search query (supports case-insensitive text matching)
        "limit": int,  # Max results to return (default 10)
    },
)
async def search_customer_feedback(args: dict) -> dict:
    """Search customer feedback in memory/feedback/ directory."""
    query = args.get("query", "").lower()
    limit = args.get("limit", 10)

    feedback_dir = MEMORY_DIR / "feedback"
    if not feedback_dir.exists():
        return {"content": [{"type": "text", "text": "No feedback directory found. Create memory/feedback/ to track customer feedback."}]}

    results = []
    feedback_files = list(feedback_dir.glob("*.md"))

    if not feedback_files:
        return {"content": [{"type": "text", "text": "No customer feedback found in memory/feedback/"}]}

    for file_path in feedback_files:
        try:
            content = file_path.read_text()
            # Search for query in content (case-insensitive)
            if query in content.lower():
                # Extract a snippet around the match
                lines = content.split("\n")
                matching_lines = [line for line in lines if query in line.lower()]
                snippet = "\n".join(matching_lines[:3])  # First 3 matching lines

                # Try to extract metadata (customer tier, date) if present
                metadata = {"source": file_path.name}
                for line in lines[:10]:  # Check first 10 lines for metadata
                    if "tier:" in line.lower():
                        metadata["tier"] = line.split(":", 1)[1].strip()
                    elif "date:" in line.lower():
                        metadata["date"] = line.split(":", 1)[1].strip()

                results.append({
                    "file": file_path.name,
                    "snippet": snippet[:300],  # Limit snippet length
                    "metadata": metadata,
                    "full_content": content if len(results) < 3 else None,  # Full content for top 3
                })
                if len(results) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
            continue

    if not results:
        return {"content": [{"type": "text", "text": f"No customer feedback found matching '{query}'"}]}

    # Format results as markdown
    output = f"# Customer Feedback (found {len(results)} matches for '{query}')\n\n"
    for idx, result in enumerate(results, 1):
        output += f"## {idx}. {result['file']}\n"
        if result["metadata"].get("tier"):
            output += f"**Tier:** {result['metadata']['tier']}\n"
        if result["metadata"].get("date"):
            output += f"**Date:** {result['metadata']['date']}\n"
        output += "\n"

        if result.get("full_content"):
            output += f"{result['full_content']}\n\n"
        else:
            output += f"**Snippet:**\n```\n{result['snippet']}\n```\n\n"

    return {"content": [{"type": "text", "text": output}]}
