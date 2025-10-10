"""
Zen MCP Tool: Agent Handover for Multi-Agent Workflows
Coordinates smooth transitions between specialized agents with context preservation
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List

from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.shared.base_tool import BaseTool
from mcp.types import TextContent

# smartmemoryapi endpoint
SMARTMEMORY_URL = os.getenv("SMARTMEMORY_URL", "http://localhost:8099")

class AgentHandoverRequest(ToolRequest):
    """Request model for Agent Handover tool"""
    
    from_agent: str = Field(..., description="Current agent role (e.g., 'research-agent')")
    to_agent: str = Field(..., description="Next agent role (e.g., 'script-agent')")
    ticket_id: str = Field(..., description="Ticket ID being worked on")
    phase_complete: str = Field(..., description="Phase just completed (e.g., 'research')")
    next_phase: str = Field(..., description="Next phase to begin (e.g., 'script')")
    summary: str = Field(..., description="Summary of work completed")
    key_findings: Optional[List[str]] = Field(None, description="Key findings to pass along")
    files_modified: Optional[List[str]] = Field(None, description="Files modified in this phase")
    pinecone_queries: Optional[List[str]] = Field(None, description="Recommended Pinecone queries for next agent")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context data")


class AgentHandoverTool(BaseTool):
    """
    Coordinates handover between specialized agents in multi-agent workflows.

    Implements the "short-lived agent" pattern:
    1. Current agent completes phase
    2. Stores work summary in Pinecone
    3. Terminates (fresh context)
    4. Next agent loads summary from Pinecone
    5. Continues work with minimal tokens

    This prevents context pollution and enables 83% token reduction.
    """

    def get_name(self) -> str:
        return "agent_handover"

    def get_description(self) -> str:
        return "Coordinates smooth handover between specialized agents with context preservation in Pinecone"

    def requires_model(self) -> bool:
        """Agent handover is a coordination utility - no AI model needed"""
        return False

    def get_input_schema(self) -> dict[str, Any]:
        """Generate schema from AgentHandoverRequest Pydantic model"""
        return AgentHandoverRequest.model_json_schema()

    def get_system_prompt(self) -> str:
        """Not used - agent handover doesn't use AI"""
        return ""

    async def prepare_prompt(self, request) -> str:
        """Not used - agent handover doesn't use AI prompts"""
        return ""

    def get_request_model(self) -> type[ToolRequest]:
        return AgentHandoverRequest

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Execute agent handover workflow:
        1. Store phase completion in Pinecone
        2. Create handover manifest file
        3. Provide next agent context
        """
        try:
            request = self.get_request_model()(**arguments)
        except Exception as e:
            return self._error(f"Invalid arguments: {e}")

        # Create handover data
        handover_data = {
            "handover_id": f"{request.ticket_id}_{request.phase_complete}_to_{request.next_phase}",
            "timestamp": datetime.now().isoformat(),
            "from_agent": request.from_agent,
            "to_agent": request.to_agent,
            "ticket_id": request.ticket_id,
            "phase_complete": request.phase_complete,
            "next_phase": request.next_phase,
            "summary": request.summary,
            "key_findings": request.key_findings or [],
            "files_modified": request.files_modified or [],
            "pinecone_queries": request.pinecone_queries or [],
            "context": request.context or {}
        }

        # Store in Pinecone for next agent
        try:
            pinecone_content = self._format_for_pinecone(handover_data)
            stored = self._store_in_pinecone(pinecone_content, handover_data)
        except Exception as e:
            # Pinecone failure shouldn't block handover
            stored = False
            pinecone_error = str(e)

        # Create handover manifest file
        manifest_path = self._create_handover_manifest(handover_data)

        # Generate next agent instructions
        next_agent_instructions = self._generate_next_agent_instructions(handover_data)

        # Build response
        result = {
            "handover_complete": True,
            "from_agent": request.from_agent,
            "to_agent": request.to_agent,
            "phase_complete": request.phase_complete,
            "next_phase": request.next_phase,
            "manifest_path": str(manifest_path) if manifest_path else None,
            "pinecone_stored": stored,
            "next_agent_instructions": next_agent_instructions
        }

        if not stored:
            result["pinecone_warning"] = f"Failed to store in Pinecone: {pinecone_error if 'pinecone_error' in locals() else 'Unknown error'}"

        return self._success(
            f"Handover from {request.from_agent} to {request.to_agent} complete. Next phase: {request.next_phase}",
            result
        )

    def _format_for_pinecone(self, handover_data: Dict) -> str:
        """Format handover data for Pinecone storage"""
        content = f"Agent Handover: {handover_data['from_agent']} → {handover_data['to_agent']}\n\n"
        content += f"Ticket: {handover_data['ticket_id']}\n"
        content += f"Phase Completed: {handover_data['phase_complete']}\n\n"
        content += f"Summary: {handover_data['summary']}\n\n"
        
        if handover_data['key_findings']:
            content += "Key Findings:\n"
            for finding in handover_data['key_findings']:
                content += f"- {finding}\n"
        
        if handover_data['pinecone_queries']:
            content += "\nRecommended queries for next agent:\n"
            for query in handover_data['pinecone_queries']:
                content += f"- {query}\n"
        
        return content

    def _store_in_pinecone(self, content: str, handover_data: Dict) -> bool:
        """Store handover data in Pinecone via smartmemoryapi"""
        try:
            import requests
            
            response = requests.post(
                f"{SMARTMEMORY_URL}/extract",
                json={
                    "user_message": content,
                    "recent_history": [],
                    "metadata": {
                        "type": "agent_handover",
                        "ticket_id": handover_data["ticket_id"],
                        "from_agent": handover_data["from_agent"],
                        "to_agent": handover_data["to_agent"],
                        "phase": handover_data["phase_complete"],
                        "next_phase": handover_data["next_phase"],
                        "timestamp": handover_data["timestamp"]
                    }
                },
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception:
            return False

    def _create_handover_manifest(self, handover_data: Dict) -> Optional[Path]:
        """Create handover manifest file in ticket directory"""
        try:
            # Assume ticket directory structure
            ticket_dir = Path(f"/home/dingo/code/toolbox-workspace/tickets/open/{handover_data['ticket_id']}")
            
            if not ticket_dir.exists():
                # Try without 'open' subdirectory
                ticket_dir = Path(f"/home/dingo/code/toolbox-workspace/tickets/{handover_data['ticket_id']}")
            
            if not ticket_dir.exists():
                return None
            
            manifest_path = ticket_dir / f".handover_{handover_data['phase_complete']}_to_{handover_data['next_phase']}.json"
            
            with open(manifest_path, 'w') as f:
                json.dump(handover_data, f, indent=2)
            
            return manifest_path
        except Exception:
            return None

    def _generate_next_agent_instructions(self, handover_data: Dict) -> str:
        """Generate instructions for next agent to load context"""
        instructions = f"""
