"""
Zen MCP Tool: Persistent Memory Manager
Manages persistent memory that survives server crashes and restarts
"""

import os
import json
import time
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List
from pydantic import Field
from datetime import datetime

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from tools.shared.tamdac import TamdacProject, MemoryManager, CommandManager
from .simple.base import SimpleTool

# Import persistent_memory_manager from the parent directory
from persistent_memory_manager import PersistentMemoryManager

FIELD_DESCRIPTIONS = {
    "action": "Action to perform: status, start, update, pause, complete, recovery_info, checkpoint",
    "todo_id": "Unique identifier for the todo item",
    "session_id": "Session ID for execution tracking",
    "platform": "Platform context: cursor, claude_code, copilot_chat, chatgpt",
    "agent": "Agent type: pm, architect, dev, universal",
    "provider": "Provider preference: gemini-2.5-flash, gpt-4.1, gpt-5, o3-pro, claude-3.5-sonnet",
    "progress_percent": "Progress percentage (0-100)",
    "current_action": "Current action being performed",
    "context": "Additional context or notes",
    "force_checkpoint": "Force immediate checkpoint creation",
    "window_id": "Window ID for multi-window todo management",
    "sync_all": "Synchronize todos across all windows",
    "show_conflicts": "Show todos that are active in multiple windows",
    "unified_view": "Show unified dashboard of all todos",
}

class PersistentMemoryRequest(ToolRequest):
    """Request model for Persistent Memory Manager tool"""

    action: str = Field(description=FIELD_DESCRIPTIONS["action"])
    todo_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["todo_id"])
    session_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["session_id"])
    platform: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["platform"])
    agent: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["agent"])
    provider: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["provider"])
    progress_percent: Optional[int] = Field(None, description=FIELD_DESCRIPTIONS["progress_percent"])
    current_action: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["current_action"])
    context: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["context"])
    force_checkpoint: bool = Field(default=False, description=FIELD_DESCRIPTIONS["force_checkpoint"])
    window_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["window_id"])
    sync_all: bool = Field(default=False, description=FIELD_DESCRIPTIONS["sync_all"])
    show_conflicts: bool = Field(default=False, description=FIELD_DESCRIPTIONS["show_conflicts"])
    unified_view: bool = Field(default=True, description=FIELD_DESCRIPTIONS["unified_view"])


