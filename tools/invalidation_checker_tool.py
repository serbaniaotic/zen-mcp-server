"""
Invalidation Checker MCP Tools

Exposes invalidation checking operations as MCP tools.
"""

import logging
from typing import Any, Dict, List

from .agent_registry import get_registry
from .evidence_monitor import EvidenceEntry, get_monitor
from .invalidation_checker import get_checker

logger = logging.getLogger(__name__)


async def check_invalidation_tool(
    agent_id: str,
    new_entry_numbers: List[int]
) -> Dict[str, Any]:
    """
    Check if new evidence entries invalidate an agent's thinking.
    
    Args:
        agent_id: Agent ID to check
        new_entry_numbers: List of new entry numbers to check
        
    Returns:
        Invalidation decision with reasoning
    """
    try:
        registry = get_registry()
        monitor = get_monitor()
        checker = get_checker()
        
        # Get agent
        agent = await registry.get(agent_id)
        if not agent:
            return {
                "success": False,
                "error": f"Agent {agent_id} not found"
            }
        
        # Get new entries
        updates = await monitor.check_for_updates(
            agent.ticket_id,
            agent.evidence_entry_range
        )
        
        # Filter to requested entry numbers
        entries = [
            u.entry for u in updates
            if u.new_entry_number in new_entry_numbers
        ]
        
        if not entries:
            return {
                "success": True,
                "should_terminate": False,
                "reason": "No matching entries found",
                "agent_id": agent_id
            }
        
        # Check invalidation
        decision = checker.check_multiple_entries(agent, entries)
        
        return {
            "success": True,
            "agent_id": agent_id,
            "should_terminate": decision.should_terminate,
            "reason": decision.reason,
            "invalidation_type": decision.invalidation_type.value,
            "conflicting_entry": decision.conflicting_entry,
            "recommendation": decision.recommendation,
            "confidence": decision.confidence,
            "matched_rules": decision.matched_rules
        }
        
    except Exception as e:
        logger.error(f"Failed to check invalidation: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def validate_before_respond_tool(agent_id: str) -> Dict[str, Any]:
    """
    Final validation check before agent responds.
    
    This is the critical check that prevents hallucination.
    Agent should call this right before generating response.
    
    Args:
        agent_id: Agent ID
        
    Returns:
        Validation result (safe to respond or terminate)
    """
    try:
        registry = get_registry()
        monitor = get_monitor()
        checker = get_checker()
        
        # Get agent
        agent = await registry.get(agent_id)
        if not agent:
            return {
                "success": False,
                "error": f"Agent {agent_id} not found"
            }
        
        # Check for ANY new entries since agent started
        updates = await monitor.check_for_updates(
            agent.ticket_id,
            agent.evidence_entry_range
        )
        
        if not updates:
            # No new entries, safe to respond
            return {
                "success": True,
                "agent_id": agent_id,
                "safe_to_respond": True,
                "reason": "No new evidence since thinking started",
                "new_entries_count": 0
            }
        
        # New entries exist, check if they invalidate
        entries = [u.entry for u in updates]
        decision = checker.check_multiple_entries(agent, entries)
        
        if decision.should_terminate:
            # CRITICAL: Terminate agent before it responds
            await registry.terminate(agent_id, decision.reason)
            
            return {
                "success": True,
                "agent_id": agent_id,
                "safe_to_respond": False,
                "should_terminate": True,
                "reason": decision.reason,
                "new_entries_count": len(updates),
                "recommendation": decision.recommendation,
                "conflicting_entry": decision.conflicting_entry
            }
        
        # New entries exist but don't invalidate
        return {
            "success": True,
            "agent_id": agent_id,
            "safe_to_respond": True,
            "reason": "New evidence checked, no invalidation detected",
            "new_entries_count": len(updates)
        }
        
    except Exception as e:
        logger.error(f"Failed to validate before respond: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def add_invalidation_rule_tool(
    rule_name: str,
    invalidation_type: str,
    severity: str,
    keywords: List[str],
    description: str
) -> Dict[str, Any]:
    """
    Add a custom invalidation rule.
    
    Args:
        rule_name: Unique rule name
        invalidation_type: Type of invalidation
        severity: "terminate", "warn", or "info"
        keywords: Keywords to match
        description: Human-readable description
        
    Returns:
        Rule addition status
    """
    try:
        from .invalidation_checker import (
            InvalidationRule,
            InvalidationSeverity,
            InvalidationType,
        )
        
        checker = get_checker()
        
        # Create keyword-based check function
        def keyword_check(agent, entry):
            content = (entry.prompt_input + " " + entry.raw_output).lower()
            return any(kw.lower() in content for kw in keywords)
        
        # Create rule
        rule = InvalidationRule(
            name=rule_name,
            invalidation_type=InvalidationType(invalidation_type),
            severity=InvalidationSeverity(severity),
            check=keyword_check,
            description=description
        )
        
        checker.add_rule(rule)
        
        return {
            "success": True,
            "rule_name": rule_name,
            "message": f"Added invalidation rule: {rule_name}"
        }
        
    except Exception as e:
        logger.error(f"Failed to add rule: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_invalidation_rules_tool() -> Dict[str, Any]:
    """
    Get all active invalidation rules.
    
    Returns:
        List of rules with descriptions
    """
    try:
        checker = get_checker()
        
        rules = [
            {
                "name": rule.name,
                "type": rule.invalidation_type.value,
                "severity": rule.severity.value,
                "description": rule.description
            }
            for rule in checker.rules
        ]
        
        return {
            "success": True,
            "rule_count": len(rules),
            "rules": rules
        }
        
    except Exception as e:
        logger.error(f"Failed to get rules: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Tool definitions for MCP server
INVALIDATION_CHECKER_TOOLS = [
    {
        "name": "check_invalidation",
        "description": "Check if new evidence entries invalidate an agent's thinking",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to check"
                },
                "new_entry_numbers": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "New entry numbers to check (e.g. [4, 5])"
                }
            },
            "required": ["agent_id", "new_entry_numbers"]
        }
    },
    {
        "name": "validate_before_respond",
        "description": "CRITICAL: Final check before agent responds (prevents hallucination)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID about to respond"
                }
            },
            "required": ["agent_id"]
        }
    },
    {
        "name": "add_invalidation_rule",
        "description": "Add a custom invalidation rule (keyword-based)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "rule_name": {
                    "type": "string",
                    "description": "Unique rule name"
                },
                "invalidation_type": {
                    "type": "string",
                    "enum": [
                        "user_direction_change",
                        "agent_solution_found",
                        "context_shift",
                        "contradiction",
                        "approach_failed"
                    ],
                    "description": "Type of invalidation"
                },
                "severity": {
                    "type": "string",
                    "enum": ["terminate", "warn", "info"],
                    "description": "Severity level"
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to match"
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description"
                }
            },
            "required": ["rule_name", "invalidation_type", "severity", "keywords", "description"]
        }
    },
    {
        "name": "get_invalidation_rules",
        "description": "Get all active invalidation rules",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


# Map tool names to functions
INVALIDATION_CHECKER_TOOL_MAP = {
    "check_invalidation": check_invalidation_tool,
    "validate_before_respond": validate_before_respond_tool,
    "add_invalidation_rule": add_invalidation_rule_tool,
    "get_invalidation_rules": get_invalidation_rules_tool,
}

