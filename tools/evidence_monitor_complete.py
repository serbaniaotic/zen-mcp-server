"""
Zen MCP Tool: Evidence Monitor (Complete)

Wraps evidence_monitor_tool.py functions into a SimpleTool for MCP integration.

Constitutional alignment: "Find hope in knowledge and grace in wisdom"
- Hope: Track evidence progression to preserve learning
- Grace: Elegant monitoring without disruption
"""

import logging
from typing import Any, Dict, Optional
from pydantic import Field
from mcp.types import TextContent

from tools.shared.base_models import ToolRequest
from tools.simple.base import SimpleTool
from tools.evidence_monitor_tool import (
    capture_evidence_state_tool,
    check_evidence_updates_tool,
    subscribe_to_evidence_tool,
    unsubscribe_from_evidence_tool,
    start_monitoring_tool,
    stop_monitoring_tool,
    get_monitoring_status_tool,
)

logger = logging.getLogger(__name__)

FIELD_DESCRIPTIONS = {
    "action": "Action to perform: capture, check, subscribe, unsubscribe, start, stop, status",
    "ticket_id": "Ticket ID to monitor",
    "evidence_file": "Path to evidence file",
    "agent_id": "Agent ID for subscription",
    "last_entry_seen": "Last entry number agent has seen (for checking updates)",
    "interval": "Monitoring check interval in seconds (default: 5)",
}


class EvidenceMonitorRequest(ToolRequest):
    """Request model for Evidence Monitor tool"""

    action: str = Field(description=FIELD_DESCRIPTIONS["action"])
    ticket_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["ticket_id"])
    evidence_file: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["evidence_file"])
    agent_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["agent_id"])
    last_entry_seen: Optional[int] = Field(None, description=FIELD_DESCRIPTIONS["last_entry_seen"])
    interval: int = Field(default=5, description=FIELD_DESCRIPTIONS["interval"])


