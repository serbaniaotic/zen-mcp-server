"""
Tâm Đắc project integration utilities for Zen MCP tools

Provides interfaces to:
- PROJECT-REGISTRY.json
- Project structure navigation
- Memory management
- Command synchronization
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class TamdacProject:
    """Interface to Tâm Đắc PROJECT-REGISTRY.json"""

    @staticmethod
    def get_tamdac_root() -> Path:
        """Get tamdac project root directory"""
        # Try common locations
        home = Path.home()
        candidates = [
            home / "code/tamdac",
            Path("/c/Users/serba/code/tamdac"),  # Windows
            Path("/home/dingo/code/tamdac"),     # Linux/WSL
        ]

        for path in candidates:
            if path.exists() and (path / "PROJECT-REGISTRY.json").exists():
                return path

        raise FileNotFoundError("Could not locate tamdac project root")

    @staticmethod
    def load_registry() -> Dict[str, Any]:
        """Load PROJECT-REGISTRY.json"""
        tamdac_root = TamdacProject.get_tamdac_root()
        registry_path = tamdac_root / "PROJECT-REGISTRY.json"

        if not registry_path.exists():
            raise FileNotFoundError(f"PROJECT-REGISTRY.json not found at {registry_path}")

        return json.loads(registry_path.read_text())

    @staticmethod
    def get_project_info(project_name: str) -> Dict[str, Any]:
        """Get project information from registry"""
        registry = TamdacProject.load_registry()
        projects = registry.get("projects", {})

        if project_name not in projects:
            available = ", ".join(projects.keys())
            raise ValueError(f"Project '{project_name}' not found. Available: {available}")

        return projects[project_name]

    @staticmethod
    def get_sections(project_name: str) -> Dict[str, str]:
        """Get project sections and their working directories"""
        info = TamdacProject.get_project_info(project_name)
        return info.get("working_directory_map", {})

    @staticmethod
    def get_project_root(project_name: str) -> Path:
        """Get absolute path to project root"""
        info = TamdacProject.get_project_info(project_name)
        path_str = info.get("path", "")

        # Handle relative paths
        if path_str.startswith("../"):
            tamdac_root = TamdacProject.get_tamdac_root()
            return (tamdac_root / path_str).resolve()
        else:
            return Path(path_str)

    @staticmethod
    def get_section_path(project_name: str, section: str) -> Path:
        """Get absolute path to project section"""
        sections = TamdacProject.get_sections(project_name)

        if section not in sections:
            available = ", ".join(sections.keys()) if sections else "none"
            raise ValueError(
                f"Section '{section}' not found in project '{project_name}'. "
                f"Available sections: {available}"
            )

        section_path = sections[section]
        project_root = TamdacProject.get_project_root(project_name)

        # Resolve relative section paths
        if section_path.startswith("./") or section_path.startswith("../"):
            return (project_root / section_path).resolve()
        else:
            return Path(section_path)

    @staticmethod
    def list_projects() -> List[str]:
        """List all available projects"""
        registry = TamdacProject.load_registry()
        return list(registry.get("projects", {}).keys())

    @staticmethod
    def get_universal_commands() -> List[str]:
        """Get list of universal commands required by all projects"""
        registry = TamdacProject.load_registry()
        return registry.get("universal_commands", [])

    @staticmethod
    def get_project_commands(project_name: str) -> List[str]:
        """Get project-specific commands"""
        info = TamdacProject.get_project_info(project_name)
        return info.get("required_commands", [])


class MemoryManager:
    """Manage .claude/memory.md files"""

    @staticmethod
    def get_memory_path(project_path: Path) -> Path:
        """Get path to project's memory.md"""
        return project_path / ".claude/memory.md"

    @staticmethod
    def memory_exists(project_path: Path) -> bool:
        """Check if memory.md exists"""
        return MemoryManager.get_memory_path(project_path).exists()

    @staticmethod
    def read_memory(project_path: Path) -> str:
        """Read memory.md content"""
        memory_path = MemoryManager.get_memory_path(project_path)
        if memory_path.exists():
            return memory_path.read_text()
        return ""

    @staticmethod
    def write_memory(project_path: Path, content: str) -> None:
        """Write memory.md content"""
        memory_path = MemoryManager.get_memory_path(project_path)
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        memory_path.write_text(content)


class CommandManager:
    """Manage .claude/commands/ directory"""

    @staticmethod
    def get_commands_dir(project_path: Path) -> Path:
        """Get path to project's commands directory"""
        return project_path / ".claude/commands"

    @staticmethod
    def list_commands(project_path: Path) -> List[str]:
        """List all commands in project"""
        commands_dir = CommandManager.get_commands_dir(project_path)
        if not commands_dir.exists():
            return []

        return [f.stem for f in commands_dir.glob("*.md")]

    @staticmethod
    def command_exists(project_path: Path, command_name: str) -> bool:
        """Check if command exists"""
        commands_dir = CommandManager.get_commands_dir(project_path)
        return (commands_dir / f"{command_name}.md").exists()

    @staticmethod
    def get_command_path(project_path: Path, command_name: str) -> Path:
        """Get path to specific command file"""
        return CommandManager.get_commands_dir(project_path) / f"{command_name}.md"
