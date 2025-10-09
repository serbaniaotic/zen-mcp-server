"""
Zen MCP Tool: Context Retriever (Complete)

Wraps context_retriever.py ContextRetriever class into a SimpleTool for MCP integration.

Constitutional alignment: "Find hope in knowledge and grace in wisdom"
- Hope: Preserve complete progression timeline (knowledge never lost)
- Grace: Elegant timeline stitching across file boundaries
"""

import logging
from typing import Any, Dict, Optional
from pydantic import Field
from mcp.types import TextContent

from tools.shared.base_models import ToolRequest
from tools.simple.base import SimpleTool
from tools.context_retriever import get_retriever

logger = logging.getLogger(__name__)

FIELD_DESCRIPTIONS = {
    "action": "Action to perform: retrieve, stitch, link",
    "ticket_id": "Ticket ID for context retrieval",
    "context_file": "Primary context file to retrieve from",
    "file_paths": "List of file paths to stitch together (comma-separated)",
    "target_file": "Target file for link entry",
    "source_file": "Source file for link entry",
    "entry_number": "Entry number in source file",
    "context_type": "Context type for link entry",
}


class ContextRetrieverRequest(ToolRequest):
    """Request model for Context Retriever tool"""

    action: str = Field(description=FIELD_DESCRIPTIONS["action"])
    ticket_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["ticket_id"])
    context_file: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["context_file"])
    file_paths: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["file_paths"])
    target_file: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["target_file"])
    source_file: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["source_file"])
    entry_number: Optional[int] = Field(None, description=FIELD_DESCRIPTIONS["entry_number"])
    context_type: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["context_type"])


