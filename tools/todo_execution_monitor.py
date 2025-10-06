"""
Zen MCP Tool: Todo Execution Monitor
Real-time monitoring of todo execution status
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
from .simple.base import SimpleTool

FIELD_DESCRIPTIONS = {
    "action": "Action to perform: status, start, update, pause, complete, cancel, monitor",
    "todo_id": "Unique identifier for the todo item",
    "session_id": "Session ID for execution tracking",
    "platform": "Platform context: cursor, claude_code, copilot_chat, chatgpt",
    "agent": "Agent type: pm, architect, dev, universal",
    "provider": "Provider preference: gemini-2.5-flash, gpt-4.1, gpt-5, o3-pro, claude-3.5-sonnet",
    "progress_percent": "Progress percentage (0-100)",
    "current_action": "Current action being performed",
    "context": "Additional context or notes",
    "check_interval": "Monitoring check interval in seconds (default: 30)",
}

class TodoExecutionMonitorRequest(ToolRequest):
    """Request model for Todo Execution Monitor tool"""

    action: str = Field(description=FIELD_DESCRIPTIONS["action"])
    todo_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["todo_id"])
    session_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["session_id"])
    platform: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["platform"])
    agent: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["agent"])
    provider: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["provider"])
    progress_percent: Optional[int] = Field(None, description=FIELD_DESCRIPTIONS["progress_percent"])
    current_action: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["current_action"])
    context: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["context"])
    check_interval: int = Field(default=30, description=FIELD_DESCRIPTIONS["check_interval"])


class TodoExecutionMonitorTool(SimpleTool):
    """
    Real-time monitoring of todo execution status across platforms.
    
    This tool provides comprehensive execution monitoring:
    - Track which todos are currently executing
    - Monitor progress and prevent conflicts
    - Detect stale executions and auto-pause
    - Provide real-time status updates
    - Generate execution reports
    """

    def get_name(self) -> str:
        return "todo_execution_monitor"

    def get_description(self) -> str:
        return "Real-time monitoring of todo execution status across platforms."

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """Return tool-specific field definitions"""
        return {
            "action": {
                "type": "string",
                "description": "Action to perform: status, start, update, pause, complete, cancel, monitor",
                "enum": ["status", "start", "update", "pause", "complete", "cancel", "monitor"]
            },
            "todo_id": {
                "type": "string",
                "description": "Unique identifier for the todo item"
            },
            "session_id": {
                "type": "string",
                "description": "Session ID for execution tracking"
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
                "description": "Provider preference: gemini-2.5-flash, gpt-4.1, gpt-5, o3-pro, claude-3.5-sonnet",
                "enum": ["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4.1", "gpt-5", "gpt-5-codex", "o3-pro", "o3-mini", "claude-3.5-sonnet"]
            },
            "progress_percent": {
                "type": "integer",
                "description": "Progress percentage (0-100)",
                "minimum": 0,
                "maximum": 100
            },
            "current_action": {
                "type": "string",
                "description": "Current action being performed"
            },
            "context": {
                "type": "string",
                "description": "Additional context or notes"
            },
            "check_interval": {
                "type": "integer",
                "description": "Monitoring check interval in seconds (default: 30)",
                "default": 30
            }
        }

    def prepare_prompt(self, request: TodoExecutionMonitorRequest, **kwargs) -> str:
        """Prepare the prompt for execution monitoring"""
        
        if request.action == "status":
            prompt = f"""Check current todo execution status.

Todo ID: {request.todo_id or 'all todos'}
Platform: {request.platform or 'all platforms'}

This tool will:
1. Check which todos are currently executing
2. Show progress and current actions
3. Identify any conflicts or issues
4. Provide recommendations for next steps
5. Generate execution status report

Please execute the execution status check workflow."""

        elif request.action == "start":
            prompt = f"""Start tracking a todo execution.

Todo ID: {request.todo_id}
Platform: {request.platform}
Agent: {request.agent}
Provider: {request.provider}
Context: {request.context or 'Starting execution'}

