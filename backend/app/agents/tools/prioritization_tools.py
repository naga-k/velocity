"""Prioritization tools — PM frameworks for decision-making.

Implements RICE, impact-effort matrix, weighted scoring, and other frameworks
for ranking features and making trade-off decisions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

logger = logging.getLogger(__name__)


@tool(
    "apply_rice_framework",
    "Calculate RICE scores (Reach × Impact × Confidence ÷ Effort) for prioritization",
    {
        "items": str,  # JSON array of items with reach, impact, confidence, effort fields
    },
)
async def apply_rice_framework(args: dict) -> dict:
    """Calculate RICE scores for a list of features/items.

    Each item should have:
    - name: str
    - reach: int (number of users/customers affected per time period)
    - impact: int (1=minimal, 2=low, 3=medium, 4=high, 5=massive)
    - confidence: float (0.0-1.0, percentage expressed as decimal)
    - effort: int (person-months or story points)
    """
    try:
        items_data = json.loads(args.get("items", "[]"))
    except json.JSONDecodeError:
        return {"content": [{"type": "text", "text": "Invalid JSON format for items"}]}

    if not items_data:
        return {"content": [{"type": "text", "text": "No items provided"}]}

    results = []
    for item in items_data:
        name = item.get("name", "Unnamed")
        reach = item.get("reach", 0)
        impact = item.get("impact", 1)
        confidence = item.get("confidence", 0.5)
        effort = item.get("effort", 1)

        if effort == 0:
            rice_score = 0
        else:
            rice_score = (reach * impact * confidence) / effort

        results.append({
            "name": name,
            "reach": reach,
            "impact": impact,
            "confidence": confidence,
            "effort": effort,
            "rice_score": round(rice_score, 2),
        })

    # Sort by RICE score (highest first)
    results.sort(key=lambda x: x["rice_score"], reverse=True)

    # Add rank
    for idx, result in enumerate(results, 1):
        result["rank"] = idx

    # Format output
    output = "# RICE Scoring Results\n\n"
    output += "| Rank | Item | RICE Score | Reach | Impact | Confidence | Effort |\n"
    output += "|------|------|------------|-------|--------|------------|--------|\n"

    for result in results:
        output += f"| {result['rank']} | {result['name']} | **{result['rice_score']}** | "
        output += f"{result['reach']} | {result['impact']} | {result['confidence']:.0%} | {result['effort']} |\n"

    output += f"\n**Formula:** RICE = (Reach × Impact × Confidence) ÷ Effort\n"
    output += f"\n**Recommendation:** Prioritize items with highest RICE scores.\n"

    # JSON for programmatic use
    json_output = json.dumps(results, indent=2)

    return {"content": [{"type": "text", "text": f"{output}\n\n<details>\n<summary>JSON Data</summary>\n\n```json\n{json_output}\n```\n</details>"}]}


@tool(
    "apply_impact_effort_matrix",
    "Map items to 2×2 impact-effort matrix (Quick Wins, Big Bets, Fill Ins, Time Sinks)",
    {
        "items": str,  # JSON array of items with name, impact, effort fields
    },
)
async def apply_impact_effort_matrix(args: dict) -> dict:
    """Plot items on impact-effort matrix for visual prioritization."""
    try:
        items_data = json.loads(args.get("items", "[]"))
    except json.JSONDecodeError:
        return {"content": [{"type": "text", "text": "Invalid JSON format for items"}]}

    if not items_data:
        return {"content": [{"type": "text", "text": "No items provided"}]}

    # Categorize items
    quick_wins = []  # High impact, low effort
    big_bets = []    # High impact, high effort
    fill_ins = []    # Low impact, low effort
    time_sinks = []  # Low impact, high effort

    for item in items_data:
        name = item.get("name", "Unnamed")
        impact = item.get("impact", 1)  # 1-5
        effort = item.get("effort", 1)  # 1-5 or story points

        # Normalize effort to 1-5 scale if using story points
        if effort > 5:
            effort_normalized = min(5, effort // 3)  # Rough conversion
        else:
            effort_normalized = effort

        # Categorize (threshold = 3)
        high_impact = impact >= 3
        low_effort = effort_normalized <= 2

        entry = {
            "name": name,
            "impact": impact,
            "effort": effort,
        }

        if high_impact and low_effort:
            quick_wins.append(entry)
        elif high_impact and not low_effort:
            big_bets.append(entry)
        elif not high_impact and low_effort:
            fill_ins.append(entry)
        else:
            time_sinks.append(entry)

    # Format output
    output = "# Impact-Effort Matrix\n\n"
    output += "```\n"
    output += "     High Impact\n"
    output += "          |\n"
    output += " Big Bets | Quick Wins\n"
    output += "    (Strategic)|(Do First!)\n"
    output += "----------+----------\n"
    output += "Time Sinks| Fill Ins\n"
    output += "   (Avoid)|  (Maybe)\n"
    output += "          |\n"
    output += "     Low Impact\n"
    output += "```\n\n"

    output += f"## 🎯 Quick Wins ({len(quick_wins)}) - **DO THESE FIRST**\n"
    for item in quick_wins:
        output += f"- **{item['name']}** (Impact: {item['impact']}, Effort: {item['effort']})\n"

    output += f"\n## 🚀 Big Bets ({len(big_bets)}) - Strategic investments\n"
    for item in big_bets:
        output += f"- **{item['name']}** (Impact: {item['impact']}, Effort: {item['effort']})\n"

    output += f"\n## 🔧 Fill Ins ({len(fill_ins)}) - Low priority\n"
    for item in fill_ins:
        output += f"- {item['name']} (Impact: {item['impact']}, Effort: {item['effort']})\n"

    output += f"\n## ⚠️ Time Sinks ({len(time_sinks)}) - **AVOID**\n"
    for item in time_sinks:
        output += f"- {item['name']} (Impact: {item['impact']}, Effort: {item['effort']})\n"

    output += "\n**Recommendation:** Start with Quick Wins, then Big Bets. Reconsider Time Sinks.\n"

    return {"content": [{"type": "text", "text": output}]}


@tool(
    "calculate_weighted_scoring",
    "Multi-criteria scoring with custom weights for different factors",
    {
        "items": str,  # JSON array of items with name and criterion scores
        "weights": str,  # JSON object with criterion names and weights (must sum to 1.0)
    },
)
async def calculate_weighted_scoring(args: dict) -> dict:
    """Calculate weighted scores across multiple criteria."""
    try:
        items_data = json.loads(args.get("items", "[]"))
        weights_data = json.loads(args.get("weights", "{}"))
    except json.JSONDecodeError:
        return {"content": [{"type": "text", "text": "Invalid JSON format"}]}

    if not items_data or not weights_data:
        return {"content": [{"type": "text", "text": "Items and weights are required"}]}

    # Validate weights sum to 1.0
    total_weight = sum(weights_data.values())
    if not (0.99 <= total_weight <= 1.01):  # Allow small floating point errors
        return {"content": [{"type": "text", "text": f"Weights must sum to 1.0 (got {total_weight})"}]}

    results = []
    for item in items_data:
        name = item.get("name", "Unnamed")
        weighted_score = 0.0
        criterion_scores = {}

        for criterion, weight in weights_data.items():
            score = item.get(criterion, 0)
            weighted_score += score * weight
            criterion_scores[criterion] = score

        results.append({
            "name": name,
            "weighted_score": round(weighted_score, 2),
            "criteria": criterion_scores,
        })

    # Sort by weighted score (highest first)
    results.sort(key=lambda x: x["weighted_score"], reverse=True)

    # Add rank
    for idx, result in enumerate(results, 1):
        result["rank"] = idx

    # Format output
    output = "# Weighted Scoring Results\n\n"
    output += f"**Criteria & Weights:**\n"
    for criterion, weight in weights_data.items():
        output += f"- {criterion}: {weight:.0%}\n"
    output += "\n"

    output += "| Rank | Item | Weighted Score | "
    output += " | ".join(weights_data.keys()) + " |\n"
    output += "|------|------|----------------|"
    output += "|".join(["--------"] * len(weights_data)) + "|\n"

    for result in results:
        output += f"| {result['rank']} | {result['name']} | **{result['weighted_score']}** | "
        criteria_values = " | ".join(str(result['criteria'].get(c, 0)) for c in weights_data.keys())
        output += criteria_values + " |\n"

    output += f"\n**Recommendation:** Prioritize {results[0]['name']} (highest weighted score).\n"

    return {"content": [{"type": "text", "text": output}]}


@tool(
    "analyze_trade_offs",
    "Structured pros/cons comparison between options with impact assessment",
    {
        "options": str,  # JSON array of options with name, pros, cons, impact
    },
)
async def analyze_trade_offs(args: dict) -> dict:
    """Analyze trade-offs between multiple options."""
    try:
        options_data = json.loads(args.get("options", "[]"))
    except json.JSONDecodeError:
        return {"content": [{"type": "text", "text": "Invalid JSON format for options"}]}

    if not options_data:
        return {"content": [{"type": "text", "text": "No options provided"}]}

    output = "# Trade-Off Analysis\n\n"

    for idx, option in enumerate(options_data, 1):
        name = option.get("name", f"Option {idx}")
        pros = option.get("pros", [])
        cons = option.get("cons", [])
        impact = option.get("impact", "Unknown")

        output += f"## {idx}. {name}\n\n"
        output += f"**Impact:** {impact}\n\n"

        output += "### ✅ Pros\n"
        if pros:
            for pro in pros:
                output += f"- {pro}\n"
        else:
            output += "- (No pros listed)\n"

        output += "\n### ❌ Cons\n"
        if cons:
            for con in cons:
                output += f"- {con}\n"
        else:
            output += "- (No cons listed)\n"

        # Calculate simple pro/con ratio
        pro_count = len(pros)
        con_count = len(cons)
        if pro_count + con_count > 0:
            ratio = pro_count / (pro_count + con_count)
            output += f"\n**Pro/Con Ratio:** {pro_count}/{con_count} ({ratio:.0%} positive)\n"

        output += "\n---\n\n"

    output += "## Recommendation\n\n"
    output += "Consider:\n"
    output += "1. Which option aligns best with strategic goals?\n"
    output += "2. What's the risk tolerance for each option's cons?\n"
    output += "3. Are there ways to mitigate the cons while preserving pros?\n"

    return {"content": [{"type": "text", "text": output}]}


@tool(
    "estimate_engineering_effort",
    "Estimate development time using Linear issue history and similar tickets",
    {
        "description": str,  # Description of the work to estimate
        "similar_issues": str,  # Comma-separated Linear issue IDs for reference
    },
)
async def estimate_engineering_effort(args: dict) -> dict:
    """Estimate effort based on historical Linear data.

    Note: This is a simplified estimation tool. For production use, integrate
    with linear_tools to fetch actual completion times.
    """
    description = args.get("description", "")
    similar_issues = args.get("similar_issues", "")

    if not description:
        return {"content": [{"type": "text", "text": "Description is required"}]}

    output = f"# Engineering Effort Estimate\n\n"
    output += f"**Work Description:** {description}\n\n"

    if similar_issues:
        output += f"**Reference Issues:** {similar_issues}\n\n"
        output += "## Estimation Approach\n\n"
        output += "1. Review the referenced Linear issues for actual time spent\n"
        output += "2. Compare complexity (is this work simpler or more complex?)\n"
        output += "3. Account for unknowns and risks (add buffer)\n"
        output += "4. Consider team velocity from `calculate_sprint_velocity`\n\n"
        output += "**Recommended Next Steps:**\n"
        output += "- Use `get_linear_issue_by_id` to analyze similar issues\n"
        output += "- Use `calculate_sprint_velocity` to understand team capacity\n"
        output += "- Apply a 1.5x buffer for unknown complexity\n"
    else:
        output += "## T-Shirt Sizing Estimate\n\n"
        output += "Without reference issues, here's a rough estimate:\n\n"

        # Estimate based on description length (very rough heuristic)
        word_count = len(description.split())

        if word_count < 20:
            estimate = "**Small (1-2 days)**"
            reasoning = "Simple, well-defined task"
        elif word_count < 50:
            estimate = "**Medium (3-5 days)**"
            reasoning = "Moderate complexity, some unknowns"
        else:
            estimate = "**Large (1-2 weeks)**"
            reasoning = "Complex task, multiple unknowns"

        output += f"- **Estimate:** {estimate}\n"
        output += f"- **Reasoning:** {reasoning}\n\n"
        output += "**⚠️ Low Confidence:** This is a rough estimate. For better accuracy:\n"
        output += "- Break down the work into smaller tasks\n"
        output += "- Identify similar completed issues for reference\n"
        output += "- Consult with engineers who have context\n"

    return {"content": [{"type": "text", "text": output}]}


@tool(
    "assess_strategic_fit",
    "Score how well an item aligns with product strategy and goals",
    {
        "item_name": str,  # Name of feature/initiative to assess
        "item_description": str,  # Description of the item
        "strategy_criteria": str,  # JSON array of strategic criteria to check against
    },
)
async def assess_strategic_fit(args: dict) -> dict:
    """Assess alignment with product strategy.

    Reads product-context.md for strategy reference.
    """
    from pathlib import Path
    import os

    item_name = args.get("item_name", "Unnamed Item")
    item_description = args.get("item_description", "")

    try:
        criteria = json.loads(args.get("strategy_criteria", "[]"))
    except json.JSONDecodeError:
        # Default criteria if none provided
        criteria = [
            "Aligns with product vision",
            "Serves target customer segment",
            "Supports key metrics/OKRs",
            "Differentiates from competitors",
            "Technically feasible",
        ]

    # Try to read product context
    memory_dir = Path(os.getenv("MEMORY_PATH", str(Path(__file__).resolve().parent.parent.parent.parent / "memory")))
    context_file = memory_dir / "product-context.md"

    context_available = False
    context_summary = ""

    if context_file.exists():
        context_available = True
        context_content = context_file.read_text()
        # Extract first paragraph as summary
        paragraphs = [p.strip() for p in context_content.split("\n\n") if p.strip()]
        context_summary = paragraphs[0] if paragraphs else "Product context available"

    output = f"# Strategic Fit Assessment: {item_name}\n\n"
    output += f"**Description:** {item_description}\n\n"

    if context_available:
        output += f"**Product Strategy Reference:**\n> {context_summary}\n\n"
    else:
        output += "**⚠️ No product context found.** Create `memory/product-context.md` for better strategic alignment.\n\n"

    output += "## Alignment Scorecard\n\n"
    output += "Rate each criterion from 1-5 (1=Poor fit, 5=Excellent fit):\n\n"

    output += "| Criterion | Score | Notes |\n"
    output += "|-----------|-------|-------|\n"

    total_score = 0
    max_score = len(criteria) * 5

    # For demonstration, use simple keyword matching against description
    for criterion in criteria:
        # This is a placeholder - in production, would use more sophisticated analysis
        score = 3  # Default neutral score
        notes = "Manual review required"

        output += f"| {criterion} | {score}/5 | {notes} |\n"
        total_score += score

    alignment_pct = (total_score / max_score) * 100 if max_score > 0 else 0

    output += f"\n**Overall Strategic Fit:** {total_score}/{max_score} ({alignment_pct:.0f}%)\n\n"

    if alignment_pct >= 80:
        output += "✅ **Strong Alignment** - This initiative aligns well with strategy.\n"
    elif alignment_pct >= 60:
        output += "⚠️ **Moderate Alignment** - Consider refining to better match strategy.\n"
    else:
        output += "❌ **Weak Alignment** - Reassess whether this supports strategic goals.\n"

    output += "\n**Recommendation:** Review alignment scores with stakeholders before prioritizing.\n"

    return {"content": [{"type": "text", "text": output}]}
