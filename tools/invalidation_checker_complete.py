"""
Zen MCP Tool: Invalidation Checker (Complete)

Wraps invalidation_checker_tool.py functions into a SimpleTool for MCP integration.

Constitutional alignment: "Find hope in knowledge and grace in wisdom"
- Hope: Prevent repeated failures (learn from mistakes)
- Grace: Intelligent termination (know when to stop thinking)
"""

import logging
from typing import Any, Dict, Optional, List
from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.simple.base import SimpleTool
from tools.invalidation_checker_tool import (
    check_invalidation_tool,
    validate_before_respond_tool,
    add_invalidation_rule_tool,
    get_invalidation_rules_tool,
)

logger = logging.getLogger(__name__)

FIELD_DESCRIPTIONS = {
    "action": "Action to perform: check, validate, add_rule, list_rules",
    "agent_id": "Agent ID to check for invalidation",
    "new_entry_numbers": "List of new evidence entry numbers to check (comma-separated)",
    "rule_pattern": "Pattern to match for invalidation rule",
    "invalidation_type": "Type of invalidation (new_evidence, contradiction, context_shift, dead_end)",
}


class InvalidationCheckerRequest(ToolRequest):
    """Request model for Invalidation Checker tool"""

    action: str = Field(description=FIELD_DESCRIPTIONS["action"])
    agent_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["agent_id"])
    new_entry_numbers: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["new_entry_numbers"])
    rule_pattern: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["rule_pattern"])
    invalidation_type: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["invalidation_type"])


