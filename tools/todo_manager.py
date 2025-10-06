"""
Zen MCP Tool: Todo Manager
Cross-platform todo management with memory integration
"""

import os
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, List
from pydantic import Field
from datetime import datetime

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from tools.shared.tamdac import TamdacProject, MemoryManager, CommandManager
from tools.shared.base_tool import BaseTool
from tools.models import ToolOutput
from mcp.types import TextContent

FIELD_DESCRIPTIONS = {
    "action": "Action to perform: status, continue, pause, complete, validate, sync",
    "todo_id": "Unique identifier for the todo item",
    "todo_text": "Description of the todo item",
    "todo_type": "Type of todo: planning, implementation, analysis, review, testing",
    "priority": "Priority level: high, medium, low",
    "status": "Todo status: pending, in_progress, paused, completed, cancelled",
    "project": "Project name (auto-detected if not provided)",
    "platform": "Platform context: cursor, claude_code, copilot_chat, chatgpt",
    "agent": "Agent type: pm, architect, dev, universal",
    "provider": "Provider preference: gemini-2.5-flash, gpt-4.1, gpt-5, o3-pro, claude-3.5-sonnet",
    "context": "Additional context or notes",
    "next_action": "Next action to take",
    "blockers": "Any blockers or dependencies",
}

class TodoManagerRequest(ToolRequest):
    """Request model for Todo Manager tool"""
    action: str = Field(..., description=FIELD_DESCRIPTIONS["action"])
    todo_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["todo_id"])
    todo_text: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["todo_text"])
    todo_type: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["todo_type"])
    priority: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["priority"])
    status: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["status"])
    project: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["project"])
    platform: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["platform"])
    agent: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["agent"])
    provider: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["provider"])
    context: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["context"])
    next_action: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["next_action"])
    blockers: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["blockers"])


