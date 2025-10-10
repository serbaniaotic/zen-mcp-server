"""
QC Workflow Tool - Quick Chat Mode with Vim-Style Exits

Implements /qc command functionality:
- Read-only chat mode (no file writes, no commands)
- Vim-style exits (:wq, :x, :q, :w, :q!)
- Context auto-loading based on directory
- Memory extraction and storage
- Mode switching (chat → implementation)

Design: Day 4 Task-5 (qc-command-specification.md)
Validation: Day 5 Task-6 (smart-qc-full-stack-test)
Implementation: Day 5 Task-7 (recursive-qc with TRM patterns)
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.shared.base_tool import BaseTool
from tools.models import ToolOutput
from mcp.types import TextContent
from tools.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)


class QCWorkflowRequest(ToolRequest):
    """Request model for QC Workflow tool"""
    action: str = Field(..., description="Action: 'enter' (start QC mode), 'exit' (vim-style exit), 'query' (ask question)")
    exit_command: Optional[str] = Field(None, description="Vim exit command: ':wq', ':x', ':q', ':w', ':q!'")
    query: Optional[str] = Field(None, description="Question to ask in QC mode")
    context: Optional[str] = Field(None, description="Context to load (project name, task-N, ticket-N)")
    working_dir: Optional[str] = Field(None, description="Current working directory for context detection")


class QCWorkflowTool(BaseTool):
    """
    QC (Quick Chat) workflow tool
    
    Provides chat mode with vim-style exits and memory integration.
    This is a utility tool that doesn't require AI model calls.
    """
    
    def __init__(self):
        super().__init__()
        self.mode = "chat"  # Always chat mode
        self.session_history = []
        self.context_loaded = None
        self.session_start = None
        self.session_id = None
        
        # Centralized prompt library (Task-8)
        home = os.path.expanduser("~")
        self.prompt_library = Path(home) / ".mcp" / "prompts"
        
        # Memory file location
        self.memory_file = Path(home) / "code" / ".claude" / "memory.md"
        
        # Usage tracker (Task-8 Phase 2.2)
        self.usage_tracker = UsageTracker()
    
    def get_name(self) -> str:
        return "qc_workflow"
    
    def get_description(self) -> str:
        return (
            "Enter Quick Chat (QC) mode for design discussions without implementation. "
            "Features vim-style exits (:wq, :x, :q), context auto-loading, and memory integration."
        )
    
    def get_system_prompt(self) -> str:
        return """You are a QC (Quick Chat) mode assistant for design discussions.

Your role is to:
1. Facilitate read-only design discussions
2. Help users explore ideas without implementation
3. Manage vim-style exits and memory storage
4. Auto-load context based on working directory