class InvalidationCheckerTool(SimpleTool):
    """
    Check if new evidence invalidates agent's current thinking.
    
    This tool enables agents to:
    - Check if new evidence makes current analysis obsolete
    - Validate before responding (prevent stale responses)
    - Force invalidation when needed (manual override)
    - Get invalidation summary (debugging)
    
    Constitutional alignment: Prevents hallucination through evidence awareness.
    """

    def get_name(self) -> str:
        return "invalidation_checker"

    def get_description(self) -> str:
        return "Check if new evidence invalidates agent's current thinking and prevent stale responses."

    def get_system_prompt(self) -> str:
        return """You are an invalidation checker that helps agents determine if their thinking is still valid.

Your role:
- Check if new evidence contradicts agent's current analysis
- Detect when context has fundamentally changed
- Recommend thinking termination when appropriate
- Prevent agents from responding with obsolete information

When checking invalidation:
1. Compare agent's evidence state vs current evidence
2. Identify what's new or changed
3. Determine if changes make agent's thinking obsolete
4. Recommend: continue OR terminate and restart

Types of invalidation:
- **New evidence**: Additional data the agent hasn't seen
- **Contradiction**: Evidence that conflicts with agent's assumptions
- **Context shift**: Investigation moved to different area
- **Dead-end marked**: Approach already tried and failed

This embodies "grace in wisdom" - knowing when to stop thinking is as important as knowing when to continue.
An agent that says "my thinking is obsolete" is more valuable than one that insists on outdated analysis."""

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """Return tool-specific field definitions"""
        return {
            "action": {
                "type": "string",
                "description": "Action to perform",
                "enum": ["check", "validate", "add_rule", "list_rules"]
            },
            "agent_id": {
                "type": "string",
                "description": "Agent ID to check for invalidation"
            },
            "new_entry_numbers": {
                "type": "string",
                "description": "Comma-separated list of new evidence entry numbers to check"
            },
            "rule_pattern": {
                "type": "string",
                "description": "Pattern to match for custom invalidation rule"
            },
            "invalidation_type": {
                "type": "string",
                "description": "Type of invalidation: new_evidence, contradiction, context_shift, dead_end",
                "enum": ["new_evidence", "contradiction", "context_shift", "dead_end"]
            }
        }

    def prepare_prompt(self, request: InvalidationCheckerRequest, **kwargs) -> str:
        """Prepare the prompt for invalidation checking action"""

        if request.action == "check":
            entry_list = request.new_entry_numbers.split(',') if request.new_entry_numbers else []
            return f"""Check if new evidence entries invalidate agent {request.agent_id}'s thinking.

New Evidence Entries: {len(entry_list)} entries to check
{chr(10).join(f'  - Entry #{e.strip()}' for e in entry_list)}

This action will:
1. Retrieve agent's current evidence state
2. Get the new evidence entries
3. Compare new evidence vs agent's assumptions
4. Determine if thinking should be terminated
5. Provide invalidation decision with reasoning

Invalidation types checked:
- New evidence agent hasn't seen
- Evidence contradicting agent's analysis
- Context shift (investigation moved direction)
- Dead-end marked (approach already failed)

Result: should_terminate (true/false) + reason + confidence level"""

        elif request.action == "validate":
            return f"""Final validation check before agent {request.agent_id} responds.

This is the CRITICAL check that prevents hallucination.

This action will:
1. Check for any evidence updates since agent started thinking
2. Verify agent's assumptions still hold
3. Confirm no context shifts occurred
4. Ensure response will be based on current evidence

If ANY invalidation detected:
→ Returns should_terminate = true
→ Agent MUST NOT respond
→ Agent should restart analysis with current evidence

If validation passes:
→ Returns safe_to_respond = true
→ Agent can proceed with response

This is called RIGHT BEFORE generating response to user.
Prevents the "confident but wrong" hallucination pattern."""

        elif request.action == "add_rule":
            return f"""Add custom invalidation rule.

Pattern: {request.rule_pattern}
Type: {request.invalidation_type}

This action will:
1. Create new invalidation pattern rule
2. Apply to future evidence checks
3. Enable custom invalidation logic
4. Pattern matches against evidence content

Use cases:
- Specific phrases that always invalidate (e.g., "FAILED: approach X")
- Context markers (e.g., "PIVOT: new direction")
- Custom domain logic

Example patterns:
- "FAILED:" → dead_end invalidation
- "NEW DATA:" → new_evidence invalidation
- "CONTRADICTION:" → contradiction invalidation"""

        elif request.action == "list_rules":
            return f"""List all configured invalidation rules.

This action will:
1. Show all active invalidation patterns
2. Display rule types and patterns
3. Show rule application statistics
4. Provide rules configuration

Useful for:
- Understanding what triggers invalidation
- Debugging over-aggressive termination
- Reviewing custom rules"""

        else:
            return f"""Unknown action: {request.action}

Available actions:
- check: Check if new evidence invalidates agent's thinking
- validate: Final check before responding (CRITICAL for hallucination prevention)
- force: Manually invalidate agent's thinking
- summary: Get invalidation summary for debugging

Please specify a valid action."""

    async def _call(self, request: InvalidationCheckerRequest, **kwargs) -> Dict[str, Any]:
        """Execute the invalidation checking action."""

        try:
            if request.action == "check":
                if not request.agent_id or not request.new_entry_numbers:
                    return {"success": False, "error": "agent_id and new_entry_numbers required for check"}
                
                # Parse entry numbers
                entry_numbers = [int(e.strip()) for e in request.new_entry_numbers.split(',')]
                
                return await check_invalidation_tool(request.agent_id, entry_numbers)

            elif request.action == "validate":
                if not request.agent_id:
                    return {"success": False, "error": "agent_id required for validate"}
                
                return await validate_before_respond_tool(request.agent_id)

            elif request.action == "add_rule":
                if not request.rule_pattern or not request.invalidation_type:
                    return {"success": False, "error": "rule_pattern and invalidation_type required for add_rule"}
                
                return await add_invalidation_rule_tool(request.rule_pattern, request.invalidation_type)

            elif request.action == "list_rules":
                return await get_invalidation_rules_tool()

            else:
                return {"success": False, "error": f"Unknown action: {request.action}"}

        except Exception as e:
            logger.error(f"Invalidation checker error: {e}")
            return {"success": False, "error": f"Invalidation check failed: {str(e)}"}

