"""
Zen MCP Tool: Cursor CLI Integration
Execute Cursor CLI commands via zen MCP for cross-platform AI orchestration
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import Field

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from tools.shared.base_tool import BaseTool
from tools.models import ToolOutput
from mcp.types import TextContent

FIELD_DESCRIPTIONS = {
    "command": "Natural language command for Cursor CLI to execute",
    "model": "AI model to use (gpt-5, claude-4, grok, auto)",
    "working_dir": "Working directory for command execution",
    "timeout": "Timeout in seconds (default: 300)",
    "approve_all": "Auto-approve all actions (use with caution)",
}

class CursorCLIRequest(ToolRequest):
    """Request model for Cursor CLI tool"""
    command: str = Field(..., description=FIELD_DESCRIPTIONS["command"])
    model: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["model"])
    working_dir: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["working_dir"])
    timeout: int = Field(default=300, description=FIELD_DESCRIPTIONS["timeout"])
    approve_all: bool = Field(default=False, description=FIELD_DESCRIPTIONS["approve_all"])

class CursorCLITool(BaseTool):
    """
    Execute Cursor CLI commands from any MCP client.

    This tool enables cross-platform AI agent orchestration by wrapping
    Cursor CLI functionality as an MCP tool. Allows Claude Code, ChatGPT,
    and other MCP clients to invoke Cursor's AI capabilities programmatically.

    Use Cases:
    - Cross-platform AI code reviews
    - Multi-agent collaborative workflows
    - Headless CI/CD automation
    - Coordinated development across tools
    """

    def get_name(self) -> str:
        return "cursor_cli"

    def get_description(self) -> str:
        return "Execute Cursor CLI commands for AI-powered code operations and cross-platform orchestration."

    def get_system_prompt(self) -> str:
        return """You are a Cursor CLI integration tool that enables cross-platform AI agent collaboration.

Your role is to:
1. Execute Cursor CLI commands with proper context
2. Handle model selection and switching
3. Manage working directories and permissions
4. Coordinate with other AI tools via zen MCP
5. Provide structured output for multi-agent workflows

Always validate commands, respect timeouts, and provide clear error messages."""

    def get_default_temperature(self) -> float:
        return 0.2  # Low temperature for consistent command execution

    def get_model_category(self) -> "ToolModelCategory":
        """Cursor CLI integration prioritizes accuracy"""
        from tools.models import ToolModelCategory
        return ToolModelCategory.BALANCED

    def get_request_model(self):
        """Return the CursorCLI-specific request model"""
        return CursorCLIRequest

    def requires_model(self) -> bool:
        """
        Cursor CLI doesn't require zen model resolution.

        Cursor CLI has its own model management, so we don't need
        to resolve models at the zen MCP boundary.

        Returns:
            bool: False - cursor_cli manages its own models
        """
        return False

    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input"""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Natural language command for Cursor CLI to execute"
                },
                "model": {
                    "type": "string",
                    "description": "AI model to use (gpt-5, claude-4, grok, auto)",
                    "enum": ["gpt-5", "claude-4", "grok", "auto", None]
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory for command execution"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 300)",
                    "default": 300
                },
                "approve_all": {
                    "type": "boolean",
                    "description": "Auto-approve all actions (use with caution)",
                    "default": False
                }
            },
            "required": ["command"],
            "additionalProperties": False,
        }

    def get_annotations(self) -> Optional[dict[str, Any]]:
        """Return tool annotations indicating this requires Cursor CLI"""
        return {
            "requiresExternal": "cursor-cli",
            "commandExecution": True
        }

    async def prepare_prompt(self, request: CursorCLIRequest) -> str:
        """Not used for this utility tool"""
        return ""

    def format_response(self, response: str, request: CursorCLIRequest, model_info: Optional[dict] = None) -> str:
        """Not used for this utility tool"""
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Execute Cursor CLI command.

        This overrides the base class execute to provide direct command execution
        without AI model calls (Cursor CLI handles its own AI models).

        Args:
            arguments: Tool arguments including command, model, working_dir, etc.

        Returns:
            Formatted command execution results
        """
        try:
            # Check if cursor-agent is installed
            if not await self._check_cursor_cli_installed():
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "error": "Cursor CLI not installed. Install with: curl https://cursor.com/install -fsSL | bash"
                }))]

            command = arguments.get("command", "")
            if not command:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "error": "No command provided"
                }))]

            model = arguments.get("model", "auto")
            working_dir = arguments.get("working_dir") or str(Path.cwd())
            timeout = arguments.get("timeout", 300)
            approve_all = arguments.get("approve_all", False)

            # Validate working directory
            work_path = Path(working_dir).resolve()
            if not work_path.exists():
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "error": f"Working directory does not exist: {work_path}"
                }))]

            # Build cursor-agent command
            cursor_cmd = await self._build_cursor_command(command, model, approve_all)

            # Execute command
            result = await self._execute_cursor_cli(
                cursor_cmd,
                working_dir=work_path,
                timeout=timeout
            )

            # Format as ToolOutput
            tool_output = ToolOutput(
                status="success" if result.get("success", False) else "error",
                content=json.dumps(result, indent=2),
                content_type="json",
                metadata={
                    "tool_name": self.get_name(),
                    "command": command,
                    "model": model,
                    "working_dir": str(work_path),
                },
            )

            return [TextContent(type="text", text=tool_output.model_dump_json())]

        except Exception as e:
            error_result = {"success": False, "error": f"Cursor CLI execution error: {str(e)}"}
            tool_output = ToolOutput(
                status="error",
                content=json.dumps(error_result, indent=2),
                content_type="json",
                metadata={"tool_name": self.get_name()},
            )
            return [TextContent(type="text", text=tool_output.model_dump_json())]

    async def _check_cursor_cli_installed(self) -> bool:
        """Check if cursor-agent CLI is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "which", "cursor-agent",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            return process.returncode == 0 and stdout.strip() != b""
        except Exception:
            return False

    async def _build_cursor_command(self, command: str, model: str, approve_all: bool) -> str:
        """Build the cursor-agent command with proper escaping"""
        # Escape the command for shell
        escaped_command = command.replace('"', '\\"')

        # Base command
        cursor_cmd = f'cursor-agent chat "{escaped_command}"'

        # Add model selection if specified
        if model and model != "auto":
            cursor_cmd = f'/model {model} && {cursor_cmd}'

        # Add auto-approve flag if requested
        if approve_all:
            cursor_cmd = f'{cursor_cmd} --yes'

        return cursor_cmd

    async def _execute_cursor_cli(
        self,
        command: str,
        working_dir: Path,
        timeout: int
    ) -> dict[str, Any]:
        """Execute the cursor-agent command with proper error handling"""

        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )

            # Wait for completion with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return {
                    "success": False,
                    "error": f"Cursor CLI timed out after {timeout} seconds",
                    "command": command,
                    "working_directory": str(working_dir),
                    "timeout": timeout
                }

            # Process output
            stdout_text = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr_text = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            return {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "output": stdout_text,
                "error": stderr_text if stderr_text else None,
                "command": command,
                "working_directory": str(working_dir),
                "timeout": timeout
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Command execution failed: {str(e)}",
                "command": command,
                "working_directory": str(working_dir),
                "timeout": timeout
            }
