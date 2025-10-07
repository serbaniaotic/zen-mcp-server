"""
Agent Registry MCP Tool

Exposes agent registry operations as MCP tools for multi-agent coordination.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from .agent_registry import (
    AgentInstance,
    AgentRegistry,
    AgentStatus,
    AgentType,
    create_agent_id,
    get_registry,
)

logger = logging.getLogger(__name__)


async def register_agent_tool(
    agent_type: str,
    ticket_id: str,
    evidence_file: str,
    evidence_entry_range: list,
    status: str = "thinking",
    parent_agent_id: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Register a new agent in the coordination system.
    
    Args:
        agent_type: Type of agent (curator, guardian, evidence-organizer, etc.)
        ticket_id: Ticket the agent is working on
        evidence_file: Path to evidence file agent is monitoring
        evidence_entry_range: [start, end] entry numbers agent has seen
        status: Initial status (default: thinking)
        parent_agent_id: ID of parent agent if this is a fork
        
    Returns:
        Dict with agent_id and registration status
    """
    try:
        registry = get_registry()
        
        # Create agent instance
        agent_id = await create_agent_id(AgentType(agent_type), ticket_id)
        now = datetime.utcnow().isoformat() + "Z"
        
        agent = AgentInstance(
            agent_id=agent_id,
            agent_type=AgentType(agent_type),
            status=AgentStatus(status),
            ticket_id=ticket_id,
            evidence_file=evidence_file,
            evidence_entry_range=tuple(evidence_entry_range),
            started_at=now,
            last_context_check=now,
            parent_agent_id=parent_agent_id,
            metadata=kwargs
        )
        
        # Register
        await registry.register(agent)
        
        logger.info(f"Registered agent {agent_id} for ticket {ticket_id}")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "agent_type": agent_type,
            "ticket_id": ticket_id,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Failed to register agent: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_agents_tool(
    ticket_id: str = None,
    agent_type: str = None,
    status: str = None
) -> Dict[str, Any]:
    """
    Query agents by ticket, type, or status.
    
    Args:
        ticket_id: Filter by ticket (optional)
        agent_type: Filter by agent type (optional)
        status: Filter by status (optional)
        
    Returns:
        List of matching agents
    """
    try:
        registry = get_registry()
        agents = []
        
        if ticket_id:
            agents = await registry.get_by_ticket(ticket_id)
        elif agent_type:
            agents = await registry.get_by_type(AgentType(agent_type))
        elif status:
            agents = await registry.get_by_status(AgentStatus(status))
        else:
            # Return all agents
            agents = list(registry.agents.values())
        
        return {
            "success": True,
            "count": len(agents),
            "agents": [agent.to_dict() for agent in agents]
        }
        
    except Exception as e:
        logger.error(f"Failed to query agents: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_thinking_agents_tool(ticket_id: str) -> Dict[str, Any]:
    """
    Get all agents currently thinking on a ticket.
    
    These agents need to be notified when evidence updates occur.
    
    Args:
        ticket_id: Ticket to check
        
    Returns:
        List of thinking agents
    """
    try:
        registry = get_registry()
        agents = await registry.get_thinking_agents(ticket_id)
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "count": len(agents),
            "thinking_agents": [
                {
                    "agent_id": a.agent_id,
                    "agent_type": a.agent_type.value,
                    "evidence_entry_range": list(a.evidence_entry_range),
                    "started_at": a.started_at,
                    "last_context_check": a.last_context_check
                }
                for a in agents
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get thinking agents: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def terminate_agent_tool(agent_id: str, reason: str) -> Dict[str, Any]:
    """
    Terminate an agent's thinking process.
    
    Used when new evidence invalidates the agent's work.
    
    Args:
        agent_id: ID of agent to terminate
        reason: Why the agent is being terminated
        
    Returns:
        Termination status
    """
    try:
        registry = get_registry()
        
        # Get agent info before termination
        agent = await registry.get(agent_id)
        if not agent:
            return {
                "success": False,
                "error": f"Agent {agent_id} not found"
            }
        
        # Terminate
        success = await registry.terminate(agent_id, reason)
        
        logger.info(f"Terminated agent {agent_id}: {reason}")
        
        return {
            "success": success,
            "agent_id": agent_id,
            "agent_type": agent.agent_type.value,
            "ticket_id": agent.ticket_id,
            "termination_reason": reason,
            "was_thinking_for": agent.started_at
        }
        
    except Exception as e:
        logger.error(f"Failed to terminate agent: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def update_context_check_tool(agent_id: str) -> Dict[str, Any]:
    """
    Update agent's last context check timestamp.
    
    Called periodically by thinking agents to show they're still active.
    
    Args:
        agent_id: ID of agent
        
    Returns:
        Update status
    """
    try:
        registry = get_registry()
        success = await registry.update_context_check(agent_id)
        
        return {
            "success": success,
            "agent_id": agent_id,
            "checked_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to update context check: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_registry_stats_tool() -> Dict[str, Any]:
    """
    Get overall registry statistics.
    
    Useful for monitoring and debugging.
    
    Returns:
        Registry statistics
    """
    try:
        registry = get_registry()
        stats = await registry.get_stats()
        
        return {
            "success": True,
            **stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get registry stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_ticket_status_tool(ticket_id: str) -> Dict[str, Any]:
    """
    Get status of all agents for a specific ticket.
    
    Args:
        ticket_id: Ticket to check
        
    Returns:
        Ticket agent status
    """
    try:
        registry = get_registry()
        status = await registry.get_ticket_status(ticket_id)
        
        return {
            "success": True,
            **status
        }
        
    except Exception as e:
        logger.error(f"Failed to get ticket status: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Tool definitions for MCP server
AGENT_REGISTRY_TOOLS = [
    {
        "name": "register_agent",
        "description": "Register a new agent in the multi-agent coordination system",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "enum": ["curator", "guardian", "evidence-organizer", "folder-parser", "thinking"],
                    "description": "Type of agent to register"
                },
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket ID the agent is working on"
                },
                "evidence_file": {
                    "type": "string",
                    "description": "Path to evidence file being monitored"
                },
                "evidence_entry_range": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "[start, end] entry numbers agent has seen"
                },
                "status": {
                    "type": "string",
                    "enum": ["foreground", "thinking", "appending", "validating"],
                    "default": "thinking",
                    "description": "Initial agent status"
                },
                "parent_agent_id": {
                    "type": "string",
                    "description": "Parent agent ID if this is a fork"
                }
            },
            "required": ["agent_type", "ticket_id", "evidence_file", "evidence_entry_range"]
        }
    },
    {
        "name": "get_agents",
        "description": "Query agents by ticket, type, or status",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Filter by ticket ID"},
                "agent_type": {"type": "string", "description": "Filter by agent type"},
                "status": {"type": "string", "description": "Filter by status"}
            }
        }
    },
    {
        "name": "get_thinking_agents",
        "description": "Get all agents currently thinking on a ticket (need notification on evidence updates)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket ID to check"
                }
            },
            "required": ["ticket_id"]
        }
    },
    {
        "name": "terminate_agent",
        "description": "Terminate an agent's thinking when new evidence invalidates their work",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to terminate"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for termination (e.g., 'User changed direction in entry #5')"
                }
            },
            "required": ["agent_id", "reason"]
        }
    },
    {
        "name": "update_context_check",
        "description": "Update agent's last context check timestamp (heartbeat)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID"
                }
            },
            "required": ["agent_id"]
        }
    },
    {
        "name": "get_registry_stats",
        "description": "Get overall agent registry statistics",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_ticket_status",
        "description": "Get status of all agents for a specific ticket",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket ID to check"
                }
            },
            "required": ["ticket_id"]
        }
    }
]


# Map tool names to functions
AGENT_REGISTRY_TOOL_MAP = {
    "register_agent": register_agent_tool,
    "get_agents": get_agents_tool,
    "get_thinking_agents": get_thinking_agents_tool,
    "terminate_agent": terminate_agent_tool,
    "update_context_check": update_context_check_tool,
    "get_registry_stats": get_registry_stats_tool,
    "get_ticket_status": get_ticket_status_tool,
}

