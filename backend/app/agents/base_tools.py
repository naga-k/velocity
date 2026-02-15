"""Base PM tools — product context and insights.

These tools are available to the orchestrator and doc-writer agent.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from claude_agent_sdk import tool

logger = logging.getLogger(__name__)

# Memory directory
MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / "memory"


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
