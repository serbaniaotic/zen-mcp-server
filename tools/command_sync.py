"""
command-sync - Ported from Tamdac universal command

Original: tamdac/.claude/commands/command-sync.md
Description: Auto-recover missing slash commands from tamdac registry
Version: 1.0.0
"""

from typing import TYPE_CHECKING, Any, Dict, Optional
from pathlib import Path
import shutil

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from tools.shared.tamdac import TamdacProject, MemoryManager, CommandManager
from .simple.base import SimpleTool


class CommandSyncRequest(ToolRequest):
    """Request model for command-sync"""

    project: Optional[str] = None
    update: bool = False
    dry_run: bool = False


class CommandSyncTool(SimpleTool):
    """
    Auto-recover missing slash commands from tamdac registry

    Ported from tamdac/.claude/commands/command-sync.md

    Cross-platform implementation that works in:
    - Claude Code (VSCode)
    - GitHub Copilot Chat (VSCode)
    - Cursor IDE
    - Any MCP client
    """

    def get_name(self) -> str:
        return "command_sync"

    def get_description(self) -> str:
        return "Auto-recover missing slash commands from tamdac registry"

    def get_system_prompt(self) -> str:
        return """Auto-recover missing slash commands from tamdac registry.

This tool detects missing commands in the current project and copies them from the tamdac registry sources.
It follows the same logic as the original command-sync.md workflow."""

    def get_default_temperature(self) -> float:
        return 0.3

    def get_model_category(self) -> "ToolModelCategory":
        from tools.models import ToolModelCategory
        return ToolModelCategory.FAST_RESPONSE

    def get_request_model(self):
        return CommandSyncRequest

    async def execute(self, request: CommandSyncRequest, **kwargs) -> Dict[str, Any]:
        """
        Execute the command sync workflow

        Steps (from original markdown):
        1. Detect current project from cwd
        2. Load PROJECT-REGISTRY.json
        3. Get universal + project-specific commands
        4. Check which commands are missing in .claude/commands/
        5. Copy missing commands from tamdac
        6. Report sync status
        """

        try:
            # Get current working directory
            current_path = Path.cwd()
            
            # Detect project from current path
            project_name = self._detect_project(current_path)
            if not project_name:
                return {
                    "success": False,
                    "error": "Could not detect project from current path",
                    "current_path": str(current_path)
                }

            # Load PROJECT-REGISTRY
            registry = TamdacProject.load_registry()
            project_info = registry.get("projects", {}).get(project_name)
            if not project_info:
                return {
                    "success": False,
                    "error": f"Project '{project_name}' not found in PROJECT-REGISTRY.json"
                }

            # Get required commands
            universal_commands = registry.get("universal_commands", {})
            project_commands = project_info.get("required_commands", [])
            
            all_required = list(universal_commands.keys()) + project_commands
            
            # Check which commands are missing
            commands_dir = CommandManager.get_commands_dir(current_path)
            missing_commands = []
            existing_commands = []
            
            for cmd_name in all_required:
                cmd_file = commands_dir / f"{cmd_name}.md"
                if cmd_file.exists():
                    existing_commands.append(cmd_name)
                else:
                    missing_commands.append(cmd_name)

            if request.dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "project": project_name,
                    "existing_commands": existing_commands,
                    "missing_commands": missing_commands,
                    "would_recover": len(missing_commands)
                }

            # Copy missing commands
            tamdac_root = TamdacProject.get_tamdac_root()
            recovered_commands = []
            failed_commands = []

            for cmd_name in missing_commands:
                try:
                    # Try to find source
                    source_path = self._find_command_source(tamdac_root, cmd_name, universal_commands, project_info)
                    if source_path and source_path.exists():
                        dest_path = commands_dir / f"{cmd_name}.md"
                        shutil.copy2(source_path, dest_path)
                        recovered_commands.append(cmd_name)
                    else:
                        failed_commands.append(cmd_name)
                except Exception as e:
                    failed_commands.append(f"{cmd_name} (error: {str(e)})")

            return {
                "success": True,
                "project": project_name,
                "existing_commands": existing_commands,
                "recovered_commands": recovered_commands,
                "failed_commands": failed_commands,
                "total_recovered": len(recovered_commands),
                "total_failed": len(failed_commands)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Command sync failed: {e}"
            }

    def _detect_project(self, current_path: Path) -> Optional[str]:
        """Detect project name from current path"""
        # Check if we're in tamdac
        if "tamdac" in str(current_path):
            return "tamdac"
        
        # Check if we're in a sibling project
        parent = current_path.parent
        while parent != parent.parent:  # Not at root
            if parent.name in ["toolbox", "arrow", "wiib", "motif", "ecce", "obs", "chord"]:
                return parent.name
            parent = parent.parent
        
        return None

    def _find_command_source(self, tamdac_root: Path, cmd_name: str, universal_commands: dict, project_info: dict) -> Optional[Path]:
        """Find the source path for a command"""
        # Check if it's a universal command
        if cmd_name in universal_commands:
            source_info = universal_commands[cmd_name]
            source_path = source_info.get("source", "")
            if source_path:
                return tamdac_root / source_path
        
        # Check project-specific commands
        project_commands = project_info.get("required_commands", [])
        if cmd_name in project_commands:
            # Look in tamdac commands first
            tamdac_cmd = tamdac_root / ".claude" / "commands" / f"{cmd_name}.md"
            if tamdac_cmd.exists():
                return tamdac_cmd
        
        return None

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """Return tool-specific field definitions"""
        return {
            "project": {
                "type": "string",
                "description": "Target project name (auto-detected if not provided)"
            },
            "update": {
                "type": "boolean",
                "description": "Update existing commands to latest versions",
                "default": False
            },
            "dry_run": {
                "type": "boolean", 
                "description": "Show what would be done without making changes",
                "default": False
            }
        }

    def prepare_prompt(self, request: CommandSyncRequest, **kwargs) -> str:
        """Prepare the prompt for command sync"""
        prompt = f"""Auto-recover missing slash commands from tamdac registry.

Project: {request.project or 'auto-detect'}
Update mode: {request.update}
Dry run: {request.dry_run}

This tool will:
1. Detect current project from working directory
2. Load PROJECT-REGISTRY.json to get required commands
3. Check which commands are missing in .claude/commands/
4. Copy missing commands from tamdac sources
5. Report sync status

Please execute the command sync workflow."""
        
        return prompt