This tool will:
1. Create a new execution session
2. Start tracking progress and activity
3. Monitor for conflicts with other executions
4. Provide session ID for updates
5. Begin real-time monitoring

Please execute the execution start workflow."""

        elif request.action == "update":
            prompt = f"""Update execution progress.

Session ID: {request.session_id}
Progress: {request.progress_percent}%
Current Action: {request.current_action or 'Continuing work'}
Context: {request.context or 'Progress update'}

This tool will:
1. Update execution progress and status
2. Record current action and context
3. Update last activity timestamp
4. Check for completion criteria
5. Provide updated status

Please execute the execution update workflow."""

        elif request.action == "pause":
            prompt = f"""Pause a todo execution.

Session ID: {request.session_id}
Context: {request.context or 'Pausing execution'}

This tool will:
1. Mark execution as paused
2. Save current progress and context
3. Update last activity timestamp
4. Provide resumption instructions
5. Update execution status

Please execute the execution pause workflow."""

        elif request.action == "complete":
            prompt = f"""Complete a todo execution.

Session ID: {request.session_id}
Context: {request.context or 'Execution completed'}

This tool will:
1. Mark execution as completed
2. Set progress to 100%
3. Calculate total duration
4. Remove from active executions
5. Generate completion report

Please execute the execution completion workflow."""

        elif request.action == "cancel":
            prompt = f"""Cancel a todo execution.

Session ID: {request.session_id}
Context: {request.context or 'Execution cancelled'}

This tool will:
1. Mark execution as cancelled
2. Save cancellation context
3. Remove from active executions
4. Update execution status
5. Provide cancellation report

Please execute the execution cancellation workflow."""

        elif request.action == "monitor":
            prompt = f"""Start real-time execution monitoring.

Check Interval: {request.check_interval} seconds

This tool will:
1. Start background monitoring
2. Check for stale executions
3. Auto-pause inactive executions
4. Provide real-time status updates
5. Generate monitoring reports

Please execute the monitoring start workflow."""

        else:
            prompt = f"""Unknown action: {request.action}

Available actions:
- status: Check current execution status
- start: Start tracking a todo execution
- update: Update execution progress
- pause: Pause a todo execution
- complete: Complete a todo execution
- cancel: Cancel a todo execution
- monitor: Start real-time monitoring

