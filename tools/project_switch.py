"""
Project Switch tool - Navigate between Tâm Đắc ecosystem projects

Port of /project slash command to Zen MCP for cross-platform usage.
Works in Claude Code, Cursor, and any MCP client.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional
from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from tools.shared.tamdac import TamdacProject, MemoryManager, CommandManager
from .simple.base import SimpleTool

FIELD_DESCRIPTIONS = {
    "project": "Project name (e.g., 'toolbox', 'tamdac', 'motif', 'lumiere', 'arrow')",
    "section": "Optional section within project (e.g., 'tickets', 'solutions', 'prompts')",
    "provider": (
        "AI provider to use for this operation: 'claude', 'gemini', 'gpt4', or 'auto' for smart routing. "
        "Use 'gemini' or 'gpt4' to save Claude limits."
    ),
}


class ProjectSwitchRequest(ToolRequest):
    """Request model for Project Switch tool"""

    project: str = Field(..., description=FIELD_DESCRIPTIONS["project"])
    section: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["section"])
    provider: str = Field(default="auto", description=FIELD_DESCRIPTIONS["provider"])


class ProjectSwitchTool(SimpleTool):
    """
    Navigate between Tâm Đắc ecosystem projects with context loading.

    This is a port of the /project slash command to Zen MCP, making it available
    in both Claude Code AND Cursor (and any MCP client).

    Features:
    - Switch between projects (toolbox, tamdac, motif, etc.)
    - Navigate to project sections (tickets, solutions, prompts, etc.)
    - Load project context (memory, recent work, commands)
    - Provider selection (route to Claude, Gemini, or GPT-4)
    - Cross-platform (works in VSCode + Cursor)

    Example usage:
    - "Use project_switch with project=toolbox"
    - "Use project_switch with project=toolbox section=tickets"
    - "Use project_switch with project=motif provider=gemini"
    """

    def get_name(self) -> str:
        return "project_switch"

    def get_description(self) -> str:
        return (
            "Switch between Tâm Đắc ecosystem projects (toolbox, tamdac, motif, etc.) "
            "with automatic context loading. Supports sections (tickets, solutions, prompts). "
            "Choose AI provider to control which API limits are used."
        )

    def get_system_prompt(self) -> str:
        return """You are helping the user navigate between projects in the Tâm Đắc ecosystem.

Projects include:
- toolbox: Technical workspace (tickets, solutions, scripts)
- tamdac: Core constitution and contracts
- motif: Workflow orchestration engine
- lumiere: RAG system
- arrow: Visual learning
- wiib: Journal and reflections
- chord: Music composition

When switching projects:
1. Report target project and section (if applicable)
2. Show working directory path
3. Summarize project context (recent work, available commands)
4. Confirm ready status
"""

    def get_default_temperature(self) -> float:
        return 0.3  # Precise, factual responses for navigation

    def get_model_category(self) -> "ToolModelCategory":
        from tools.models import ToolModelCategory

        return ToolModelCategory.FAST_RESPONSE

    def get_request_model(self):
        return ProjectSwitchRequest

    async def execute(self, request: ProjectSwitchRequest, **kwargs) -> Dict[str, Any]:
        """Execute project switch"""

        try:
            # Determine target path
            if request.section:
                target_path = TamdacProject.get_section_path(request.project, request.section)
                location_desc = f"{request.project} / {request.section}"
            else:
                target_path = TamdacProject.get_project_root(request.project)
                location_desc = request.project

            # Verify path exists
            if not target_path.exists():
                return {
                    "success": False,
                    "error": f"Path does not exist: {target_path}",
                    "suggestion": "Check PROJECT-REGISTRY.json for correct paths",
                }

            # Change working directory (for subsequent operations)
            os.chdir(target_path)

            # Load project context
            context = self._load_project_context(target_path, request.project)

            return {
                "success": True,
                "project": request.project,
                "section": request.section,
                "location": location_desc,
                "working_directory": str(target_path),
                "provider_used": request.provider,
                "context": context,
                "message": f"Switched to {location_desc}. Working directory: {target_path}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project": request.project,
                "section": request.section,
            }

    def _load_project_context(self, project_path: Path, project_name: str) -> Dict[str, Any]:
        """Load project context for display"""

        context = {}

        # Check memory
        if MemoryManager.memory_exists(project_path):
            memory_content = MemoryManager.read_memory(project_path)
            context["memory_exists"] = True
            context["memory_size"] = len(memory_content)
        else:
            context["memory_exists"] = False

        # List commands
        commands = CommandManager.list_commands(project_path)
        context["commands"] = commands
        context["command_count"] = len(commands)

        # Check recent files (git-aware)
        try:
            import subprocess

            result = subprocess.run(
                ["git", "log", "--pretty=format:%H", "-1"],
                cwd=project_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                context["git_available"] = True
                context["latest_commit"] = result.stdout.strip()[:8]
            else:
                context["git_available"] = False
        except:
            context["git_available"] = False

        # Get project info
        try:
            project_info = TamdacProject.get_project_info(project_name)
            context["description"] = project_info.get("description", "")
            sections = TamdacProject.get_sections(project_name)
            context["available_sections"] = list(sections.keys()) if sections else []
        except:
            context["description"] = ""
            context["available_sections"] = []

        return context

    def get_input_schema(self) -> dict[str, Any]:
        """Return the input schema for MCP"""
        return {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": FIELD_DESCRIPTIONS["project"],
                },
                "section": {
                    "type": "string",
                    "description": FIELD_DESCRIPTIONS["section"],
                },
                "provider": {
                    "type": "string",
                    "description": FIELD_DESCRIPTIONS["provider"],
                    "default": "auto",
                },
                **COMMON_FIELD_DESCRIPTIONS,
            },
            "required": ["project"],
        }