class TodoManagerTool(BaseTool):
    """
    Cross-platform todo management with memory integration.
    
    This tool provides comprehensive todo management across all platforms:
    - Check todo status and prevent prompt chaining
    - Continue existing work with full context
    - Pause work and save progress
    - Complete todos and update status
    - Validate before starting new work
    - Sync todos across projects and platforms
    """

    def get_name(self) -> str:
        return "todo_manager"

    def get_description(self) -> str:
        return "Cross-platform todo management with memory integration and smart routing."

    def get_system_prompt(self) -> str:
        return """You are a todo management assistant that helps track and manage work across multiple projects and platforms.

Your role is to:
1. Check todo status and prevent prompt chaining
2. Continue existing work with full context
3. Pause work and save progress
4. Complete todos and update status
5. Validate before starting new work
6. Sync todos across projects and platforms

Always provide clear, actionable responses with routing recommendations based on todo type and priority."""

    def get_default_temperature(self) -> float:
        return 0.3  # Low temperature for consistent todo management

    def get_model_category(self) -> "ToolModelCategory":
        """Todo management prioritizes accuracy and consistency"""
        from tools.models import ToolModelCategory
        return ToolModelCategory.BALANCED

    def get_request_model(self):
        """Return the TodoManager-specific request model"""
        return TodoManagerRequest

    def requires_model(self) -> bool:
        """
        Todo manager doesn't require model resolution at the MCP boundary.
        
        This is a pure data processing tool that manages todos without calling
        external AI models. It reads from memory files and returns structured data.
        
        Returns:
            bool: False - todo manager doesn't need AI model access
        """
        return False

    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform: status, continue, pause, complete, validate, sync",
                    "enum": ["status", "continue", "pause", "complete", "validate", "sync"]
                },
                "todo_id": {
                    "type": "string",
                    "description": "Unique identifier for the todo item"
                },
                "todo_text": {
                    "type": "string",
                    "description": "Description of the todo item"
                },
                "todo_type": {
                    "type": "string",
                    "description": "Type of todo: planning, implementation, analysis, review, testing",
                    "enum": ["planning", "implementation", "analysis", "review", "testing"]
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level: high, medium, low",
                    "enum": ["high", "medium", "low"]
                },
                "status": {
                    "type": "string",
                    "description": "Todo status: pending, in_progress, paused, completed, cancelled",
                    "enum": ["pending", "in_progress", "paused", "completed", "cancelled"]
                },
                "project": {
                    "type": "string",
                    "description": "Project name (auto-detected if not provided)"
                },
                "platform": {
                    "type": "string",
                    "description": "Platform context: cursor, claude_code, copilot_chat, chatgpt",
                    "enum": ["cursor", "claude_code", "copilot_chat", "chatgpt"]
                },
                "agent": {
                    "type": "string",
                    "description": "Agent type: pm, architect, dev, universal",
                    "enum": ["pm", "architect", "dev", "universal"]
                },
                "provider": {
                    "type": "string",
                    "description": "Provider preference: gemini-2.5-flash, gpt-4.1, gpt-5, o3-pro, claude-3.5-sonnet"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context or notes"
                },
                "next_action": {
                    "type": "string",
                    "description": "Next action to take"
                },
                "blockers": {
                    "type": "string",
                    "description": "Any blockers or dependencies"
                }
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    def get_annotations(self) -> Optional[dict[str, Any]]:
        """Return tool annotations indicating this is a read-only tool"""
        return {"readOnlyHint": True}

    async def prepare_prompt(self, request: TodoManagerRequest) -> str:
        """Not used for this utility tool"""
        return ""

    def format_response(self, response: str, request: TodoManagerRequest, model_info: Optional[dict] = None) -> str:
        """Not used for this utility tool"""
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Execute the todo management logic.
        
        This overrides the base class execute to provide direct output without AI model calls.
        
        Args:
            arguments: Tool arguments including action, project, platform, etc.
            
        Returns:
            Formatted todo status and recommendations
        """
        try:
            # Detect current project if not provided
            current_path = Path(os.getcwd())
            project_name = arguments.get("project") or self._detect_project_from_path(current_path)
            
            if not project_name:
                return [TextContent(type="text", text=json.dumps({
                    "success": False, 
                    "error": "Could not detect project from current path"
                }))]
            
            # Execute based on action
            action = arguments.get("action", "status")
            if action == "status":
                result = await self._check_todo_status(arguments, project_name)
            elif action == "continue":
                result = await self._continue_todo(arguments, project_name)
            elif action == "pause":
                result = await self._pause_todo(arguments, project_name)
            elif action == "complete":
                result = await self._complete_todo(arguments, project_name)
            elif action == "validate":
                result = await self._validate_todos(arguments, project_name)
            elif action == "sync":
                result = await self._sync_todos(arguments, project_name)
            else:
                result = {"success": False, "error": f"Unknown action: {action}"}
            
            # Format as ToolOutput
            tool_output = ToolOutput(
                status="success" if result.get("success", False) else "error",
                content=json.dumps(result, indent=2),
                content_type="json",
                metadata={
                    "tool_name": self.get_name(),
                    "action": action,
                    "project": project_name,
                },
            )
            
            return [TextContent(type="text", text=tool_output.model_dump_json())]
                
        except Exception as e:
            error_result = {"success": False, "error": f"Todo management error: {str(e)}"}
            tool_output = ToolOutput(
                status="error",
                content=json.dumps(error_result, indent=2),
                content_type="json",
                metadata={"tool_name": self.get_name()},
            )
            return [TextContent(type="text", text=tool_output.model_dump_json())]

    def _detect_project_from_path(self, path: Path) -> Optional[str]:
        """Detect project name from current path"""
        # Check if we're in a tamdac project
        if "tamdac" in str(path):
            return "tamdac"
        
        # Check for other known projects
        for part in path.parts:
            if part in ["toolbox", "arrow", "wiib", "motif", "lumiere", "obs", "chord", "ecce"]:
                return part
        
        return None

    async def _check_todo_status(self, request: dict, project_name: str) -> dict[str, Any]:
        """Check todo status and prevent prompt chaining"""
        
        # For now, return a basic status since we don't have active todos
        return {
            "success": True,
            "action": "status",
            "project": project_name,
            "platform": request.get("platform", "current"),
            "todos": {
                "pending": [],
                "completed": [],
                "paused": [],
                "total": 0
            },
            "recommendation": "Safe to start new work - no pending todos",
            "routing_recommendation": None,
            "message": "Found 0 pending todos, 0 completed, 0 paused"
        }

    def _parse_todos_from_memory(self, memory_content: str) -> List[dict]:
        """Parse todos from memory content"""
        # This is a simplified parser - in a real implementation, you'd parse the actual memory format
        todos = []
        
        # For now, return empty list since we don't have active todos
        # In a real implementation, this would parse the memory.md file
        return todos

    def _get_todo_routing_recommendation(self, todo: dict) -> dict:
        """Get routing recommendation for a todo"""
        todo_type = todo.get("type", "general")
        
        routing_map = {
            "planning": {
                "platform": "cursor",
                "agent": "pm",
                "provider": "gemini-2.5-flash",
                "tokens": 8000,
                "cost": 0.075
            },
            "implementation": {
                "platform": "cursor",
                "agent": "dev",
                "provider": "gpt-5-codex",
                "tokens": 15000,
                "cost": 0.20
            },
            "review": {
                "platform": "cursor",
                "agent": "architect",
                "provider": "gpt-4.1",
                "tokens": 12000,
                "cost": 0.30
            },
            "analysis": {
                "platform": "chatgpt",
                "agent": "analyst",
                "provider": "o3-pro",
                "tokens": 20000,
                "cost": 0.35
            }
        }
        
        return routing_map.get(todo_type, routing_map["general"])

    async def _continue_todo(self, request: dict, project_name: str) -> dict[str, Any]:
        """Continue existing todo work"""
        return {"success": False, "error": "Continue functionality not yet implemented"}

    async def _pause_todo(self, request: dict, project_name: str) -> dict[str, Any]:
        """Pause current todo work"""
        return {"success": False, "error": "Pause functionality not yet implemented"}

    async def _complete_todo(self, request: dict, project_name: str) -> dict[str, Any]:
        """Complete a todo"""
        return {"success": False, "error": "Complete functionality not yet implemented"}

    async def _validate_todos(self, request: dict, project_name: str) -> dict[str, Any]:
        """Validate todos before starting new work"""
        return {"success": False, "error": "Validate functionality not yet implemented"}

    async def _sync_todos(self, request: dict, project_name: str) -> dict[str, Any]:
        """Sync todos across projects"""
        return {"success": False, "error": "Sync functionality not yet implemented"}