class EvidenceMonitorTool(SimpleTool):
    """
    Monitor evidence files for changes and coordinate agent awareness.
    
    This tool enables agents to:
    - Track evidence file state (entry count, timestamps)
    - Check for new evidence entries  
    - Subscribe to evidence updates
    - Start/stop automated monitoring
    - Prevent stale responses from outdated evidence
    
    Constitutional alignment: Preserves progression intelligence across file boundaries.
    """

    def get_name(self) -> str:
        return "evidence_monitor"

    def get_description(self) -> str:
        return "Monitor evidence files for changes and coordinate agent awareness of new information."

    def get_system_prompt(self) -> str:
        return """You are an evidence monitoring assistant that helps agents stay aware of evidence progression.

Your role:
- Track evidence file state (entry counts, timestamps, hashes)
- Detect when new evidence has been added
- Coordinate agent subscriptions to evidence updates
- Prevent agents from responding with outdated information

When monitoring evidence:
1. Capture baseline state before agent starts thinking
2. Check for updates periodically during long-running analysis
3. Alert agent if evidence changed (invalidate thinking if needed)
4. Preserve progression timeline across file splits

This embodies "hope in knowledge" - we preserve all learning, even across interrupted sessions."""

    def get_request_model(self):
        """Return the custom request model class"""
        return EvidenceMonitorRequest

    def requires_model(self) -> bool:
        """This tool does pure data processing and doesn't need AI model access"""
        return False

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """Return tool-specific field definitions"""
        return {
            "action": {
                "type": "string",
                "description": "Action to perform",
                "enum": ["capture", "check", "subscribe", "unsubscribe", "start", "stop", "status"]
            },
            "ticket_id": {
                "type": "string",
                "description": "Ticket ID to monitor"
            },
            "evidence_file": {
                "type": "string",
                "description": "Path to evidence file (relative to ticket directory)"
            },
            "agent_id": {
                "type": "string",
                "description": "Agent ID for subscription management"
            },
            "last_entry_seen": {
                "type": "integer",
                "description": "Last entry number agent has seen (for update checking)"
            },
            "interval": {
                "type": "integer",
                "description": "Monitoring check interval in seconds (default: 5)",
                "default": 5
            }
        }

    async def prepare_prompt(self, request: EvidenceMonitorRequest, **kwargs) -> str:
        """Prepare the prompt for evidence monitoring action"""

        if request.action == "capture":
            return f"""Capture the current state of evidence file for ticket {request.ticket_id}.

Evidence File: {request.evidence_file}

This action will:
1. Calculate file hash (for collision detection)
2. Count current entries
3. Capture last entry timestamp
4. Record evidence context type
5. Create baseline snapshot for comparison

This establishes a known state that agents can check against for updates."""

        elif request.action == "check":
            return f"""Check for new evidence entries on ticket {request.ticket_id}.

Last Entry Seen: {request.last_entry_seen}

This action will:
1. Scan evidence file for entries > {request.last_entry_seen}
2. Identify what changed (new data, context shifts, etc.)
3. Determine if changes invalidate current thinking
4. Provide update summary for agent coordination

This prevents agents from responding with outdated analysis."""

        elif request.action == "subscribe":
            return f"""Subscribe agent {request.agent_id} to evidence updates for ticket {request.ticket_id}.

This action will:
1. Register agent in evidence subscription system
2. Agent will be notified when evidence changes
3. Enables automated invalidation checking
4. Coordinates multi-agent awareness

This prevents agent confusion from split evidence files."""

        elif request.action == "unsubscribe":
            return f"""Unsubscribe agent {request.agent_id} from ticket {request.ticket_id} updates.

This action will:
1. Remove agent from subscription list
2. Stop sending evidence update notifications
3. Clean up subscription resources

Use when agent completes work on ticket."""

        elif request.action == "start":
            return f"""Start automated monitoring of evidence file.

Ticket: {request.ticket_id}
Evidence File: {request.evidence_file}
Check Interval: {request.interval} seconds

This action will:
1. Begin periodic monitoring (every {request.interval}s)
2. Detect file changes automatically
3. Notify subscribed agents of updates
4. Run in background until stopped

Use for long-running investigation tickets."""

        elif request.action == "stop":
            return f"""Stop automated monitoring for ticket {request.ticket_id}.

This action will:
1. Stop periodic evidence checks
2. Preserve current state snapshot
3. Clean up monitoring resources

Evidence history is preserved."""

        elif request.action == "status":
            return f"""Get monitoring status for all evidence monitors.

This action will:
1. List all active evidence monitors
2. Show subscribed agents per ticket
3. Display monitoring intervals
4. Provide system health status

Useful for debugging coordination issues."""

        else:
            return f"""Unknown action: {request.action}

Available actions:
- capture: Capture evidence file state
- check: Check for new evidence entries
- subscribe: Subscribe agent to updates
- unsubscribe: Unsubscribe from updates
- start: Start automated monitoring
- stop: Stop monitoring
- status: Get monitoring status

Please specify a valid action."""

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the evidence monitoring action."""
        from mcp.types import TextContent
        from tools.models import ToolOutput
        import json

        try:
            # Validate request
            try:
                request = self.get_request_model()(**arguments)
            except Exception as e:
                return self._error(f"Invalid arguments: {e}")

            # Execute action
            if request.action == "capture":
                if not request.ticket_id or not request.evidence_file:
                    return self._error("ticket_id and evidence_file required for capture")
                result = await capture_evidence_state_tool(request.ticket_id, request.evidence_file)

            elif request.action == "check":
                if not request.ticket_id or request.last_entry_seen is None:
                    return self._error("ticket_id and last_entry_seen required for check")
                result = await check_evidence_updates_tool(request.ticket_id, request.last_entry_seen)

            elif request.action == "subscribe":
                if not request.agent_id or not request.ticket_id:
                    return self._error("agent_id and ticket_id required for subscribe")
                result = await subscribe_to_evidence_tool(request.agent_id, request.ticket_id)

            elif request.action == "unsubscribe":
                if not request.agent_id or not request.ticket_id:
                    return self._error("agent_id and ticket_id required for unsubscribe")
                result = await unsubscribe_from_evidence_tool(request.agent_id, request.ticket_id)

            elif request.action == "start":
                if not request.ticket_id or not request.evidence_file:
                    return self._error("ticket_id and evidence_file required for start")
                result = await start_monitoring_tool(request.ticket_id, request.evidence_file, request.interval)

            elif request.action == "stop":
                if not request.ticket_id:
                    return self._error("ticket_id required for stop")
                result = await stop_monitoring_tool(request.ticket_id)

            elif request.action == "status":
                result = await get_monitoring_status_tool()

            else:
                return self._error(f"Unknown action: {request.action}")

            # Format response
            if result.get("success"):
                return self._success(
                    result.get("message", f"Action '{request.action}' completed"),
                    result
                )
            else:
                return self._error(result.get("error", "Action failed"), {"result": result})

        except Exception as e:
            logger.error(f"Evidence monitor error: {e}")
            return self._error(f"Evidence monitoring failed: {str(e)}")

    def _success(self, message: str, data: Dict[str, Any] = None) -> list[TextContent]:
        """Helper to format success responses"""
        from tools.models import ToolOutput
        import json
        from mcp.types import TextContent
        
        tool_output = ToolOutput(
            status="success",
            content=json.dumps({"message": message, "data": data or {}}, indent=2),
            content_type="json",
            metadata={"tool_name": self.get_name()}
        )
        return [TextContent(type="text", text=tool_output.model_dump_json())]

    def _error(self, message: str, details: Dict[str, Any] = None) -> list[TextContent]:
        """Helper to format error responses"""
        from tools.models import ToolOutput
        import json
        from mcp.types import TextContent
        
        error_data = {"error": message}
        if details:
            error_data["details"] = details
            
        tool_output = ToolOutput(
            status="error",
            content=json.dumps(error_data, indent=2),
            content_type="json",
            metadata={"tool_name": self.get_name()}
        )
        return [TextContent(type="text", text=tool_output.model_dump_json())]

