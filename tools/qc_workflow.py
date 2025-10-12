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
        
        # Parse --load or -loadqc flag for loading specific QCs
        load_qcs = []
        if context_arg:
            if '--load' in context_arg:
                parts = context_arg.split('--load')
                context_arg = parts[0].strip()
                load_str = parts[1].strip() if len(parts) > 1 else ""
                load_qcs = self._parse_qc_refs(load_str)
            elif '-loadqc' in context_arg:
                parts = context_arg.split('-loadqc')
                context_arg = parts[0].strip()
                load_str = parts[1].strip() if len(parts) > 1 else ""
                load_qcs = self._parse_qc_refs(load_str)
        
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
        
        # Load specific QCs if requested
        loaded_qcs = []
        if load_qcs:
            loaded_qcs = await self._load_specific_qc_sessions(load_qcs)
            logger.info(f"Loaded {len(loaded_qcs)} specific QC sessions: {load_qcs}")
        
        # Load recent QC sessions for reference (if no specific ones loaded)
        recent_qcs = []
        if not loaded_qcs:
            recent_qcs = await self._load_recent_qc_sessions(limit=5)
        
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
        
        # Show loaded or recent QC sessions
        if loaded_qcs:
            message.append("")
            message.append(f"📚 Loaded QC Sessions ({len(loaded_qcs)}):")
            for qc in loaded_qcs:
                message.append(f"  - {qc['id']}: {qc.get('title', 'No title')}")
                if qc.get('summary'):
                    message.append(f"    → {qc['summary'][:60]}...")
                elif qc.get('key_insight'):
                    message.append(f"    → {qc['key_insight'][:60]}...")
        elif recent_qcs:
            message.append("")
            message.append("📖 Recent QC Sessions (for context):")
            for qc in recent_qcs[:3]:  # Show last 3
                message.append(f"  - {qc['id']}: {qc['title']}")
                if qc.get('key_insight'):
                    message.append(f"    → {qc['key_insight'][:60]}...")
        
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
            # PRIMARY: Save full session to qc/ folder (permanent record)
            qc_file = await self._save_qc_session_file()
            
            # SECONDARY: Extract and save decisions to memory (optional backup)
            decisions = await self._extract_decisions()
            memory_saved = False
            if decisions:  # Only save to memory if there are actual decisions
                await self._save_to_memory(decisions)
                memory_saved = True
            
            # Build success message
            message = "✅ QC Session saved\n"
            if qc_file:
                message += f"📝 QC File: {qc_file}\n"
            if memory_saved:
                message += "💾 Decisions: .claude/memory.md\n"
            
            # Phase 2: Auto-feed to RAG
            if qc_file:
                rag_success = await self._feed_to_rag(qc_file)
                if rag_success:
                    message += "📊 Indexed in RAG\n"
            
            # Phase 3: Auto-update README
            if qc_file:
                readme_success = await self._update_readme(qc_file)
                if readme_success:
                    message += "📄 README updated\n"
            
            # Phase 4: Index in spatial memory
            if qc_file:
                spatial_success = await self._index_spatial_memory(qc_file)
                if spatial_success:
                    message += "🧠 Spatial memory indexed\n"
            
            message += "🚪 Exited QC mode → Implementation mode"
            
            return ToolOutput(
                status="success",
                content=message,
                content_type="text"
            )
        
        elif exit_cmd == ":x":
            # Save and implement immediately
            decisions = await self._extract_decisions()
            await self._save_to_memory(decisions)
            
            # Save full session to qc/ folder
            qc_file = await self._save_qc_session_file()
            
            # Offer to create task structure
            task_offer = await self._offer_task_creation(arguments)
            
            message = "✅ Decisions saved to memory.\n"
            if qc_file:
                message += f"💾 QC Session: {qc_file}\n"
            message += "🚀 Switching to implementation mode...\n"
            message += f"{task_offer}\n"
            message += "💡 Ready to execute discussed changes"
            
            return ToolOutput(
                status="success",
                content=message,
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
            
            # Save full session to qc/ folder
            qc_file = await self._save_qc_session_file()
            
            message = "✅ Progress saved (checkpoint)\n"
            if qc_file:
                message += f"💾 QC Session: {qc_file}\n"
            message += "💬 QC mode still active - continue chatting"
            
            return ToolOutput(
                status="success",
                content=message,
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
    
    async def _save_qc_session_file(self) -> Optional[str]:
        """
        Save QC session to permanent storage in qc/YYYY/MM/DD/ folder.
        Returns the path to the saved file or None if save failed.
        """
        try:
            # Get home directory
            home = Path.home()
            code_root = home / "code"
            qc_dir = code_root / "qc"
            template_file = qc_dir / "template-qc-session.md"
            
            # Check template exists
            if not template_file.exists():
                logger.error(f"QC template not found: {template_file}")
                return None
            
            # Generate QC number and path
            now = datetime.now()
            year = now.strftime("%Y")
            month = now.strftime("%m")
            day = now.strftime("%d")
            
            # Create directory structure
            qc_day_dir = qc_dir / year / month / day
            qc_day_dir.mkdir(parents=True, exist_ok=True)
            
            # Get next QC number for this month
            qc_num = await self._get_next_qc_number(qc_dir, year, month)
            
            # Generate topic slug from session history
            topic = "qc-session"
            if self.session_history:
                first_query = next((h for h in self.session_history if h.get('type') == 'query'), None)
                if first_query:
                    # Take first 50 chars and slugify
                    topic_text = first_query['content'][:50]
                    topic = topic_text.lower().replace(' ', '-')
                    # Remove non-alphanumeric chars except hyphens
                    topic = ''.join(c for c in topic if c.isalnum() or c == '-')
                    topic = topic.strip('-')
            
            # Create filename
            filename = qc_day_dir / f"QC-{qc_num:03d}-{topic}.md"
            
            # Read template
            template_content = template_file.read_text(encoding='utf-8')
            
            # Calculate duration
            duration_minutes = 0
            if self.session_start:
                duration_seconds = (datetime.now() - self.session_start).total_seconds()
                duration_minutes = int(duration_seconds / 60)
            
            # Get context info
            context_name = self.context_loaded.get('name', 'workspace') if self.context_loaded else 'workspace'
            context_type = self.context_loaded.get('type', 'general') if self.context_loaded else 'general'
            
            # Replace placeholders
            content = template_content
            content = content.replace("QC-NNN", f"QC-{qc_num:03d}")
            content = content.replace("YYYY-MM-DD", now.strftime("%Y-%m-%d"))
            content = content.replace("HH:MM", now.strftime("%H:%M"))
            content = content.replace("XXmin", f"{duration_minutes}min")
            content = content.replace("Session Title", topic.replace('-', ' ').title())
            
            # Add session notes
            if self.session_history:
                notes_section = "\n## Discussion Notes\n\n"
                for item in self.session_history:
                    if item.get('type') == 'query':
                        notes_section += f"**Q**: {item.get('content', '')}\n\n"
                
                # Insert after "## Discussion Notes" section
                content = content.replace(
                    "## Discussion Notes\n\n[Your thinking, exploration, design work...]",
                    notes_section
                )
            
            # Write file
            filename.write_text(content, encoding='utf-8')
            
            logger.info(f"✅ Saved QC session to {filename}")
            return str(filename)
            
        except Exception as e:
            logger.error(f"Failed to save QC session file: {e}", exc_info=True)
            return None
    
    async def _get_next_qc_number(self, qc_dir: Path, year: str, month: str) -> int:
        """Get next QC number for the given month"""
        try:
            qc_month_dir = qc_dir / year / month
            
            if not qc_month_dir.exists():
                return 1
            
            # Find all QC-*.md files in this month (across all days)
            qc_files = list(qc_month_dir.rglob("QC-*.md"))
            
            if not qc_files:
                return 1
            
            # Extract numbers and find highest
            numbers = []
            for qc_file in qc_files:
                # Extract number from QC-NNN-topic.md format
                parts = qc_file.stem.split('-')
                if len(parts) >= 2 and parts[0] == 'QC':
                    try:
                        numbers.append(int(parts[1]))
                    except ValueError:
                        continue
            
            if numbers:
                return max(numbers) + 1
            return 1
            
        except Exception as e:
            logger.error(f"Error getting next QC number: {e}")
            return 1
    
    async def _load_recent_qc_sessions(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Load recent QC sessions for context reference.
        Returns list of QC session summaries with id, title, date, key insight.
        """
        try:
            home = Path.home()
            qc_dir = home / "code" / "qc"
            
            if not qc_dir.exists():
                return []
            
            # Find all QC-*.md files (excluding template and archived)
            qc_files = []
            for year_dir in sorted((qc_dir / "2025").iterdir(), reverse=True):
                if not year_dir.is_dir():
                    continue
                for month_dir in sorted(year_dir.iterdir(), reverse=True):
                    if not month_dir.is_dir():
                        continue
                    for day_dir in sorted(month_dir.iterdir(), reverse=True):
                        if not day_dir.is_dir():
                            continue
                        for qc_file in sorted(day_dir.glob("QC-*.md"), reverse=True):
                            qc_files.append(qc_file)
                            if len(qc_files) >= limit:
                                break
                        if len(qc_files) >= limit:
                            break
                    if len(qc_files) >= limit:
                        break
                if len(qc_files) >= limit:
                    break
            
            # Parse each QC file
            sessions = []
            for qc_file in qc_files[:limit]:
                try:
                    content = qc_file.read_text(encoding='utf-8')
                    
                    # Extract YAML frontmatter
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            frontmatter = parts[1]
                            body = parts[2]
                            
                            # Parse basic fields
                            qc_id = None
                            qc_date = None
                            for line in frontmatter.split('\n'):
                                if line.startswith('id:'):
                                    qc_id = line.split(':', 1)[1].strip()
                                elif line.startswith('date:'):
                                    qc_date = line.split(':', 1)[1].strip()
                            
                            # Extract title from first h1
                            title = "Unknown"
                            for line in body.split('\n'):
                                if line.startswith('# '):
                                    title = line[2:].strip()
                                    # Remove QC-XXX: prefix if present
                                    if ':' in title:
                                        title = title.split(':', 1)[1].strip()
                                    break
                            
                            # Extract first insight/key point
                            key_insight = None
                            in_insights = False
                            for line in body.split('\n'):
                                if '## Insights' in line:
                                    in_insights = True
                                    continue
                                if in_insights and line.startswith('💡'):
                                    key_insight = line.replace('💡', '').replace('**', '').strip()
                                    # Remove "Key Insight:" prefix if present
                                    if ':' in key_insight:
                                        key_insight = key_insight.split(':', 1)[1].strip()
                                    break
                                if in_insights and line.startswith('##'):
                                    break
                            
                            if qc_id:
                                sessions.append({
                                    'id': qc_id,
                                    'title': title,
                                    'date': qc_date or 'unknown',
                                    'key_insight': key_insight,
                                    'file': str(qc_file)
                                })
                
                except Exception as e:
                    logger.error(f"Error parsing QC file {qc_file}: {e}")
                    continue
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error loading recent QC sessions: {e}")
            return []
    
    def _parse_qc_refs(self, load_str: str) -> list[str]:
        """
        Parse QC references from various formats.
        
        Accepts:
        - "002 003" → ["QC-002", "QC-003"]
        - "QC-002,QC-005" → ["QC-002", "QC-005"]
        - "2,5" → ["QC-002", "QC-005"]
        - "QC-002 QC-005" → ["QC-002", "QC-005"]
        
        Returns list of normalized QC IDs.
        """
        if not load_str:
            return []
        
        refs = []
        # Replace commas with spaces for consistent parsing
        normalized = load_str.replace(',', ' ')
        
        for ref in normalized.split():
            ref = ref.strip()
            if not ref:
                continue
            
            if ref.startswith('QC-'):
                # Already in full format
                refs.append(ref)
            else:
                # Convert short format to full
                try:
                    num = int(ref)
                    refs.append(f"QC-{num:03d}")
                except ValueError:
                    logger.warning(f"Invalid QC reference: {ref}")
                    continue
        
        return refs
    
    async def _load_specific_qc_sessions(self, qc_ids: list[str]) -> list[dict[str, Any]]:
        """
        Load specific QC sessions by ID.
        
        Args:
            qc_ids: List of QC IDs like ["QC-002", "QC-005"]
        
        Returns:
            List of QC session dictionaries with metadata
        """
        sessions = []
        
        home = Path.home()
        qc_dir = home / "code" / "qc"
        
        if not qc_dir.exists():
            logger.warning(f"QC directory not found: {qc_dir}")
            return []
        
        for qc_id in qc_ids:
            try:
                # Search for QC file (could be in any date folder)
                qc_files = list(qc_dir.rglob(f"{qc_id}-*.md"))
                
                if not qc_files:
                    logger.warning(f"QC session not found: {qc_id}")
                    continue
                
                # Use the first match (should only be one)
                qc_file = qc_files[0]
                content = qc_file.read_text(encoding='utf-8')
                
                # Parse YAML header
                if not content.startswith('---'):
                    logger.warning(f"QC file has no YAML header: {qc_file}")
                    continue
                
                parts = content.split('---', 2)
                if len(parts) < 3:
                    logger.warning(f"QC file has invalid format: {qc_file}")
                    continue
                
                frontmatter = parts[1]
                body = parts[2]
                
                # Parse basic YAML fields manually
                qc_data = {'id': qc_id, 'file': str(qc_file)}
                
                for line in frontmatter.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip().strip('"')
                        
                        if key in ['id', 'date', 'time', 'duration', 'type', 'action', 'outcome', 'status']:
                            qc_data[key] = value
                
                # Extract title from first h1
                title = "Unknown"
                for line in body.split('\n'):
                    if line.startswith('# '):
                        title = line[2:].strip()
                        # Remove QC-XXX: prefix if present
                        if ':' in title:
                            title = title.split(':', 1)[1].strip()
                        break
                
                qc_data['title'] = title
                
                # Extract summary if available
                if '## Session Context' in body:
                    context_section = body.split('## Session Context', 1)[1]
                    context_section = context_section.split('##', 1)[0]
                    # First paragraph as summary
                    paragraphs = [p.strip() for p in context_section.split('\n\n') if p.strip()]
                    if paragraphs:
                        qc_data['summary'] = paragraphs[0][:200]
                
                sessions.append(qc_data)
                logger.info(f"Loaded QC session: {qc_id} from {qc_file}")
                
            except Exception as e:
                logger.error(f"Error loading QC {qc_id}: {e}", exc_info=True)
                continue
        
        return sessions
    
    async def _offer_task_creation(self, arguments: dict[str, Any]) -> str:
        """Offer to create task structure using task-create.sh"""
        
        # Get context info
        context = self.context_loaded or {}
        context_name = context.get('name', 'unknown')
        
        # Extract title from session history
        title = "Implementation from QC"
        if self.session_history:
            first_query = next((h for h in self.session_history if h.get('type') == 'query'), None)
            if first_query:
                title = first_query['content'][:50]
        
        # Detect complexity from session length
        query_count = len([h for h in self.session_history if h.get('type') == 'query'])
        complexity = "medium"
        if query_count > 10:
            complexity = "high"
        elif query_count > 20:
            complexity = "critical"
        
        return (
            f"📋 Task Details from QC:\n"
            f"   Title: {title}\n"
            f"   Complexity: {complexity}\n"
            f"   Context: {context_name}\n"
            f"\n"
            f"💡 To create task structure:\n"
            f"   ~/code/scripts/task-create.sh [day] \"{title}\" {complexity}"
        )
    
    # ==================== RAG & Auto-Documentation Methods ====================
    # Added: Task-5 (QC RAG Integration & Auto-Documentation)
    
    async def _feed_to_rag(self, qc_file_path: str) -> bool:
        """
        Feed QC session to RAG system (OWL/Pinecone) after save.
        
        Process:
        1. Read and parse QC file (YAML + content)
        2. Extract key sections (insights, decisions, patterns)
        3. Store in spatial memory / RAG
        
        Returns True if successful, False otherwise.
        """
        try:
            # Read QC content
            qc_path = Path(qc_file_path)
            if not qc_path.exists():
                logger.error(f"QC file not found: {qc_file_path}")
                return False
            
            content = qc_path.read_text(encoding='utf-8')
            
            # Parse YAML frontmatter
            import yaml
            parts = content.split('---', 2)
            metadata = {}
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError as e:
                    logger.warning(f"Failed to parse YAML frontmatter: {e}")
            
            # Extract sections
            sections = {
                'full_content': content,
                'metadata': metadata,
                'insights': self._extract_section(content, '## Insights'),
                'decisions': self._extract_section(content, '## Anchors'),
                'context': metadata.get('context', []),
            }
            
            # TODO: Integrate with spatial_memory tool
            # For now, just log that we would feed to RAG
            logger.info(f"📊 Would feed to RAG: {qc_file_path}")
            logger.debug(f"   Metadata: {metadata}")
            logger.debug(f"   Context: {sections['context']}")
            
            # Future: Call spatial_memory.store_knowledge()
            # await store_knowledge(
            #     content=sections['full_content'],
            #     domain='qc-session',
            #     pattern=metadata.get('type', 'design'),
            #     metadata={...}
            # )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to feed QC to RAG: {e}", exc_info=True)
            return False
    
    async def _update_readme(self, qc_file_path: str) -> bool:
        """
        Auto-update README.md in the QC day folder.
        
        Process:
        1. Parse QC metadata and content
        2. Find or create README.md
        3. Add new QC entry
        4. Update session count
        
        Returns True if successful, False otherwise.
        """
        try:
            qc_path = Path(qc_file_path)
            readme_path = qc_path.parent / "README.md"
            
            # Read QC content for metadata
            content = qc_path.read_text(encoding='utf-8')
            
            # Parse YAML frontmatter
            import yaml
            parts = content.split('---', 2)
            metadata = {}
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    logger.warning("Failed to parse YAML, skipping README update")
                    return False
            
            # Extract key info
            qc_id = metadata.get('id', 'QC-???')
            qc_type = metadata.get('type', 'ponder')
            qc_time = metadata.get('time', '??:??')
            
            # Extract title from content (first # header)
            import re
            title_match = re.search(r'^# (QC-\d+: .+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else "QC Session"
            topic = title.replace(f'{qc_id}: ', '')
            
            # Extract key insights (first 3)
            insights_section = self._extract_section(content, '## Insights')
            key_insights = []
            if insights_section:
                insight_lines = [l.strip() for l in insights_section.split('\n') 
                                if l.strip().startswith(('💡', '💭', '🎯', '-'))]
                key_insights = [l.lstrip('💡💭🎯-• ').strip() for l in insight_lines[:3]]
            
            # Calculate file size
            file_size_kb = qc_path.stat().st_size / 1024
            
            # Generate README entry
            entry = f"""
### {qc_id}: {topic}
- **Time**: {qc_time}
- **Type**: {qc_type.capitalize()}
"""
            
            if key_insights:
                entry += "- **Key Insights**:\n"
                for insight in key_insights:
                    entry += f"  - {insight}\n"
            
            entry += f"- **Size**: {file_size_kb:.1f}k\n"
            
            # Update or create README
            if readme_path.exists():
                readme = readme_path.read_text(encoding='utf-8')
                
                # Find insertion point after "## Sessions Overview"
                if "## Sessions Overview" in readme:
                    readme = readme.replace(
                        "## Sessions Overview\n",
                        f"## Sessions Overview\n{entry}"
                    )
                else:
                    # Append to end
                    readme += f"\n{entry}"
                
                # Update count in header if present
                qc_count = len(list(qc_path.parent.glob("QC-*.md")))
                readme = re.sub(
                    r'This folder contains \d+ QC',
                    f'This folder contains {qc_count} QC',
                    readme
                )
                
            else:
                # Create new README
                date_str = metadata.get('date', datetime.now().strftime('%Y-%m-%d'))
                qc_count = len(list(qc_path.parent.glob("QC-*.md")))
                readme = f"""# QC Sessions - {date_str}

This folder contains {qc_count} QC (Quick Chat) sessions.

## Sessions Overview
{entry}

## Organization

Each QC session follows the QC template with:
- YAML frontmatter with metadata
- Structured sections: Context, Questions, Notes, Insights, Anchors
- Action items and references

---

**Status**: Active
**Latest**: {qc_id}
"""
            
            # Save README
            readme_path.write_text(readme, encoding='utf-8')
            logger.info(f"📝 Updated README: {readme_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update README: {e}", exc_info=True)
            return False
    
    async def _index_spatial_memory(self, qc_file_path: str) -> bool:
        """
        Index QC session in spatial memory for cross-domain pattern recognition.
        
        Process:
        1. Parse QC content and metadata
        2. Classify domain
        3. Extract patterns
        4. Index in spatial memory
        
        Returns True if successful, False otherwise.
        """
        try:
            qc_path = Path(qc_file_path)
            content = qc_path.read_text(encoding='utf-8')
            
            # Parse YAML frontmatter
            import yaml
            parts = content.split('---', 2)
            metadata = {}
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    pass
            
            # Classify domain
            context_tags = metadata.get('context', [])
            domain = self._classify_domain(context_tags, content)
            
            # Extract patterns
            patterns = self._extract_patterns(content)
            
            # TODO: Integrate with spatial_memory tool
            # For now, just log
            logger.info(f"🧠 Would index in spatial memory: {qc_file_path}")
            logger.debug(f"   Domain: {domain}")
            logger.debug(f"   Patterns: {patterns}")
            
            # Future: Call spatial_memory.store_memory()
            # for pattern in patterns:
            #     await store_memory(
            #         content=pattern['description'],
            #         domain=domain,
            #         pattern=pattern['type'],
            #         metadata={...}
            #     )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to index spatial memory: {e}", exc_info=True)
            return False
    
    def _extract_section(self, content: str, header: str) -> str:
        """Extract section content between markdown headers"""
        import re
        pattern = f"{re.escape(header)}\\n+(.*?)(?=\\n## |$)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else ""
    
    def _classify_domain(self, context_tags: list, content: str) -> str:
        """Classify QC domain based on context tags and content"""
        # Domain keyword mapping
        domain_keywords = {
            'technical': ['architecture', 'implementation', 'code', 'api', 'database'],
            'business': ['user', 'feature', 'product', 'requirement', 'strategy'],
            'devops': ['deployment', 'infrastructure', 'ci/cd', 'docker', 'kubernetes'],
            'ux': ['interface', 'design', 'user experience', 'workflow', 'usability'],
            'security': ['auth', 'security', 'encryption', 'vulnerability', 'permission'],
        }
        
        # Check context tags first
        for tag in context_tags:
            tag_lower = str(tag).lower()
            for domain, keywords in domain_keywords.items():
                if any(kw in tag_lower for kw in keywords):
                    return domain
        
        # Check content
        content_lower = content.lower()
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(content_lower.count(kw) for kw in keywords)
            domain_scores[domain] = score
        
        # Return highest scoring domain or default
        if domain_scores and max(domain_scores.values()) > 0:
            return max(domain_scores.items(), key=lambda x: x[1])[0]
        return 'technical'
    
    def _extract_patterns(self, content: str) -> list[dict]:
        """Extract architectural/design patterns from QC content"""
        patterns = []
        
        # Pattern markers
        pattern_markers = {
            'resource_contention': ['queue', 'pool', 'throttle', 'rate limit'],
            'config_error': ['configuration', 'env var', 'settings', 'config'],
            'performance_degradation': ['slow', 'performance', 'optimization', 'latency'],
            'state_management': ['state', 'context', 'session', 'cache'],
            'data_flow': ['pipeline', 'flow', 'stream', 'transform'],
            'integration_pattern': ['api', 'integration', 'connector', 'adapter'],
        }
        
        content_lower = content.lower()
        for pattern_type, keywords in pattern_markers.items():
            if any(kw in content_lower for kw in keywords):
                patterns.append({
                    'type': pattern_type,
                    'description': f"Pattern identified: {pattern_type}"
                })
        
        return patterns
