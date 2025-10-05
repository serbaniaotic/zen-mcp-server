#!/usr/bin/env python3
"""
Command Generator - Watch for new .md commands and port them to Zen MCP tools

This script enables a powerful workflow:
1. Use Claude Code to create new command (.md file in .claude/commands/)
2. Script detects the new command
3. Prompts you to port it to Zen MCP (cross-platform)
4. Can use any AI model (Claude, Gemini, GPT-4) to do the porting

Usage:
  python scripts/command-generator.py --watch
  python scripts/command-generator.py --port command-name
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent


class CommandWatcher(FileSystemEventHandler):
    """Watch for new .md commands in .claude/commands/"""

    def __init__(self, callback):
        self.callback = callback
        self.processed = set()

    def on_created(self, event):
        if event.is_directory:
            return

        if isinstance(event, FileCreatedEvent) and event.src_path.endswith(".md"):
            command_path = Path(event.src_path)
            if command_path.stem not in self.processed:
                self.processed.add(command_path.stem)
                self.callback(command_path)


class CommandGenerator:
    """Generate Zen MCP tools from Claude markdown commands"""

    def __init__(self, tamdac_root: Optional[Path] = None):
        if tamdac_root is None:
            # Auto-detect tamdac root
            home = Path.home()
            candidates = [
                home / "code/tamdac",
                Path("/c/Users/serba/code/tamdac"),
                Path("/home/dingo/code/tamdac"),
            ]
            for path in candidates:
                if path.exists():
                    tamdac_root = path
                    break

        if tamdac_root is None:
            raise FileNotFoundError("Could not locate tamdac root")

        self.tamdac_root = tamdac_root
        self.zen_root = tamdac_root.parent / "zen-mcp-server"

    def watch_for_commands(self):
        """Watch .claude/commands/ for new commands"""
        commands_dir = self.tamdac_root / ".claude/commands"

        if not commands_dir.exists():
            print(f"Commands directory not found: {commands_dir}")
            return

        print(f"👀 Watching for new commands in: {commands_dir}")
        print("Create a new .md file in .claude/commands/ to trigger porting...")
        print()

        event_handler = CommandWatcher(self.on_new_command)
        observer = Observer()
        observer.schedule(event_handler, str(commands_dir), recursive=False)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    def on_new_command(self, command_path: Path):
        """Callback when new command is detected"""
        command_name = command_path.stem

        print(f"🆕 New command detected: {command_name}")
        print(f"   File: {command_path}")
        print()

        # Read command content
        content = command_path.read_text()
        print("Preview:")
        print("─" * 60)
        lines = content.split("\n")
        for line in lines[:15]:  # Show first 15 lines
            print(f"   {line}")
        if len(lines) > 15:
            print(f"   ... ({len(lines) - 15} more lines)")
        print("─" * 60)
        print()

        # Prompt user
        response = input("Port this command to Zen MCP? [y/N]: ")

        if response.lower() == "y":
            self.port_command(command_name, command_path)
        else:
            print("Skipped. You can port manually later with:")
            print(f"  python scripts/command-generator.py --port {command_name}")
            print()

    def port_command(self, command_name: str, md_path: Path):
        """Port a markdown command to Zen MCP tool"""

        print(f"🔄 Porting {command_name} to Zen MCP...")
        print()

        # Read markdown content
        md_content = md_path.read_text()

        # Generate tool name
        tool_name = command_name.replace("-", "_")
        tool_file = self.zen_root / f"tools/{tool_name}.py"

        # Check if already exists
        if tool_file.exists():
            print(f"⚠️  Tool already exists: {tool_file}")
            response = input("Overwrite? [y/N]: ")
            if response.lower() != "y":
                print("Cancelled.")
                return

        # Generate tool code
        print("Generating Python tool code...")
        tool_code = self.generate_tool_code(command_name, tool_name, md_content)

        # Write tool file
        tool_file.write_text(tool_code)
        print(f"✅ Created: {tool_file}")

        # Update __init__.py
        self.update_tool_registry(tool_name)

        print()
        print("✨ Port complete!")
        print()
        print("Next steps:")
        print("1. Review the generated code")
        print("2. Test in Claude Code: 'Use " + tool_name + " ...'")
        print("3. Test in Cursor: 'Use " + tool_name + " ...'")
        print()

    def generate_tool_code(self, command_name: str, tool_name: str, md_content: str) -> str:
        """Generate Python tool code from markdown command"""

        # Extract description from markdown frontmatter
        description = "Ported command"
        if "description:" in md_content:
            for line in md_content.split("\n"):
                if line.strip().startswith("description:"):
                    description = line.split(":", 1)[1].strip()
                    break

        # Generate tool class
        class_name = "".join(word.title() for word in tool_name.split("_")) + "Tool"

        tool_code = f'''"""
{command_name} - Ported from Claude command

