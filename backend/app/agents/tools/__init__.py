"""Agent tools — organized by domain.

This module exports all tools available to agents. Tools are organized into:
- memory_tools: Product context, decisions, insights, customer feedback
- linear_tools: Linear issue management (CRUD + metrics)
- prioritization_tools: PM frameworks (RICE, impact-effort, weighted scoring)
- document_tools: Template generation and validation
"""

from __future__ import annotations

# Import all tools from submodules
from .memory_tools import *
from .linear_tools import *
from .prioritization_tools import *
from .document_tools import *

__all__ = [
    # Memory tools (4)
    "read_product_context",
    "save_insight",
    "search_past_decisions",
    "search_customer_feedback",
    # Linear tools (10)
    "create_linear_issue",
    "update_linear_issue",
    "list_linear_issues",
    "get_linear_issue_by_id",
    "search_linear_issues_advanced",
    "add_linear_comment",
    "get_linear_project_status",
    "bulk_update_linear_issues",
    "calculate_sprint_velocity",
    "get_issue_dependencies",
    # Prioritization tools (6)
    "apply_rice_framework",
    "apply_impact_effort_matrix",
    "calculate_weighted_scoring",
    "analyze_trade_offs",
    "estimate_engineering_effort",
    "assess_strategic_fit",
    # Document tools (4)
    "generate_prd_from_template",
    "generate_stakeholder_update",
    "validate_document_citations",
    "format_for_notion",
]