# Context for {handover_data['to_agent']}

**Ticket**: {handover_data['ticket_id']}
**Phase**: {handover_data['next_phase']}
**Previous Phase**: {handover_data['phase_complete']} (completed by {handover_data['from_agent']})

## Summary of Previous Work

{handover_data['summary']}

## Key Findings
"""
        
        if handover_data['key_findings']:
            for finding in handover_data['key_findings']:
                instructions += f"\n- {finding}"
        else:
            instructions += "\n(No specific findings documented)"
        
        instructions += "\n\n## Files to Review\n"
        
        if handover_data['files_modified']:
            for file_path in handover_data['files_modified']:
                instructions += f"\n- {file_path}"
        else:
            instructions += "\n(No files modified in previous phase)"
        
        instructions += "\n\n## Load Context from Pinecone\n"
        
        if handover_data['pinecone_queries']:
            instructions += "\nRecommended queries:\n"
            for query in handover_data['pinecone_queries']:
                instructions += f"\n- `{query}`"
        else:
            instructions += f"\n- Query: `ticket {handover_data['ticket_id']} {handover_data['phase_complete']} findings`"
        
        instructions += f"\n\n## Your Task\n\nBegin {handover_data['next_phase']} phase. Load context from Pinecone using queries above, then proceed with your work."
        
        return instructions