class ContextRetrieverTool(SimpleTool):
    """
    Retrieve and stitch context files to preserve progression timeline.
    
    This tool enables agents to:
    - Retrieve full context from split files (automatic chain following)
    - Stitch multiple evidence files into coherent timeline
    - Create link entries for cross-context evidence
    - Reconstruct complete progression history
    
    Constitutional alignment: Preserves complete learning timeline across file splits.
    """

    def get_name(self) -> str:
        return "context_retriever"

    def get_description(self) -> str:
        return "Retrieve and stitch context files to preserve progression timeline across splits."

    def get_request_model(self):
        """Return the custom request model class"""
        return ContextRetrieverRequest

    def requires_model(self) -> bool:
        """This tool does pure data processing and doesn't need AI model access"""
        return False

    def get_system_prompt(self) -> str:
        return """You are a context retrieval assistant that helps agents access complete progression timelines.

Your role:
- Retrieve full context from split evidence files
- Automatically follow evidence chains (file-001 → file-002 → file-003)
- Stitch multiple files into coherent timeline
- Create link entries to connect related contexts

When retrieving context:
1. Start with primary context file
2. Follow chain links (previous/next context files)
3. Preserve chronological order
4. Include all evidence in timeline
5. Present as coherent narrative

This embodies "hope in knowledge" - we preserve complete progression intelligence,
never losing context due to file splits or token limits.

When an agent asks "What's the history of this investigation?", you provide the
COMPLETE timeline, not just the most recent file."""

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """Return tool-specific field definitions"""
        return {
            "action": {
                "type": "string",
                "description": "Action to perform",
                "enum": ["retrieve", "stitch", "link"]
            },
            "ticket_id": {
                "type": "string",
                "description": "Ticket ID for context retrieval"
            },
            "context_file": {
                "type": "string",
                "description": "Primary context file to retrieve from"
            },
            "file_paths": {
                "type": "string",
                "description": "Comma-separated list of file paths to stitch together"
            },
            "target_file": {
                "type": "string",
                "description": "Target file for link entry creation"
            },
            "source_file": {
                "type": "string",
                "description": "Source file for link entry (contains full evidence)"
            },
            "entry_number": {
                "type": "integer",
                "description": "Entry number in source file to link to"
            },
            "context_type": {
                "type": "string",
                "description": "Context type for link entry (e.g., 'diagnostic', 'research')"
            }
        }

    async def prepare_prompt(self, request: ContextRetrieverRequest, **kwargs) -> str:
        """Prepare the prompt for context retrieval action"""

        if request.action == "retrieve":
            return f"""Retrieve full context timeline for ticket {request.ticket_id}.

Context File: {request.context_file}

This action will:
1. Start with primary context file
2. Automatically detect if this file is part of a chain
3. Follow previous/next file links
4. Retrieve ALL files in the chain
5. Stitch together in chronological order
6. Return complete progression timeline

This ensures agents never respond with incomplete context due to file splits.

Use case: "What's the complete history of this investigation?" → Returns full timeline
from all split files, not just the most recent one."""

        elif request.action == "stitch":
            file_list = request.file_paths.split(',') if request.file_paths else []
            return f"""Stitch multiple context files into coherent timeline.

Files to Stitch: {len(file_list)} files
{chr(10).join(f'  - {f.strip()}' for f in file_list)}

This action will:
1. Read all specified files
2. Extract timestamps and entry numbers
3. Sort chronologically
4. Merge into single coherent timeline
5. Preserve all evidence without duplication

This is useful when evidence is split across multiple files without explicit chain links,
or when you want to create a summary timeline from multiple contexts.

Use case: Merge diagnostic.md + research.md + deployment.md into complete story."""

        elif request.action == "link":
            return f"""Create a link entry connecting two evidence files.

Target File: {request.target_file}
Source File: {request.source_file}
Entry: #{request.entry_number}
Context: {request.context_type}

This action will:
1. Create a link entry in target file
2. Link points to full evidence in source file
3. Avoids duplication across context types
4. Preserves evidence relationships

This is used when evidence has multiple contexts (e.g., both "diagnostic" and "performance").
Instead of duplicating, we create a link entry saying "See diagnostic.md entry #5 for full details."

Use case: Evidence about database performance also relates to deployment timeline,
so deployment.md gets a link to the full analysis in performance.md."""

        else:
            return f"""Unknown action: {request.action}

Available actions:
- retrieve: Get full context from chain of split files
- stitch: Merge multiple files into timeline
- link: Create cross-reference link entry

Please specify a valid action."""

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the context retrieval action."""
        from mcp.types import TextContent
        from tools.models import ToolOutput
        import json

        try:
            # Validate request
            try:
                request = self.get_request_model()(**arguments)
            except Exception as e:
                return self._error(f"Invalid arguments: {e}")

            retriever = get_retriever()

            # Execute action
            if request.action == "retrieve":
                if not request.context_file:
                    return self._error("context_file required for retrieve")
                
                # Get full context chain - returns tuple (stitched_content, chain)
                stitched_content, chain = await retriever.get_full_context(request.context_file)
                
                result = {
                    "success": True,
                    "primary_file": chain.primary_file,
                    "chain_files": chain.chain_files,
                    "total_entries": chain.total_entries,
                    "context_type": chain.context_type,
                    "date_range": {
                        "earliest": chain.date_range[0],
                        "latest": chain.date_range[1]
                    },
                    "file_count": len(chain.chain_files),
                    "content_length": len(stitched_content),
                    "message": f"Retrieved {len(chain.chain_files)} files with {chain.total_entries} total entries"
                }

            elif request.action == "stitch":
                if not request.file_paths:
                    return self._error("file_paths required for stitch")
                
                # Parse file paths
                file_list = [f.strip() for f in request.file_paths.split(',')]
                
                # Stitch files together
                stitched_content = await retriever._stitch_files(file_list)
                
                result = {
                    "success": True,
                    "file_count": len(file_list),
                    "files": file_list,
                    "stitched_content": stitched_content,
                    "content_length": len(stitched_content),
                    "message": f"Stitched {len(file_list)} files into timeline"
                }

            elif request.action == "link":
                if not all([request.target_file, request.source_file, request.entry_number, request.context_type]):
                    return self._error("target_file, source_file, entry_number, and context_type required for link")
                
                # Create link entry
                link_entry = await retriever.create_link_entry(
                    request.target_file,
                    request.source_file,
                    request.entry_number,
                    request.context_type
                )
                
                result = {
                    "success": True,
                    "target_file": request.target_file,
                    "source_file": request.source_file,
                    "entry_number": request.entry_number,
                    "link_entry": link_entry,
                    "message": f"Created link entry pointing to {request.source_file} #{request.entry_number}"
                }

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
            logger.error(f"Context retrieval error: {e}")
            return self._error(f"Context retrieval failed: {str(e)}")

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

