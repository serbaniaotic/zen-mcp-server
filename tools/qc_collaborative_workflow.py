"""
QC Collaborative Workflow Tool - Collaborative Quick Chat Mode

Implements /qc-collab command functionality:
- Read-only collaborative chat mode (no file writes, no commands)
- Identity-aware session management (participant tracking)
- Separate storage namespace (qc-collab/) to prevent RAG pollution
- Vim-style exits (:wq, :x, :q, :w, :q!)
- Context auto-loading based on directory
- RAG isolation safeguards for demo and collaborative sessions
- Mode switching (chat → implementation)

Design Philosophy:
- Keep collaborative sessions completely separate from personal QC learning
- Prevent identity confusion in RAG/spatial memory systems
- Enable safe demos and friend assistance without polluting dingo's AI patterns
- Maintain same UX as personal QC but with identity safeguards

Storage Location: qc-collab/YYYY/MM/DD/QC-COLLAB-NNN-topic.md
RAG Policy: READ-ONLY mode - no learning/vocabulary updates
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


class QCCollaborativeWorkflowRequest(ToolRequest):
    """Request model for QC Collaborative Workflow tool"""
    action: str = Field(..., description="Action: 'enter' (start collab QC), 'exit' (vim-style exit), 'query' (ask question)")
    exit_command: Optional[str] = Field(None, description="Vim exit command: ':wq', ':x', ':q', ':w', ':q!'")
    query: Optional[str] = Field(None, description="Question to ask in collaborative QC mode")
    context: Optional[str] = Field(None, description="Context to load (project name, task-N, ticket-N)")
    working_dir: Optional[str] = Field(None, description="Current working directory for context detection")
    participant: Optional[str] = Field(None, description="Name/identifier of collaborating participant (friend, demo guest, etc.)")


class QCCollaborativeWorkflowTool(BaseTool):
    """
    QC (Quick Chat) collaborative workflow tool
    
    Provides safe collaborative chat mode with identity isolation and RAG pollution prevention.
    This is a utility tool that doesn't require AI model calls but maintains session integrity.
    """
    
    def __init__(self):
        super().__init__()
        self.mode = "collaborative-chat"
        self.session_history = []
        self.context_loaded = None
        self.session_start = None
        self.session_id = None
        self.participant = None
        
        # Centralized prompt library (Task-8)
        home = os.path.expanduser("~")
        self.prompt_library = Path(home) / ".mcp" / "prompts"
        
        # Collaborative memory file location (separate from personal)
        self.memory_file = Path(home) / "code" / ".claude" / "collab-memory.md"
        
        # Usage tracker (Task-8 Phase 2.2)
        self.usage_tracker = UsageTracker()
    
    def get_name(self) -> str:
        return "qc_collaborative_workflow"
    
    def get_description(self) -> str:
        return (
            "Collaborative Quick Chat (QC) mode for working with friends, demos, and teaching. "
            "Features identity isolation, separate storage namespace, RAG pollution prevention, "
            "and vim-style exits (:wq, :x, :q). Safe for collaborative work without affecting personal AI learning."
        )
    
    def get_system_prompt(self) -> str:
        return """You are a QC (Quick Chat) collaborative mode assistant for safe multi-person design discussions.

Your role is to:
1. Facilitate read-only collaborative design discussions
2. Help multiple participants explore ideas without implementation
3. Manage vim-style exits and collaborative memory storage
4. Auto-load context based on working directory
5. Maintain identity separation and prevent RAG pollution
6. Track participants and collaboration context

IMPORTANT SAFEGUARDS:
- This is collaborative mode - sessions are stored separately from personal QC
- RAG system operates in READ-ONLY mode - no learning/vocabulary updates
- Identity tracking prevents confusion between dingo and collaborators
- Sessions tagged as collaborative to prevent personal AI pattern pollution