Original: .claude/commands/{command_name}.md
Description: {description}
"""

from typing import TYPE_CHECKING, Any, Optional
from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from .simple.base import SimpleTool


class {class_name}Request(ToolRequest):
    """Request model for {command_name}"""

    # TODO: Add specific parameters based on command requirements
    prompt: str = Field(..., description="Task description")


class {class_name}(SimpleTool):
    """
    {description}

    Ported from .claude/commands/{command_name}.md

    Original markdown command:
    {md_content[:500]}...
    """

    def get_name(self) -> str:
        return "{tool_name}"

    def get_description(self) -> str:
        return "{description}"

    def get_system_prompt(self) -> str:
        # TODO: Extract and adapt from markdown content
        return """Original command logic:

{md_content}
"""

    def get_default_temperature(self) -> float:
        return 0.5

    def get_model_category(self) -> "ToolModelCategory":
        from tools.models import ToolModelCategory
        return ToolModelCategory.FAST_RESPONSE

    def get_request_model(self):
        return {class_name}Request

    async def execute(self, request, **kwargs):
        # TODO: Implement command logic
        # Original markdown describes the workflow
        # Translate to Python operations

        return {{
            "success": True,
            "message": "Tool executed (implementation pending)",
            "original_command": "{command_name}",
        }}

    def get_input_schema(self) -> dict[str, Any]:
        return {{
            "type": "object",
            "properties": {{
                "prompt": {{
                    "type": "string",
                    "description": "Task description",
                }},
                **COMMON_FIELD_DESCRIPTIONS,
            }},
            "required": ["prompt"],
        }}
'''

        return tool_code

    def update_tool_registry(self, tool_name: str):
        """Update tools/__init__.py to register new tool"""

        init_file = self.zen_root / "tools/__init__.py"

        if not init_file.exists():
            print(f"⚠️  Could not find: {init_file}")
            return

        content = init_file.read_text()

        # Generate class name
        class_name = "".join(word.title() for word in tool_name.split("_")) + "Tool"

        # Add import
        import_line = f"from .{tool_name} import {class_name}"
        if import_line not in content:
            # Find where to insert (after other imports)
            lines = content.split("\n")
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("from ."):
                    insert_idx = i + 1

            lines.insert(insert_idx, import_line)
            content = "\n".join(lines)

        # Add to __all__
        if f'"{class_name}"' not in content:
            # Find __all__ array
            all_idx = content.find("__all__ = [")
            if all_idx != -1:
                # Find closing bracket
                close_idx = content.find("]", all_idx)
                # Insert before closing
                content = content[:close_idx] + f'    "{class_name}",\n' + content[close_idx:]

        init_file.write_text(content)
        print(f"✅ Updated: {init_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate Zen MCP tools from Claude commands")
    parser.add_argument("--watch", action="store_true", help="Watch for new commands")
    parser.add_argument("--port", metavar="COMMAND", help="Port specific command to Zen MCP")

    args = parser.parse_args()

    generator = CommandGenerator()

    if args.watch:
        generator.watch_for_commands()
    elif args.port:
        tamdac_root = generator.tamdac_root
        md_path = tamdac_root / f".claude/commands/{args.port}.md"

        if not md_path.exists():
            print(f"❌ Command not found: {md_path}")
            sys.exit(1)

        generator.port_command(args.port, md_path)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