Please specify a valid action."""

        return prompt

    async def _call(self, request: TodoExecutionMonitorRequest, **kwargs) -> Dict[str, Any]:
        """Execute the execution monitoring logic."""
        
        try:
            # Import the execution monitor
            import sys
            from pathlib import Path
            
            # Add the current directory to Python path
            current_dir = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(current_dir))
            
            from todo_execution_monitor import TodoExecutionMonitor
            
            # Initialize monitor
            db_path = os.path.join(os.getcwd(), "todo_execution_monitor.db")
            monitor = TodoExecutionMonitor(db_path)
            
            # Execute based on action
            if request.action == "status":
                return await self._check_execution_status(request, monitor)
            elif request.action == "start":
                return await self._start_execution(request, monitor)
            elif request.action == "update":
                return await self._update_execution(request, monitor)
            elif request.action == "pause":
                return await self._pause_execution(request, monitor)
            elif request.action == "complete":
                return await self._complete_execution(request, monitor)
            elif request.action == "cancel":
                return await self._cancel_execution(request, monitor)
            elif request.action == "monitor":
                return await self._start_monitoring(request, monitor)
            else:
                return {"success": False, "error": f"Unknown action: {request.action}"}
                
        except Exception as e:
            return {"success": False, "error": f"Execution monitoring error: {str(e)}"}

    async def _check_execution_status(self, request: TodoExecutionMonitorRequest, monitor: TodoExecutionMonitor) -> Dict[str, Any]:
        """Check current execution status"""
        
        status = monitor.get_execution_status(request.todo_id)
        active_executions = monitor.get_active_executions()
        
        # Generate status report
        report = monitor.generate_status_report()
        
        return {
            "success": True,
            "action": "status",
            "todo_id": request.todo_id,
            "active_executions": status["active_executions"],
            "paused_executions": status["paused_executions"],
            "executions": status["executions"],
            "report": report,
            "message": f"Found {status['active_executions']} active executions, {status['paused_executions']} paused"
        }

    async def _start_execution(self, request: TodoExecutionMonitorRequest, monitor: TodoExecutionMonitor) -> Dict[str, Any]:
        """Start tracking a todo execution"""
        
        if not all([request.todo_id, request.platform, request.agent, request.provider]):
            return {"success": False, "error": "Missing required fields: todo_id, platform, agent, provider"}
        
        session_id = monitor.start_execution(
            request.todo_id,
            f"Todo execution for {request.todo_id}",
            request.platform,
            request.agent,
            request.provider,
            request.context or "Starting execution"
        )
        
        return {
            "success": True,
            "action": "start",
            "todo_id": request.todo_id,
            "session_id": session_id,
            "platform": request.platform,
            "agent": request.agent,
            "provider": request.provider,
            "message": f"Started execution tracking for {request.todo_id}"
        }

    async def _update_execution(self, request: TodoExecutionMonitorRequest, monitor: TodoExecutionMonitor) -> Dict[str, Any]:
        """Update execution progress"""
        
        if not request.session_id:
            return {"success": False, "error": "session_id required for update action"}
        
        success = monitor.update_execution(
            request.session_id,
            request.progress_percent,
            request.current_action,
            request.context
        )
        
        if success:
            return {
                "success": True,
                "action": "update",
                "session_id": request.session_id,
                "progress_percent": request.progress_percent,
                "current_action": request.current_action,
                "message": f"Updated execution {request.session_id}"
            }
        else:
            return {"success": False, "error": f"Could not find execution session: {request.session_id}"}

    async def _pause_execution(self, request: TodoExecutionMonitorRequest, monitor: TodoExecutionMonitor) -> Dict[str, Any]:
        """Pause a todo execution"""
        
        if not request.session_id:
            return {"success": False, "error": "session_id required for pause action"}
        
        success = monitor.pause_execution(request.session_id, request.context)
        
        if success:
            return {
                "success": True,
                "action": "pause",
                "session_id": request.session_id,
                "status": "paused",
                "message": f"Paused execution {request.session_id}"
            }
        else:
            return {"success": False, "error": f"Could not find execution session: {request.session_id}"}

    async def _complete_execution(self, request: TodoExecutionMonitorRequest, monitor: TodoExecutionMonitor) -> Dict[str, Any]:
        """Complete a todo execution"""
        
        if not request.session_id:
            return {"success": False, "error": "session_id required for complete action"}
        
        success = monitor.complete_execution(request.session_id, request.context)
        
        if success:
            return {
                "success": True,
                "action": "complete",
                "session_id": request.session_id,
                "status": "completed",
                "message": f"Completed execution {request.session_id}"
            }
        else:
            return {"success": False, "error": f"Could not find execution session: {request.session_id}"}

    async def _cancel_execution(self, request: TodoExecutionMonitorRequest, monitor: TodoExecutionMonitor) -> Dict[str, Any]:
        """Cancel a todo execution"""
        
        if not request.session_id:
            return {"success": False, "error": "session_id required for cancel action"}
        
        success = monitor.cancel_execution(request.session_id, request.context)
        
        if success:
            return {
                "success": True,
                "action": "cancel",
                "session_id": request.session_id,
                "status": "cancelled",
                "message": f"Cancelled execution {request.session_id}"
            }
        else:
            return {"success": False, "error": f"Could not find execution session: {request.session_id}"}

    async def _start_monitoring(self, request: TodoExecutionMonitorRequest, monitor: TodoExecutionMonitor) -> Dict[str, Any]:
        """Start real-time monitoring"""
        
        monitor.start_monitoring(request.check_interval)
        
        return {
            "success": True,
            "action": "monitor",
            "check_interval": request.check_interval,
            "message": f"Started real-time monitoring (check every {request.check_interval}s)"
        }