Remember: Collaborative QC mode is for discussion only - no file writes or command execution."""
    
    def get_default_temperature(self) -> float:
        return 0.3
    
    def get_model_category(self) -> "ToolModelCategory":
        """QC collaborative workflow prioritizes clarity and safety"""
        from tools.models import ToolModelCategory
        return ToolModelCategory.BALANCED
    
    def get_request_model(self):
        """Return the QC Collaborative Workflow-specific request model"""
        return QCCollaborativeWorkflowRequest
    
    def requires_model(self) -> bool:
        """
        QC collaborative workflow doesn't require model resolution at the MCP boundary.
        
        This is primarily a workflow management tool that coordinates collaborative discussions.
        
        Returns:
            bool: False - QC collaborative workflow doesn't need AI model access for basic operations
        """
        return False
    
    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action: 'enter' (start collab QC), 'exit' (vim-style exit), 'query' (ask question)",
                    "enum": ["enter", "exit", "query"]
                },
                "exit_command": {
                    "type": "string",
                    "description": "Vim exit command: ':wq' (save+quit), ':x' (save+implement), ':q' (quit), ':w' (save), ':q!' (force quit)",
                    "enum": [":wq", ":x", ":q", ":w", ":q!"]
                },
                "query": {
                    "type": "string",
                    "description": "Question to ask in collaborative QC mode"
                },
                "context": {
                    "type": "string",
                    "description": "Context to load (project name, task-N, ticket-N). Auto-detected if not provided."
                },
                "working_dir": {
                    "type": "string",
                    "description": "Current working directory for context detection"
                },
                "participant": {
                    "type": "string",
                    "description": "Name/identifier of collaborating participant (friend name, 'demo-guest', etc.)"
                }
            },
            "required": ["action"],
            "additionalProperties": False,
        }
    
    def get_annotations(self) -> Optional[dict[str, Any]]:
        """Return tool annotations indicating this is a read-only collaborative tool"""
        return {
            "readOnlyHint": True,
            "collaborativeMode": True,
            "ragIsolated": True
        }
    
    async def prepare_prompt(self, request: QCCollaborativeWorkflowRequest) -> str:
        """Not used for this utility tool"""
        return ""
    
    def format_response(self, response: str, request: QCCollaborativeWorkflowRequest, model_info: Optional[dict] = None) -> str:
        """Not used for this utility tool"""
        return response
    
    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Execute the QC collaborative workflow logic.
        
        This overrides the base class execute to provide direct output without AI model calls.
        """
        
        action = arguments.get("action")
        
        try:
            if action == "enter":
                result = await self._enter_collaborative_qc_mode(arguments)
            elif action == "exit":
                result = await self._exit_collaborative_qc_mode(arguments)
            elif action == "query":
                result = await self._handle_collaborative_query(arguments)
            else:
                result = ToolOutput(status="error", content=f"Unknown action: {action}", content_type="text")
            
            # Convert ToolOutput to TextContent list
            if isinstance(result, ToolOutput):
                return [TextContent(type="text", text=result.model_dump_json())]
            return result
            
        except Exception as e:
            logger.error(f"Error in QC collaborative workflow: {e}", exc_info=True)
            error_output = ToolOutput(status="error", content=f"QC collaborative workflow error: {str(e)}", content_type="text")
            return [TextContent(type="text", text=error_output.model_dump_json())]
    
    async def _enter_collaborative_qc_mode(self, arguments: dict[str, Any]) -> ToolOutput:
        """Enter collaborative QC mode with context loading and identity tracking"""
        
        working_dir = arguments.get("working_dir", os.getcwd())
        context_arg = arguments.get("context")
        participant = arguments.get("participant", "guest-participant")
        
        # Parse --load or -loadqc flag for loading specific QCs (collaborative ones only)
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
        self.participant = participant
        self.session_history = []
        self.session_start = datetime.now()
        self.session_id = f"qc-collab-{self.session_start.strftime('%Y%m%d_%H%M%S')}-{participant}"
        
        # Track collaborative QC session start (Task-8 Phase 2.2)
        self.usage_tracker.track_usage(
            prompt_id="qc-collaborative-analysis",
            context={
                "mode": "qc-collaborative",
                "type": context["type"],
                "name": context["name"],
                "dir": context["dir"],
                "participant": participant,
                "primary_user": "dingo",
            }
        )
        
        # Load context files
        context_files = await self._load_context_files(context)
        
        # Load specific collaborative QCs if requested
        loaded_qcs = []
        if load_qcs:
            loaded_qcs = await self._load_specific_collaborative_qc_sessions(load_qcs)
            logger.info(f"Loaded {len(loaded_qcs)} collaborative QC sessions: {load_qcs}")
        
        # Load recent collaborative QC sessions for reference (if no specific ones loaded)
        recent_qcs = []
        if not loaded_qcs:
            recent_qcs = await self._load_recent_collaborative_qc_sessions(limit=3)
        
        message = [
            "🤝 Collaborative Quick Chat Mode Active",
            "",
            f"👥 Participants: dingo (owner), {participant} (collaborator)",
            f"📍 Context: {context['type']} ({context['name']})",
            f"📁 Directory: {context['dir']}",
            "",
            "🔒 Identity Safeguards:",
            "  - Separate storage namespace (qc-collab/)",
            "  - RAG system in READ-ONLY mode",
            "  - No personal AI pattern updates",
            "  - Collaborative sessions isolated",
            "",
            "✅ Allowed:",
            "  - Read files",
            "  - Discuss and design",
            "  - Analyze and recommend",
            "  - Safe collaborative exploration",
            "",
            "❌ Not Allowed:",
            "  - Write files",
            "  - Run commands",
            "  - Implement changes",
            "  - Update personal AI learning",
            "",
            "🎯 Vim-Style Exits:",
            "  :wq  - Save collaborative decisions and exit",
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
        
        # Show loaded or recent collaborative QC sessions
        if loaded_qcs:
            message.append("")
            message.append(f"📚 Loaded Collaborative QC Sessions ({len(loaded_qcs)}):")
            for qc in loaded_qcs:
                message.append(f"  - {qc['id']}: {qc.get('title', 'No title')}")
                if qc.get('summary'):
                    message.append(f"    → {qc['summary'][:60]}...")
                elif qc.get('key_insight'):
                    message.append(f"    → {qc['key_insight'][:60]}...")
        elif recent_qcs:
            message.append("")
            message.append("📖 Recent Collaborative Sessions (for context):")
            for qc in recent_qcs[:3]:  # Show last 3
                message.append(f"  - {qc['id']}: {qc['title']}")
                if qc.get('key_insight'):
                    message.append(f"    → {qc['key_insight'][:60]}...")
        
        message.append("")
        message.append("⚠️  RAG Isolation: This session won't affect dingo's personal AI learning")
        
        return ToolOutput(status="success", content="\n".join(message), content_type="text")
    
    async def _handle_collaborative_query(self, arguments: dict[str, Any]) -> ToolOutput:
        """Handle query in collaborative QC mode"""
        
        query = arguments.get("query")
        
        if not query:
            return ToolOutput(status="error", content="Query is required", content_type="text")
        
        # Add to session history with participant tracking
        self.session_history.append({
            "type": "query",
            "content": query,
            "participant": self.participant or "guest",
            "timestamp": datetime.now().isoformat()
        })
        
        # For now, just acknowledge the query
        response = [
            f"📝 Query recorded: {query[:80]}{'...' if len(query) > 80 else ''}",
            f"👤 From: {self.participant or 'guest'}",
            "",
            "💡 In collaborative QC mode - discussion only",
            "🔒 RAG isolation active - no personal learning updates",
            f"📊 Session queries: {len([h for h in self.session_history if h['type'] == 'query'])}",
        ]
        
        return ToolOutput(status="success", content="\n".join(response), content_type="text")
    
    async def _exit_collaborative_qc_mode(self, arguments: dict[str, Any]) -> ToolOutput:
        """Exit collaborative QC mode with vim-style command"""
        
        exit_cmd = arguments.get("exit_command", ":q")
        
        # Calculate session duration
        duration_seconds = 0
        if self.session_start:
            duration_seconds = int((datetime.now() - self.session_start).total_seconds())
        
        # Track outcome (Task-8 Phase 2.2) - mark as collaborative
        if self.session_id:
            outcome = {
                "success": exit_cmd in [":wq", ":x"],
                "clarifications": len([h for h in self.session_history if h.get("type") == "query"]),
                "duration_seconds": duration_seconds,
                "exit_command": exit_cmd,
                "mode": "collaborative",
                "participant": self.participant,
                "rag_isolated": True,
            }
            self.usage_tracker.record_outcome(self.session_id, outcome)
        
        if exit_cmd == ":wq":
            # Save collaborative session (separate namespace)
            qc_file = await self._save_collaborative_qc_session_file()
            
            # Extract and save decisions to collaborative memory (separate from personal)
            decisions = await self._extract_collaborative_decisions()
            memory_saved = False
            if decisions:
                await self._save_to_collaborative_memory(decisions)
                memory_saved = True
            
            # Build success message
            message = "✅ Collaborative QC Session saved\n"
            if qc_file:
                message += f"📝 Collab QC File: {qc_file}\n"
            if memory_saved:
                message += "💾 Collaborative decisions: .claude/collab-memory.md\n"
            
            # Note: NO RAG feeding or spatial memory indexing for collaborative sessions
            message += "🔒 RAG isolation maintained - no personal learning updates\n"
            message += "🚪 Exited collaborative QC mode → Implementation mode"
            
            return ToolOutput(
                status="success",
                content=message,
                content_type="text"
            )
        
        elif exit_cmd == ":x":
            # Save and implement immediately
            decisions = await self._extract_collaborative_decisions()
            await self._save_to_collaborative_memory(decisions)
            
            # Save full collaborative session 
            qc_file = await self._save_collaborative_qc_session_file()
            
            # Offer to create task structure
            task_offer = await self._offer_collaborative_task_creation(arguments)
            
            message = "✅ Collaborative decisions saved.\n"
            if qc_file:
                message += f"💾 Collab QC Session: {qc_file}\n"
            message += "🔒 RAG isolation maintained\n"
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
                content="🚪 Exited collaborative QC mode (no save)\n"
                "💭 Collaborative discussion was ephemeral\n"
                "🔒 No impact on personal AI learning",
                content_type="text"
            )
        
        elif exit_cmd == ":w":
            # Save and continue
            decisions = await self._extract_collaborative_decisions()
            await self._save_to_collaborative_memory(decisions)
            
            # Save full collaborative session
            qc_file = await self._save_collaborative_qc_session_file()
            
            message = "✅ Collaborative progress saved (checkpoint)\n"
            if qc_file:
                message += f"💾 Collab QC Session: {qc_file}\n"
            message += "🔒 RAG isolation maintained\n"
            message += "💬 Collaborative QC mode still active - continue chatting"
            
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
                content="⚠️  Force quit - collaborative session discarded\n"
                "🚪 Exited collaborative QC mode\n"
                "🔒 No impact on personal AI learning",
                content_type="text"
            )
        
        else:
            return ToolOutput(status="error", content=f"Unknown exit command: {exit_cmd}", content_type="text")
    
    # ==================== Context Detection & File Loading ====================
    # (Reuse existing methods from personal QC workflow)
    
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
            "name": "collaborative-workspace",
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
    
    # ==================== Collaborative Decision Management ====================
    
    async def _extract_collaborative_decisions(self) -> list[dict[str, Any]]:
        """Extract decisions from collaborative session history"""
        
        decisions = []
        for item in self.session_history:
            if item["type"] == "query":
                decisions.append({
                    "topic": item["content"][:50],
                    "decision": "Collaborative discussion captured",
                    "rationale": f"Collaborative QC session with {item.get('participant', 'guest')}",
                    "confidence": "medium",
                    "participant": item.get('participant', 'guest'),
                    "mode": "collaborative",
                    "timestamp": item.get("timestamp", datetime.now().isoformat())
                })
        
        return decisions[:5]  # Max 5
    
    async def _save_to_collaborative_memory(self, decisions: list[dict[str, Any]]) -> None:
        """Save collaborative decisions to separate memory file"""
        
        if not decisions:
            logger.info("No collaborative decisions to save")
            return
        
        try:
            # Ensure directory exists
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing collaborative memory or create new
            if self.memory_file.exists():
                memory = self.memory_file.read_text(encoding='utf-8')
            else:
                memory = """# Claude Collaborative Memory

This file contains collaborative QC session decisions and is separate from personal memory.
These sessions involve dingo working with friends, demos, or teaching scenarios.
RAG system operates in READ-ONLY mode for these sessions to prevent personal AI learning pollution.

"""
            
            # Format entry
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            context = self.context_loaded.get('name', 'general') if self.context_loaded else 'general'
            participant = self.participant or 'guest'
            
            entry = f"\n## Collaborative QC Session - {context}\n\n"
            entry += f"**Date**: {timestamp}\n"
            entry += f"**Mode**: Collaborative QC Chat\n"
            entry += f"**Primary User**: dingo\n"
            entry += f"**Participant**: {participant}\n"
            entry += f"**RAG Mode**: READ-ONLY (isolated)\n"
            entry += f"**Decisions**: {len(decisions)}\n\n"
            
            for i, d in enumerate(decisions, 1):
                entry += f"### Decision {i}: {d.get('topic', 'N/A')}\n"
                entry += f"**Decision**: {d.get('decision', 'N/A')}\n"
                if d.get('rationale'):
                    entry += f"**Rationale**: {d['rationale']}\n"
                if d.get('confidence'):
                    entry += f"**Confidence**: {d['confidence']}\n"
                if d.get('participant'):
                    entry += f"**Contributor**: {d['participant']}\n"
                entry += "\n"
            
            # Append to memory
            memory += entry
            
            # Write back
            self.memory_file.write_text(memory, encoding='utf-8')
            
            logger.info(f"✅ Saved {len(decisions)} collaborative decisions to {self.memory_file}")
            
        except Exception as e:
            logger.error(f"Failed to save collaborative memory: {e}")
    
    # ==================== Collaborative Storage Methods ====================
    
    async def _save_collaborative_qc_session_file(self) -> Optional[str]:
        """
        Save collaborative QC session to separate storage in qc-collab/YYYY/MM/DD/ folder.
        Returns the path to the saved file or None if save failed.
        """
        try:
            # Get home directory
            home = Path.home()
            code_root = home / "code"
            qc_collab_dir = code_root / "qc-collab"
            template_file = code_root / "qc" / "template-qc-session.md"
            
            # Check template exists
            if not template_file.exists():
                logger.error(f"QC template not found: {template_file}")
                return None
            
            # Generate QC number and path
            now = datetime.now()
            year = now.strftime("%Y")
            month = now.strftime("%m")
            day = now.strftime("%d")
            
            # Create collaborative directory structure
            qc_day_dir = qc_collab_dir / year / month / day
            qc_day_dir.mkdir(parents=True, exist_ok=True)
            
            # Get next collaborative QC number for this month
            qc_num = await self._get_next_collaborative_qc_number(qc_collab_dir, year, month)
            
            # Generate topic slug from session history
            topic = "collaborative-qc"
            if self.session_history:
                first_query = next((h for h in self.session_history if h.get('type') == 'query'), None)
                if first_query:
                    topic_text = first_query['content'][:50]
                    topic = topic_text.lower().replace(' ', '-')
                    topic = ''.join(c for c in topic if c.isalnum() or c == '-')
                    topic = topic.strip('-')
            
            # Create filename with collaborative prefix
            filename = qc_day_dir / f"QC-COLLAB-{qc_num:03d}-{topic}.md"
            
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
            
            # Replace placeholders with collaborative-specific info
            content = template_content
            content = content.replace("QC-NNN", f"QC-COLLAB-{qc_num:03d}")
            content = content.replace("YYYY-MM-DD", now.strftime("%Y-%m-%d"))
            content = content.replace("HH:MM", now.strftime("%H:%M"))
            content = content.replace("XXmin", f"{duration_minutes}min")
            content = content.replace("Session Title", f"Collaborative: {topic.replace('-', ' ').title()}")
            
            # Add collaborative-specific YAML fields
            participant_yaml = f"""mode: collaborative
primary_user: dingo
participant: {self.participant or 'guest'}
rag_mode: readonly
learning_isolated: true"""
            
            # Insert collaborative metadata after main YAML
            content = content.replace(
                "status: thinking          # thinking, actioned, offline, dead-end\n---",
                f"status: thinking          # thinking, actioned, offline, dead-end\n{participant_yaml}\n---"
            )
            
            # Add session notes with participant tracking
            if self.session_history:
                notes_section = "\n## Discussion Notes\n\n"
                for item in self.session_history:
                    if item.get('type') == 'query':
                        participant = item.get('participant', 'guest')
                        notes_section += f"**Q ({participant})**: {item.get('content', '')}\n\n"
                
                # Insert after "## Discussion Notes" section
                content = content.replace(
                    "## Discussion Notes\n\n[Your thinking, exploration, design work...]",
                    notes_section
                )
            
            # Add collaborative session footer
            footer = f"""

---

## Collaborative Session Info

- **Mode**: Collaborative QC
- **Primary User**: dingo (owner)
- **Participant**: {self.participant or 'guest'}
- **RAG Mode**: READ-ONLY (isolated from personal learning)
- **Storage**: Separate namespace (qc-collab/)
- **Impact**: No personal AI pattern updates

This session was conducted in collaborative mode to prevent RAG pollution
and maintain identity separation between personal and collaborative work.
"""
            
            content += footer
            
            # Write file
            filename.write_text(content, encoding='utf-8')
            
            logger.info(f"✅ Saved collaborative QC session to {filename}")
            return str(filename)
            
        except Exception as e:
            logger.error(f"Failed to save collaborative QC session file: {e}", exc_info=True)
            return None
    
    async def _get_next_collaborative_qc_number(self, qc_collab_dir: Path, year: str, month: str) -> int:
        """Get next collaborative QC number for the given month"""
        try:
            qc_month_dir = qc_collab_dir / year / month
            
            if not qc_month_dir.exists():
                return 1
            
            # Find all QC-COLLAB-*.md files in this month (across all days)
            qc_files = list(qc_month_dir.rglob("QC-COLLAB-*.md"))
            
            if not qc_files:
                return 1
            
            # Extract numbers and find highest
            numbers = []
            for qc_file in qc_files:
                # Extract number from QC-COLLAB-NNN-topic.md format
                parts = qc_file.stem.split('-')
                if len(parts) >= 3 and parts[0] == 'QC' and parts[1] == 'COLLAB':
                    try:
                        numbers.append(int(parts[2]))
                    except ValueError:
                        continue
            
            if numbers:
                return max(numbers) + 1
            return 1
            
        except Exception as e:
            logger.error(f"Error getting next collaborative QC number: {e}")
            return 1
    
    # ==================== Collaborative QC Loading Methods ====================
    
    def _parse_qc_refs(self, load_str: str) -> list[str]:
        """
        Parse collaborative QC references from various formats.
        
        Accepts:
        - "002 003" → ["QC-COLLAB-002", "QC-COLLAB-003"]
        - "COLLAB-002,COLLAB-005" → ["QC-COLLAB-002", "QC-COLLAB-005"]
        - "2,5" → ["QC-COLLAB-002", "QC-COLLAB-005"]
        
        Returns list of normalized collaborative QC IDs.
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
            
            if ref.startswith('QC-COLLAB-'):
                # Already in full collaborative format
                refs.append(ref)
            elif ref.startswith('COLLAB-'):
                # Convert COLLAB-NNN to QC-COLLAB-NNN
                refs.append(f"QC-{ref}")
            else:
                # Convert short format to full collaborative format
                try:
                    num = int(ref)
                    refs.append(f"QC-COLLAB-{num:03d}")
                except ValueError:
                    logger.warning(f"Invalid collaborative QC reference: {ref}")
                    continue
        
        return refs
    
    async def _load_specific_collaborative_qc_sessions(self, qc_ids: list[str]) -> list[dict[str, Any]]:
        """
        Load specific collaborative QC sessions by ID.
        
        Args:
            qc_ids: List of collaborative QC IDs like ["QC-COLLAB-002", "QC-COLLAB-005"]
        
        Returns:
            List of collaborative QC session dictionaries with metadata
        """
        sessions = []
        
        home = Path.home()
        qc_collab_dir = home / "code" / "qc-collab"
        
        if not qc_collab_dir.exists():
            logger.warning(f"Collaborative QC directory not found: {qc_collab_dir}")
            return []
        
        for qc_id in qc_ids:
            try:
                # Search for collaborative QC file (could be in any date folder)
                qc_files = list(qc_collab_dir.rglob(f"{qc_id}-*.md"))
                
                if not qc_files:
                    logger.warning(f"Collaborative QC session not found: {qc_id}")
                    continue
                
                # Use the first match (should only be one)
                qc_file = qc_files[0]
                content = qc_file.read_text(encoding='utf-8')
                
                # Parse YAML header
                if not content.startswith('---'):
                    logger.warning(f"Collaborative QC file has no YAML header: {qc_file}")
                    continue
                
                parts = content.split('---', 2)
                if len(parts) < 3:
                    logger.warning(f"Collaborative QC file has invalid format: {qc_file}")
                    continue
                
                frontmatter = parts[1]
                body = parts[2]
                
                # Parse basic YAML fields manually
                qc_data = {'id': qc_id, 'file': str(qc_file), 'mode': 'collaborative'}
                
                for line in frontmatter.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip().strip('"')
                        
                        if key in ['id', 'date', 'time', 'duration', 'type', 'action', 'outcome', 'status', 'participant', 'primary_user']:
                            qc_data[key] = value
                
                # Extract title from first h1
                title = "Unknown"
                for line in body.split('\n'):
                    if line.startswith('# '):
                        title = line[2:].strip()
                        # Remove QC-COLLAB-XXX: prefix if present
                        if ':' in title:
                            title = title.split(':', 1)[1].strip()
                        break
                
                qc_data['title'] = title
                
                # Extract summary if available
                if '## Session Context' in body:
                    context_section = body.split('## Session Context', 1)[1]
                    context_section = context_section.split('##', 1)[0]
                    paragraphs = [p.strip() for p in context_section.split('\n\n') if p.strip()]
                    if paragraphs:
                        qc_data['summary'] = paragraphs[0][:200]
                
                sessions.append(qc_data)
                logger.info(f"Loaded collaborative QC session: {qc_id} from {qc_file}")
                
            except Exception as e:
                logger.error(f"Error loading collaborative QC {qc_id}: {e}", exc_info=True)
                continue
        
        return sessions
    
    async def _load_recent_collaborative_qc_sessions(self, limit: int = 3) -> list[dict[str, Any]]:
        """
        Load recent collaborative QC sessions for context reference.
        Returns list of collaborative QC session summaries.
        """
        try:
            home = Path.home()
            qc_collab_dir = home / "code" / "qc-collab"
            
            if not qc_collab_dir.exists():
                return []
            
            # Find all QC-COLLAB-*.md files
            qc_files = []
            for year_dir in sorted((qc_collab_dir).glob("20*"), reverse=True):
                if not year_dir.is_dir():
                    continue
                for month_dir in sorted(year_dir.iterdir(), reverse=True):
                    if not month_dir.is_dir():
                        continue
                    for day_dir in sorted(month_dir.iterdir(), reverse=True):
                        if not day_dir.is_dir():
                            continue
                        for qc_file in sorted(day_dir.glob("QC-COLLAB-*.md"), reverse=True):
                            qc_files.append(qc_file)
                            if len(qc_files) >= limit:
                                break
                        if len(qc_files) >= limit:
                            break
                    if len(qc_files) >= limit:
                        break
                if len(qc_files) >= limit:
                    break
            
            # Parse each collaborative QC file
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
                            participant = None
                            for line in frontmatter.split('\n'):
                                if line.startswith('id:'):
                                    qc_id = line.split(':', 1)[1].strip()
                                elif line.startswith('date:'):
                                    qc_date = line.split(':', 1)[1].strip()
                                elif line.startswith('participant:'):
                                    participant = line.split(':', 1)[1].strip()
                            
                            # Extract title from first h1
                            title = "Unknown"
                            for line in body.split('\n'):
                                if line.startswith('# '):
                                    title = line[2:].strip()
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
                                    'participant': participant or 'unknown',
                                    'key_insight': key_insight,
                                    'file': str(qc_file),
                                    'mode': 'collaborative'
                                })
                
                except Exception as e:
                    logger.error(f"Error parsing collaborative QC file {qc_file}: {e}")
                    continue
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error loading recent collaborative QC sessions: {e}")
            return []
    
    async def _offer_collaborative_task_creation(self, arguments: dict[str, Any]) -> str:
        """Offer to create task structure from collaborative session"""
        
        # Get context info
        context = self.context_loaded or {}
        context_name = context.get('name', 'unknown')
        
        # Extract title from session history
        title = "Collaborative implementation"
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
        
        participant = self.participant or 'guest'
        
        return (
            f"📋 Collaborative Task Details:\n"
            f"   Title: {title}\n"
            f"   Complexity: {complexity}\n"
            f"   Context: {context_name}\n"
            f"   Collaborator: {participant}\n"
            f"\n"
            f"💡 To create task structure:\n"
            f"   ~/code/scripts/task-create.sh [day] \"{title}\" {complexity}\n"
            f"   Note: Mark as collaborative effort with {participant}"
        )