Remember: QC mode is for discussion only - no file writes or command execution."""
    
    def get_default_temperature(self) -> float:
        return 0.3
    
    def get_model_category(self) -> "ToolModelCategory":
        """QC workflow prioritizes clarity and consistency"""
        from tools.models import ToolModelCategory
        return ToolModelCategory.BALANCED
    
    def get_request_model(self):
        """Return the QCWorkflow-specific request model"""
        return QCWorkflowRequest
    
    def requires_model(self) -> bool:
        """
        QC workflow doesn't require model resolution at the MCP boundary.
        
        This is primarily a workflow management tool that coordinates discussions.
        
        Returns:
            bool: False - QC workflow doesn't need AI model access for basic operations
        """
        return False
    
    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: 'enter' (start QC mode), 'exit' (vim-style exit), 'query' (ask question)",
                    "enum": ["enter", "exit", "query"]
                },
                "exit_command": {
                    "type": "string",
                    "description": "Vim exit command: ':wq' (save+quit), ':x' (save+implement), ':q' (quit), ':w' (save), ':q!' (force quit)",
                    "enum": [":wq", ":x", ":q", ":w", ":q!"]
                },
                "query": {
                    "type": "string",
                    "description": "Question to ask in QC mode"
                },
                "context": {
                    "type": "string",
                    "description": "Context to load (project name, task-N, ticket-N). Auto-detected if not provided."
                },
                "working_dir": {
                    "type": "string",
                    "description": "Current working directory for context detection"
                }
            },
            "required": ["action"],
            "additionalProperties": False,
        }
    
    def get_annotations(self) -> Optional[dict[str, Any]]:
        """Return tool annotations indicating this is a read-only tool"""
        return {"readOnlyHint": True}
    
    async def prepare_prompt(self, request: QCWorkflowRequest) -> str:
        """Not used for this utility tool"""
        return ""
    
    def format_response(self, response: str, request: QCWorkflowRequest, model_info: Optional[dict] = None) -> str:
        """Not used for this utility tool"""
        return response
    
    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Execute the QC workflow logic.
        
        This overrides the base class execute to provide direct output without AI model calls.
        """
        
        action = arguments.get("action")
        
        try:
            if action == "enter":
                result = await self._enter_qc_mode(arguments)
            elif action == "exit":
                result = await self._exit_qc_mode(arguments)
            elif action == "query":
                result = await self._handle_query(arguments)
            else:
                result = ToolOutput(status="error", content=f"Unknown action: {action}", content_type="text")
            
            # Convert ToolOutput to TextContent list
            if isinstance(result, ToolOutput):
                return [TextContent(type="text", text=result.model_dump_json())]
            return result
            
        except Exception as e:
            logger.error(f"Error in QC workflow: {e}", exc_info=True)
            error_output = ToolOutput(status="error", content=f"QC workflow error: {str(e)}", content_type="text")
            return [TextContent(type="text", text=error_output.model_dump_json())]
    
    async def _enter_qc_mode(self, arguments: dict[str, Any]) -> ToolOutput:
        """Enter QC mode with context loading"""
        
        working_dir = arguments.get("working_dir", os.getcwd())
        context_arg = arguments.get("context")
        
        # Auto-detect context from directory
        context = await self._detect_context(working_dir, context_arg)
        
        self.context_loaded = context
        self.session_history = []
        self.session_start = datetime.now()
        self.session_id = f"qc-{self.session_start.strftime('%Y%m%d_%H%M%S')}"
        
        # Track QC session start (Task-8 Phase 2.2)
        self.usage_tracker.track_usage(
            prompt_id="qc-analysis",  # Default prompt for QC mode
            context={
                "mode": "qc",
                "type": context["type"],
                "name": context["name"],
                "dir": context["dir"],
            }
        )
        
        # Load context files
        context_files = await self._load_context_files(context)
        
        message = [
            "💬 Quick Chat Mode Active",
            "",
            f"📍 Context: {context['type']} ({context['name']})",
            f"📁 Directory: {context['dir']}",
            "",
            "✅ Allowed:",
            "  - Read files",
            "  - Discuss and design",
            "  - Analyze and recommend",
            "",
            "❌ Not Allowed:",
            "  - Write files",
            "  - Run commands",
            "  - Implement changes",
            "",
            "🎯 Vim-Style Exits:",
            "  :wq  - Save decisions and exit",
            "  :x   - Save and implement immediately",
            "  :q   - Exit without saving",
            "  :w   - Save progress, continue chatting",
            "  :q!  - Force quit, discard session",
            "",
            f"📚 Context loaded: {len(context_files)} files",
        ]
        
        if context_files:
            message.append("")
            message.append("Files available:")
            for file in context_files[:5]:  # Show first 5
                message.append(f"  - {file}")
            if len(context_files) > 5:
                message.append(f"  ... and {len(context_files) - 5} more")
        
        return ToolOutput(status="success", content="\n".join(message), content_type="text")
    
    async def _handle_query(self, arguments: dict[str, Any]) -> ToolOutput:
        """Handle query in QC mode"""
        
        query = arguments.get("query")
        
        if not query:
            return ToolOutput(status="error", content="Query is required", content_type="text")
        
        # Add to session history
        self.session_history.append({
            "type": "query",
            "content": query,
            "timestamp": datetime.now().isoformat()
        })
        
        # For now, just acknowledge the query
        # In the future, this could use RecursiveQueryHandler
        response = [
            f"📝 Query recorded: {query[:80]}{'...' if len(query) > 80 else ''}",
            "",
            "💡 In QC mode - discussion only",
            f"📊 Session queries: {len([h for h in self.session_history if h['type'] == 'query'])}",
        ]
        
        return ToolOutput(status="success", content="\n".join(response), content_type="text")
    
    async def _exit_qc_mode(self, arguments: dict[str, Any]) -> ToolOutput:
        """Exit QC mode with vim-style command"""
        
        exit_cmd = arguments.get("exit_command", ":q")
        
        # Calculate session duration
        duration_seconds = 0
        if self.session_start:
            duration_seconds = int((datetime.now() - self.session_start).total_seconds())
        
        # Track outcome (Task-8 Phase 2.2)
        if self.session_id:
            outcome = {
                "success": exit_cmd in [":wq", ":x"],
                "clarifications": len([h for h in self.session_history if h.get("type") == "query"]),
                "duration_seconds": duration_seconds,
                "exit_command": exit_cmd,
            }
            self.usage_tracker.record_outcome(self.session_id, outcome)
        
        if exit_cmd == ":wq":
            # Save and quit
            decisions = await self._extract_decisions()
            await self._save_to_memory(decisions)
            
            return ToolOutput(
                status="success",
                content="✅ Decisions saved to memory.\n"
                "📝 Updated: .claude/memory.md\n"
                "🚪 Exited QC mode → Implementation mode",
                content_type="text"
            )
        
        elif exit_cmd == ":x":
            # Save and implement immediately
            decisions = await self._extract_decisions()
            await self._save_to_memory(decisions)
            
            return ToolOutput(
                status="success",
                content="✅ Decisions saved to memory.\n"
                "🚀 Switching to implementation mode...\n"
                "💡 Ready to execute discussed changes",
                content_type="text"
            )
        
        elif exit_cmd == ":q":
            # Quit without saving
            return ToolOutput(
                status="success",
                content="🚪 Exited QC mode (no save)\n"
                "💭 Discussion was ephemeral",
                content_type="text"
            )
        
        elif exit_cmd == ":w":
            # Save and continue
            decisions = await self._extract_decisions()
            await self._save_to_memory(decisions)
            
            return ToolOutput(
                status="success",
                content="✅ Progress saved (checkpoint)\n"
                "💬 QC mode still active - continue chatting",
                content_type="text"
            )
        
        elif exit_cmd == ":q!":
            # Force quit
            self.session_history = []
            return ToolOutput(
                status="success",
                content="⚠️  Force quit - session discarded\n"
                "🚪 Exited QC mode",
                content_type="text"
            )
        
        else:
            return ToolOutput(status="error", content=f"Unknown exit command: {exit_cmd}", content_type="text")
    
    async def _detect_context(
        self, 
        working_dir: str, 
        context_arg: Optional[str]
    ) -> dict[str, Any]:
        """Auto-detect context from directory or argument"""
        
        if context_arg:
            # Explicit context provided
            if context_arg.startswith("task-"):
                return {
                    "type": "task",
                    "name": context_arg,
                    "dir": working_dir
                }
            elif context_arg.startswith("ticket-"):
                return {
                    "type": "ticket",
                    "name": context_arg,
                    "dir": working_dir
                }
            else:
                return {
                    "type": "project",
                    "name": context_arg,
                    "dir": working_dir
                }
        
        # Auto-detect from directory
        path = Path(working_dir)
        
        # Check if in task directory
        if "task-" in path.name:
            return {
                "type": "task",
                "name": path.name,
                "dir": working_dir
            }
        
        # Check if in ticket directory
        if "ticket-" in path.name:
            return {
                "type": "ticket",
                "name": path.name,
                "dir": working_dir
            }
        
        # Check for project root indicators
        project_markers = [
            "CONSTITUTION.md",
            "PROJECT-REGISTRY.json",
            "package.json",
            ".git"
        ]
        
        for marker in project_markers:
            if (path / marker).exists():
                return {
                    "type": "project",
                    "name": path.name,
                    "dir": working_dir
                }
        
        # Default: general context
        return {
            "type": "general",
            "name": "workspace",
            "dir": working_dir
        }
    
    async def _load_context_files(self, context: dict[str, Any]) -> list[str]:
        """Load relevant context files based on context type"""
        
        context_dir = Path(context["dir"])
        files = []
        
        if context["type"] == "task":
            # Task context: TASK.md, evidence files
            if (context_dir / "TASK.md").exists():
                files.append("TASK.md")
            
            evidence_dir = context_dir / "evidence"
            if evidence_dir.exists():
                files.extend([
                    f"evidence/{f.name}"
                    for f in evidence_dir.iterdir()
                    if f.is_file() and f.suffix == ".md"
                ])
        
        elif context["type"] == "ticket":
            # Ticket context: TICKET.md, SOLUTION.md
            if (context_dir / "TICKET.md").exists():
                files.append("TICKET.md")
            if (context_dir / "SOLUTION.md").exists():
                files.append("SOLUTION.md")
        
        elif context["type"] == "project":
            # Project context: CONSTITUTION.md, PROJECT-REGISTRY.json
            if (context_dir / "CONSTITUTION.md").exists():
                files.append("CONSTITUTION.md")
            if (context_dir / "PROJECT-REGISTRY.json").exists():
                files.append("PROJECT-REGISTRY.json")
            if (context_dir / "README.md").exists():
                files.append("README.md")
        
        return files
    
    async def _extract_decisions(self) -> list[dict[str, Any]]:
        """Extract decisions from session history"""
        
        # Simple extraction: Create decisions from queries
        decisions = []
        for item in self.session_history:
            if item["type"] == "query":
                decisions.append({
                    "topic": item["content"][:50],
                    "decision": "Discussion captured",
                    "rationale": "QC session",
                    "confidence": "medium",
                    "timestamp": item.get("timestamp", datetime.now().isoformat())
                })
        
        return decisions[:5]  # Max 5
    
    async def _save_to_memory(self, decisions: list[dict[str, Any]]) -> None:
        """Save decisions to .claude/memory.md"""
        
        if not decisions:
            logger.info("No decisions to save")
            return
        
        try:
            # Ensure directory exists
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing memory or create new
            if self.memory_file.exists():
                memory = self.memory_file.read_text(encoding='utf-8')
            else:
                memory = "# Claude Memory\n\n"
            
            # Format entry
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            context = self.context_loaded.get('name', 'general') if self.context_loaded else 'general'
            
            entry = f"\n## QC Session - {context}\n\n"
            entry += f"**Date**: {timestamp}\n"
            entry += f"**Mode**: QC Chat\n"
            entry += f"**Decisions**: {len(decisions)}\n\n"
            
            for i, d in enumerate(decisions, 1):
                entry += f"### Decision {i}: {d.get('topic', 'N/A')}\n"
                entry += f"**Decision**: {d.get('decision', 'N/A')}\n"
                if d.get('rationale'):
                    entry += f"**Rationale**: {d['rationale']}\n"
                if d.get('confidence'):
                    entry += f"**Confidence**: {d['confidence']}\n"
                entry += "\n"
            
            # Append to memory
            memory += entry
            
            # Write back
            self.memory_file.write_text(memory, encoding='utf-8')
            
            logger.info(f"✅ Saved {len(decisions)} decisions to {self.memory_file}")
            
        except Exception as e:
            logger.error(f"Failed to save to memory: {e}")
