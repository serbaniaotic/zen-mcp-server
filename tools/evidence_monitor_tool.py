"""
Evidence Monitor MCP Tools

Exposes evidence monitoring operations as MCP tools.
"""

import logging
from typing import Any, Dict

from .evidence_monitor import EvidenceUpdate, get_monitor

logger = logging.getLogger(__name__)


async def capture_evidence_state_tool(
    ticket_id: str,
    evidence_file: str
) -> Dict[str, Any]:
    """
    Capture current state of an evidence file.
    
    Args:
        ticket_id: Ticket ID
        evidence_file: Path to evidence file
        
    Returns:
        Evidence state snapshot
    """
    try:
        monitor = get_monitor()
        state = await monitor.capture_state(ticket_id, evidence_file)
        
        return {
            "success": True,
            "ticket_id": state.ticket_id,
            "evidence_file": state.evidence_file,
            "entry_count": state.entry_count,
            "last_entry_timestamp": state.last_entry_timestamp,
            "context_type": state.context_type,
            "file_hash": state.file_hash,
            "captured_at": state.captured_at
        }
        
    except Exception as e:
        logger.error(f"Failed to capture evidence state: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def check_evidence_updates_tool(
    ticket_id: str,
    last_entry_seen: int
) -> Dict[str, Any]:
    """
    Check for new evidence entries since last known state.
    
    Args:
        ticket_id: Ticket to check
        last_entry_seen: Last entry number agent has seen
        
    Returns:
        List of new updates
    """
    try:
        monitor = get_monitor()
        
        # Check for updates
        updates = await monitor.check_for_updates(
            ticket_id,
            (1, last_entry_seen)
        )
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "new_entries_count": len(updates),
            "updates": [
                {
                    "entry_number": u.new_entry_number,
                    "timestamp": u.entry.timestamp,
                    "source": u.source,
                    "context_changed": u.context_changed,
                    "invalidates_thinking": u.invalidates_thinking,
                    "reason": u.reason
                }
                for u in updates
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to check evidence updates: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def subscribe_to_evidence_tool(
    agent_id: str,
    ticket_id: str
) -> Dict[str, Any]:
    """
    Subscribe an agent to evidence updates.
    
    Args:
        agent_id: Agent ID
        ticket_id: Ticket to monitor
        
    Returns:
        Subscription status
    """
    try:
        monitor = get_monitor()
        success = await monitor.subscribe(agent_id, ticket_id)
        
        logger.info(f"Agent {agent_id} subscribed to ticket {ticket_id}")
        
        return {
            "success": success,
            "agent_id": agent_id,
            "ticket_id": ticket_id,
            "message": f"Agent will be notified of evidence updates to ticket {ticket_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to subscribe agent: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def unsubscribe_from_evidence_tool(
    agent_id: str,
    ticket_id: str
) -> Dict[str, Any]:
    """
    Unsubscribe an agent from evidence updates.
    
    Args:
        agent_id: Agent ID
        ticket_id: Ticket to stop monitoring
        
    Returns:
        Unsubscription status
    """
    try:
        monitor = get_monitor()
        success = await monitor.unsubscribe(agent_id, ticket_id)
        
        return {
            "success": success,
            "agent_id": agent_id,
            "ticket_id": ticket_id
        }
        
    except Exception as e:
        logger.error(f"Failed to unsubscribe agent: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def start_monitoring_tool(
    ticket_id: str,
    evidence_file: str,
    interval: int = 5
) -> Dict[str, Any]:
    """
    Start monitoring an evidence file for changes.
    
    Args:
        ticket_id: Ticket ID
        evidence_file: Path to evidence file
        interval: Check interval in seconds (default: 5)
        
    Returns:
        Monitoring status
    """
    try:
        monitor = get_monitor()
        await monitor.start_monitoring(ticket_id, evidence_file, interval)
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "evidence_file": evidence_file,
            "interval": interval,
            "message": f"Started monitoring ticket {ticket_id} every {interval}s"
        }
        
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def stop_monitoring_tool(ticket_id: str) -> Dict[str, Any]:
    """
    Stop monitoring an evidence file.
    
    Args:
        ticket_id: Ticket to stop monitoring
        
    Returns:
        Stop status
    """
    try:
        monitor = get_monitor()
        await monitor.stop_monitoring(ticket_id)
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "message": f"Stopped monitoring ticket {ticket_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_monitoring_status_tool() -> Dict[str, Any]:
    """
    Get status of all evidence monitoring.
    
    Returns:
        Monitoring status
    """
    try:
        monitor = get_monitor()
        status = await monitor.get_monitoring_status()
        
        return {
            "success": True,
            **status
        }
        
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Tool definitions for MCP server
EVIDENCE_MONITOR_TOOLS = [
    {
        "name": "capture_evidence_state",
        "description": "Capture current state of an evidence file (entry count, hash, timestamp)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket ID"
                },
                "evidence_file": {
                    "type": "string",
                    "description": "Path to evidence file to capture"
                }
            },
            "required": ["ticket_id", "evidence_file"]
        }
    },
    {
        "name": "check_evidence_updates",
        "description": "Check for new evidence entries since last known state",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket ID to check"
                },
                "last_entry_seen": {
                    "type": "integer",
                    "description": "Last entry number agent has seen"
                }
            },
            "required": ["ticket_id", "last_entry_seen"]
        }
    },
    {
        "name": "subscribe_to_evidence",
        "description": "Subscribe an agent to evidence updates (will be notified of new entries)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID to subscribe"
                },
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket to monitor"
                }
            },
            "required": ["agent_id", "ticket_id"]
        }
    },
    {
        "name": "unsubscribe_from_evidence",
        "description": "Unsubscribe an agent from evidence updates",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Agent ID"
                },
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket to stop monitoring"
                }
            },
            "required": ["agent_id", "ticket_id"]
        }
    },
    {
        "name": "start_monitoring_evidence",
        "description": "Start periodic monitoring of an evidence file (checks every N seconds)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket ID"
                },
                "evidence_file": {
                    "type": "string",
                    "description": "Path to evidence file"
                },
                "interval": {
                    "type": "integer",
                    "default": 5,
                    "description": "Check interval in seconds (default: 5)"
                }
            },
            "required": ["ticket_id", "evidence_file"]
        }
    },
    {
        "name": "stop_monitoring_evidence",
        "description": "Stop monitoring an evidence file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "Ticket to stop monitoring"
                }
            },
            "required": ["ticket_id"]
        }
    },
    {
        "name": "get_monitoring_status",
        "description": "Get status of all evidence monitoring (active monitors, subscribers)",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


# Map tool names to functions
EVIDENCE_MONITOR_TOOL_MAP = {
    "capture_evidence_state": capture_evidence_state_tool,
    "check_evidence_updates": check_evidence_updates_tool,
    "subscribe_to_evidence": subscribe_to_evidence_tool,
    "unsubscribe_from_evidence": unsubscribe_from_evidence_tool,
    "start_monitoring_evidence": start_monitoring_tool,
    "stop_monitoring_evidence": stop_monitoring_tool,
    "get_monitoring_status": get_monitoring_status_tool,
}