class PersistentMemoryTool(SimpleTool):
    """
    Persistent memory management that survives server crashes and restarts.
    
    This tool provides crash-resistant execution tracking:
    - Persistent storage across server restarts
    - Automatic crash recovery and state restoration
    - Checkpoint-based incremental saves
    - Graceful shutdown handling
    - Cross-session continuity
    """

    def get_name(self) -> str:
        return "persistent_memory"

    def get_description(self) -> str:
        return "Persistent memory management that survives server crashes and restarts."

    def get_system_prompt(self) -> str:
        return """You are a persistent memory management system that ensures work continuity across context window limits, server crashes, and platform switches.

Your role is to:
1. Track execution sessions with unique IDs
2. Store progress and context persistently
3. Enable crash recovery and state restoration
4. Provide seamless work continuation
5. Maintain cross-platform compatibility
6. Auto-detect context window thresholds and start protection
7. Integrate with AI responses to reference persistent state

Always provide clear status updates and actionable next steps. When responding to prompts, automatically reference persistent execution state when available."""

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """Return tool-specific field definitions"""
        return {
            "action": {
                "type": "string",
                "description": "Action to perform: status, start, update, pause, complete, recovery_info, checkpoint, recovery_summary, multi_window_todos",
                "enum": ["status", "start", "update", "pause", "complete", "recovery_info", "checkpoint", "recovery_summary", "multi_window_todos"]
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
            "force_checkpoint": {
                "type": "boolean",
                "description": "Force immediate checkpoint creation",
                "default": False
            },
            "window_id": {
                "type": "string",
                "description": "Window ID for multi-window todo management"
            },
            "sync_all": {
                "type": "boolean",
                "description": "Synchronize todos across all windows",
                "default": False
            },
            "show_conflicts": {
                "type": "boolean",
                "description": "Show todos that are active in multiple windows",
                "default": False
            },
            "unified_view": {
                "type": "boolean",
                "description": "Show unified dashboard of all todos",
                "default": True
            }
        }

    def prepare_prompt(self, request: PersistentMemoryRequest, **kwargs) -> str:
        """Prepare the prompt for persistent memory management"""
        
        if request.action == "status":
            prompt = f"""Check persistent memory status and crash recovery information.

Todo ID: {request.todo_id or 'all todos'}
Platform: {request.platform or 'all platforms'}

This tool will:
1. Check persistent execution status
2. Show crash recovery information
3. Display checkpoint history
4. Provide persistence statistics
5. Generate recovery report

Please execute the persistent memory status check workflow."""

        elif request.action == "start":
            prompt = f"""Start persistent execution tracking.

Todo ID: {request.todo_id}
Platform: {request.platform}
Agent: {request.agent}
Provider: {request.provider}
Context: {request.context or 'Starting persistent execution'}

This tool will:
1. Create persistent execution session
2. Initialize crash-resistant storage
3. Start checkpoint monitoring
4. Provide session ID for updates
5. Enable crash recovery

Please execute the persistent execution start workflow."""

        elif request.action == "update":
            prompt = f"""Update persistent execution progress.

Session ID: {request.session_id}
Progress: {request.progress_percent}%
Current Action: {request.current_action or 'Continuing work'}
Context: {request.context or 'Progress update'}

This tool will:
1. Update execution progress with persistence
2. Create checkpoint if needed
3. Record current action and context
4. Update last activity timestamp
5. Ensure crash recovery capability

Please execute the persistent execution update workflow."""

        elif request.action == "pause":
            prompt = f"""Pause persistent execution.

Session ID: {request.session_id}
Context: {request.context or 'Pausing execution'}

This tool will:
1. Mark execution as paused with persistence
2. Create final checkpoint
3. Save current progress and context
4. Enable resumption after restart
5. Update persistence status

Please execute the persistent execution pause workflow."""

        elif request.action == "complete":
            prompt = f"""Complete persistent execution.

Session ID: {request.session_id}
Context: {request.context or 'Execution completed'}

This tool will:
1. Mark execution as completed with persistence
2. Calculate total duration
3. Create final checkpoint
4. Archive execution data
5. Update persistence records

Please execute the persistent execution completion workflow."""

        elif request.action == "recovery_info":
            prompt = f"""Get crash recovery information.

This tool will:
1. Check for recent crash recovery events
2. Show recovery statistics
3. Display recovered executions
4. Provide recovery recommendations
5. Generate recovery report

Please execute the crash recovery information workflow."""

        elif request.action == "checkpoint":
            prompt = f"""Create execution checkpoint.

Force Checkpoint: {request.force_checkpoint}

This tool will:
1. Create immediate checkpoint of all executions
2. Save current state to persistent storage
3. Update checkpoint timestamps
4. Ensure crash recovery capability
5. Provide checkpoint confirmation

Please execute the checkpoint creation workflow."""

        else:
            prompt = f"""Unknown action: {request.action}

Available actions:
- status: Check persistent memory status
- start: Start persistent execution tracking
- update: Update persistent execution progress
- pause: Pause persistent execution
- complete: Complete persistent execution
- recovery_info: Get crash recovery information
- checkpoint: Create execution checkpoint

Please specify a valid action."""

        return prompt

    async def _call(self, request: PersistentMemoryRequest, **kwargs) -> Dict[str, Any]:
        """Execute the persistent memory management logic."""
        
        try:
            # Import the persistent memory manager
            import sys
            from pathlib import Path
            
            # Add the current directory to Python path
            current_dir = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(current_dir))
            
            from persistent_memory_manager import PersistentMemoryManager
            
            # Initialize manager with correct path
            # Use the same path as the test directory
            db_path = "/home/dingo/code/toolbox-workspace/tickets/open/ticket-011-cursor-vscode-exploration/persistent_todo_execution.db"
            manager = PersistentMemoryManager(db_path)
            
            # Execute based on action
            if request.action == "status":
                return await self._check_persistent_status(request, manager)
            elif request.action == "start":
                return await self._start_persistent_execution(request, manager)
            elif request.action == "update":
                return await self._update_persistent_execution(request, manager)
            elif request.action == "pause":
                return await self._pause_persistent_execution(request, manager)
            elif request.action == "complete":
                return await self._complete_persistent_execution(request, manager)
            elif request.action == "recovery_info":
                return await self._get_recovery_info(request, manager)
            elif request.action == "checkpoint":
                return await self._create_checkpoint(request, manager)
            elif request.action == "recovery_summary":
                return await self._get_recovery_summary(request, manager)
            elif request.action == "multi_window_todos":
                return await self._get_multi_window_todos(request, manager)
            else:
                return {"success": False, "error": f"Unknown action: {request.action}"}
                
        except Exception as e:
            return {"success": False, "error": f"Persistent memory error: {str(e)}"}

    async def _check_persistent_status(self, request: PersistentMemoryRequest, manager: PersistentMemoryManager) -> Dict[str, Any]:
        """Check persistent memory status"""
        
        executions = manager.get_persistent_executions()
        recovery_info = manager.get_crash_recovery_info()
        
        return {
            "success": True,
            "action": "status",
            "todo_id": request.todo_id,
            "active_executions": len(executions),
            "executions": [execution.__dict__ for execution in executions],
            "crash_recovery_info": recovery_info.__dict__ if recovery_info else None,
            "message": f"Found {len(executions)} persistent executions"
        }

    async def _start_persistent_execution(self, request: PersistentMemoryRequest, manager: PersistentMemoryManager) -> Dict[str, Any]:
        """Start persistent execution tracking"""
        
        if not all([request.todo_id, request.platform, request.agent, request.provider]):
            return {"success": False, "error": "Missing required fields: todo_id, platform, agent, provider"}
        
        session_id = manager.start_execution(
            request.todo_id,
            f"Persistent execution for {request.todo_id}",
            request.platform,
            request.agent,
            request.provider,
            request.context or "Starting persistent execution"
        )
        
        return {
            "success": True,
            "action": "start",
            "todo_id": request.todo_id,
            "session_id": session_id,
            "platform": request.platform,
            "agent": request.agent,
            "provider": request.provider,
            "message": f"Started persistent execution tracking for {request.todo_id}"
        }

    async def _update_persistent_execution(self, request: PersistentMemoryRequest, manager: PersistentMemoryManager) -> Dict[str, Any]:
        """Update persistent execution progress"""
        
        if not request.session_id:
            return {"success": False, "error": "session_id required for update action"}
        
        success = manager.update_execution(
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
                "message": f"Updated persistent execution {request.session_id}"
            }
        else:
            return {"success": False, "error": f"Could not find execution session: {request.session_id}"}

    async def _pause_persistent_execution(self, request: PersistentMemoryRequest, manager: PersistentMemoryManager) -> Dict[str, Any]:
        """Pause persistent execution"""
        
        if not request.session_id:
            return {"success": False, "error": "session_id required for pause action"}
        
        success = manager.pause_execution(request.session_id, request.context)
        
        if success:
            return {
                "success": True,
                "action": "pause",
                "session_id": request.session_id,
                "status": "paused",
                "message": f"Paused persistent execution {request.session_id}"
            }
        else:
            return {"success": False, "error": f"Could not find execution session: {request.session_id}"}

    async def _complete_persistent_execution(self, request: PersistentMemoryRequest, manager: PersistentMemoryManager) -> Dict[str, Any]:
        """Complete persistent execution"""
        
        if not request.session_id:
            return {"success": False, "error": "session_id required for complete action"}
        
        success = manager.complete_execution(request.session_id, request.context)
        
        if success:
            return {
                "success": True,
                "action": "complete",
                "session_id": request.session_id,
                "status": "completed",
                "message": f"Completed persistent execution {request.session_id}"
            }
        else:
            return {"success": False, "error": f"Could not find execution session: {request.session_id}"}

    async def _get_recovery_info(self, request: PersistentMemoryRequest, manager: PersistentMemoryManager) -> Dict[str, Any]:
        """Get crash recovery information"""
        
        recovery_info = manager.get_crash_recovery_info()
        
        if recovery_info:
            return {
                "success": True,
                "action": "recovery_info",
                "crash_recovery_info": recovery_info.__dict__,
                "message": "Crash recovery information retrieved"
            }
        else:
            return {
                "success": True,
                "action": "recovery_info",
                "crash_recovery_info": None,
                "message": "No crash recovery events found"
            }

    async def _create_checkpoint(self, request: PersistentMemoryRequest, manager: PersistentMemoryManager) -> Dict[str, Any]:
        """Create execution checkpoint"""
        
        # Force checkpoint if requested
        if request.force_checkpoint:
            manager._create_checkpoint()
        
        return {
            "success": True,
            "action": "checkpoint",
            "force_checkpoint": request.force_checkpoint,
            "message": f"Checkpoint {'forced' if request.force_checkpoint else 'scheduled'}"
        }

    async def _get_recovery_summary(self, request: PersistentMemoryRequest, manager: PersistentMemoryManager) -> Dict[str, Any]:
        """Get quick recovery summary with continuation options"""
        
        executions = manager.get_persistent_executions()
        # Convert PersistentExecution objects to dictionaries
        execution_dicts = []
        for exec in executions:
            exec_dict = {
                'session_id': exec.session_id,
                'status': exec.status,
                'platform': exec.platform,
                'agent': exec.agent,
                'provider': exec.provider,
                'progress_percent': exec.progress_percent,
                'current_action': exec.current_action,
                'started_at': exec.started_at,
                'last_activity': exec.last_activity,
                'todo_id': exec.todo_id,
                'todo_text': exec.todo_text,
                'context': exec.context
            }
            execution_dicts.append(exec_dict)
        
        active_executions = [e for e in execution_dicts if e.get('status') in ['executing', 'paused']]
        
        if not active_executions:
            return {
                "success": True,
                "action": "recovery_summary",
                "active_sessions": 0,
                "message": "No active sessions found. Ready to start new work.",
                "recommendations": [
                    "Start new work: /persistent-start --todo-id=new_task",
                    "Check completed work: /persistent-status --show-all"
                ]
            }
        
        # Sort by most recent
        active_executions.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
        primary_work = active_executions[0]
        
        # Calculate time estimates and complexity
        duration_hours = self._calculate_duration_hours(primary_work)
        estimated_remaining = self._estimate_remaining_time(primary_work)
        complexity = self._assess_complexity(primary_work)
        chain_recommended = estimated_remaining > 1.0 or complexity == 'high'
        
        continuation_commands = [
            f"/persistent-continue --session-id={primary_work.get('session_id')}",
            f"/persistent-update --session-id={primary_work.get('session_id')} --progress={primary_work.get('progress_percent', 0) + 5}",
            f"/persistent-pause --session-id={primary_work.get('session_id')} --context='Switching context'",
            "/persistent-start --todo-id=new_task"
        ]
        
        summary = {
            "success": True,
            "action": "recovery_summary",
            "active_sessions": len(active_executions),
            "primary_work": {
                "session_id": primary_work.get('session_id'),
                "platform": primary_work.get('platform'),
                "agent": primary_work.get('agent'),
                "provider": primary_work.get('provider'),
                "progress": primary_work.get('progress_percent', 0),
                "current_action": primary_work.get('current_action'),
                "duration_hours": duration_hours,
                "status": primary_work.get('status')
            },
            "assessment": {
                "estimated_remaining_hours": estimated_remaining,
                "complexity": complexity,
                "chain_recommended": chain_recommended
            },
            "continuation_commands": continuation_commands,
            "secondary_work": active_executions[1:] if len(active_executions) > 1 else []
        }
        
        return summary
    
    def _calculate_duration_hours(self, execution: Dict[str, Any]) -> float:
        """Calculate duration in hours"""
        start_time = execution.get('started_at')
        if not start_time:
            return 0.0
        
        try:
            from datetime import datetime
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            duration = datetime.now() - start_dt
            return duration.total_seconds() / 3600
        except:
            return 0.0
    
    def _estimate_remaining_time(self, execution: Dict[str, Any]) -> float:
        """Estimate remaining time based on progress"""
        progress = execution.get('progress_percent', 0)
        duration_hours = self._calculate_duration_hours(execution)
        
        if progress == 0:
            return 2.0  # Default estimate
        
        # Simple linear estimation
        if progress > 0:
            estimated_total = (duration_hours / progress) * 100
            return max(0.5, estimated_total - duration_hours)
        
        return 1.0
    
    def _assess_complexity(self, execution: Dict[str, Any]) -> str:
        """Assess task complexity"""
        current_action = execution.get('current_action', '').lower()
        
        if any(word in current_action for word in ['implement', 'architecture', 'core', 'system']):
            return 'high'
        elif any(word in current_action for word in ['test', 'debug', 'fix', 'update']):
            return 'medium'
        else:
            return 'low'
    
    async def _get_multi_window_todos(self, request: PersistentMemoryRequest, manager: PersistentMemoryManager) -> Dict[str, Any]:
        """Get multi-window todo management dashboard"""
        
        executions = manager.get_persistent_executions()
        # Convert PersistentExecution objects to dictionaries
        execution_dicts = []
        for exec in executions:
            exec_dict = {
                'session_id': exec.session_id,
                'status': exec.status,
                'platform': exec.platform,
                'agent': exec.agent,
                'provider': exec.provider,
                'progress_percent': exec.progress_percent,
                'current_action': exec.current_action,
                'started_at': exec.started_at,
                'last_activity': exec.last_activity,
                'todo_id': exec.todo_id,
                'todo_text': exec.todo_text,
                'context': exec.context
            }
            execution_dicts.append(exec_dict)
        
        # Auto-detect window ID if not provided
        window_id = request.window_id or self._detect_window_id()
        
        # Group executions by status
        active_executions = [e for e in execution_dicts if e.get('status') in ['executing', 'paused']]
        completed_executions = [e for e in execution_dicts if e.get('status') == 'completed']
        
        # Detect conflicts (same todo active in multiple windows)
        conflicts = self._detect_conflicts(active_executions)
        
        # Generate window-specific recommendations
        window_recommendations = self._generate_window_recommendations(active_executions, window_id)
        
        summary = {
            "success": True,
            "action": "multi_window_todos",
            "window_status": {
                "current_window": window_id,
                "total_windows": len(set(e.get('platform', 'unknown') for e in execution_dicts)),
                "active_windows": len(set(e.get('platform', 'unknown') for e in active_executions))
            },
            "todo_dashboard": {
                "active_todos": len(active_executions),
                "paused_todos": len([e for e in active_executions if e.get('status') == 'paused']),
                "completed_today": len(completed_executions)
            },
            "cross_window_status": active_executions,
            "conflicts": conflicts,
            "window_recommendations": window_recommendations,
            "sync_commands": [
                "/multi-window-todos --sync-all",
                "/persistent-status --show-all",
                "/quick-recovery"
            ]
        }
        
        return summary
    
    def _detect_window_id(self) -> str:
        """Auto-detect current window ID"""
        import os
        import time
        
        # Try to detect from environment variables or process info
        window_id = os.environ.get('WINDOW_ID')
        if not window_id:
            # Generate a unique window ID based on process and time
            window_id = f"window_{os.getpid()}_{int(time.time())}"
        
        return window_id
    
    def _detect_conflicts(self, executions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect todos that are active in multiple windows"""
        conflicts = []
        todo_windows = {}
        
        for exec in executions:
            todo_id = exec.get('todo_id')
            platform = exec.get('platform', 'unknown')
            
            if todo_id not in todo_windows:
                todo_windows[todo_id] = []
            todo_windows[todo_id].append(platform)
        
        for todo_id, windows in todo_windows.items():
            if len(windows) > 1:
                conflicts.append({
                    'todo_id': todo_id,
                    'windows': windows,
                    'resolution': f"Transfer to '{windows[0]}' window, pause in others"
                })
        
        return conflicts
    
    def _generate_window_recommendations(self, executions: List[Dict[str, Any]], window_id: str) -> Dict[str, List[str]]:
        """Generate window-specific recommendations"""
        recommendations = {}
        
        # Group executions by platform/window
        window_executions = {}
        for exec in executions:
            platform = exec.get('platform', 'unknown')
            if platform not in window_executions:
                window_executions[platform] = []
            window_executions[platform].append(exec)
        
        for platform, execs in window_executions.items():
            platform_recommendations = []
            
            for exec in execs:
                todo_id = exec.get('todo_id')
                progress = exec.get('progress_percent', 0)
                status = exec.get('status')
                
                if status == 'executing':
                    platform_recommendations.append(f"Continue {todo_id}: /todo-continue --todo-id={todo_id}")
                elif status == 'paused':
                    platform_recommendations.append(f"Resume {todo_id}: /todo-continue --todo-id={todo_id}")
            
            platform_recommendations.append(f"Start new todo: /todo-start --todo-id=new_feature")
            platform_recommendations.append(f"Sync with other windows: /multi-window-todos --sync-all")
            
            recommendations[platform] = platform_recommendations
        
        return recommendations
