"""
Zen MCP Tool: Shell Executor
Execute shell commands and scripts safely
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, List
from pydantic import Field
from datetime import datetime

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from tools.shared.base_tool import BaseTool
from tools.models import ToolOutput
from mcp.types import TextContent

FIELD_DESCRIPTIONS = {
    "command": "Shell command or script to execute",
    "working_directory": "Working directory for command execution (defaults to current directory)",
    "timeout": "Timeout in seconds (default: 30)",
    "capture_output": "Whether to capture stdout/stderr (default: true)",
    "shell": "Whether to use shell execution (default: true)",
    "env_vars": "Additional environment variables as JSON string",
}

class ShellExecutorRequest(ToolRequest):
    """Request model for Shell Executor tool"""
    command: str = Field(..., description=FIELD_DESCRIPTIONS["command"])
    working_directory: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["working_directory"])
    timeout: int = Field(default=30, description=FIELD_DESCRIPTIONS["timeout"])
    capture_output: bool = Field(default=True, description=FIELD_DESCRIPTIONS["capture_output"])
    shell: bool = Field(default=False, description=FIELD_DESCRIPTIONS["shell"])
    env_vars: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["env_vars"])


class ShellExecutorTool(BaseTool):
    """
    Execute shell commands and scripts safely.
    
    This tool provides secure shell command execution:
    - Execute shell commands and scripts
    - Set working directory
    - Configure timeouts
    - Capture output
    - Set environment variables
    - Safe execution with proper error handling
    """

    def get_name(self) -> str:
        return "shell_executor"

    def get_description(self) -> str:
        return "Execute shell commands and scripts safely with proper error handling."

    def get_system_prompt(self) -> str:
        return """You are a shell command executor that safely runs shell commands and scripts.

Your role is to:
1. Execute shell commands and scripts safely
2. Handle errors gracefully
3. Provide clear output and error messages
4. Respect timeouts and working directories
5. Capture output properly

Always provide clear, actionable responses with proper error handling."""

    def get_default_temperature(self) -> float:
        return 0.1  # Very low temperature for consistent command execution

    def get_model_category(self) -> "ToolModelCategory":
        """Shell execution prioritizes accuracy and consistency"""
        from tools.models import ToolModelCategory
        return ToolModelCategory.BALANCED

    def get_request_model(self):
        """Return the ShellExecutor-specific request model"""
        return ShellExecutorRequest

    def requires_model(self) -> bool:
        """
        Shell executor doesn't require model resolution at the MCP boundary.
        
        This is a pure command execution tool that runs shell commands without calling
        external AI models.
        
        Returns:
            bool: False - shell executor doesn't need AI model access
        """
        return False

    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input"""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command or script to execute"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Working directory for command execution (defaults to current directory)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 30)",
                    "default": 30
                },
                "capture_output": {
                    "type": "boolean",
                    "description": "Whether to capture stdout/stderr (default: true)",
                    "default": True
                },
                "shell": {
                    "type": "boolean",
                    "description": "Whether to use shell execution (default: false for security)",
                    "default": False
                },
                "env_vars": {
                    "type": "string",
                    "description": "Additional environment variables as JSON string"
                }
            },
            "required": ["command"],
            "additionalProperties": False,
        }

    def get_annotations(self) -> Optional[dict[str, Any]]:
        """Return tool annotations indicating this is a command execution tool"""
        return {"commandExecution": True}

    async def prepare_prompt(self, request: ShellExecutorRequest) -> str:
        """Not used for this utility tool"""
        return ""

    def format_response(self, response: str, request: ShellExecutorRequest, model_info: Optional[dict] = None) -> str:
        """Not used for this utility tool"""
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Execute the shell command.
        
        This overrides the base class execute to provide direct command execution without AI model calls.
        
        Args:
            arguments: Tool arguments including command, working_directory, timeout, etc.
            
        Returns:
            Formatted command execution results
        """
        try:
            command = arguments.get("command", "")
            if not command:
                return [TextContent(type="text", text=json.dumps({
                    "success": False, 
                    "error": "No command provided"
                }))]
            
            # Get working directory
            working_dir = arguments.get("working_directory")
            if working_dir:
                working_dir = Path(working_dir).resolve()
                if not working_dir.exists():
                    return [TextContent(type="text", text=json.dumps({
                        "success": False, 
                        "error": f"Working directory does not exist: {working_dir}"
                    }))]
            else:
                working_dir = Path.cwd()
            
            # Get timeout
            timeout = arguments.get("timeout", 30)
            
            # Get capture output setting
            capture_output = arguments.get("capture_output", True)
            
            # Get shell setting (default to False for security)
            use_shell = arguments.get("shell", False)
            
            # Parse environment variables
            env_vars = {}
            env_vars_str = arguments.get("env_vars")
            if env_vars_str:
                try:
                    env_vars = json.loads(env_vars_str)
                except json.JSONDecodeError:
                    return [TextContent(type="text", text=json.dumps({
                        "success": False, 
                        "error": "Invalid JSON in env_vars"
                    }))]
            
            # Prepare environment
            env = os.environ.copy()
            env.update(env_vars)
            
            # Execute command
            result = await self._execute_command(
                command=command,
                working_dir=working_dir,
                timeout=timeout,
                capture_output=capture_output,
                use_shell=use_shell,
                env=env
            )
            
            # Format as ToolOutput
            tool_output = ToolOutput(
                status="success" if result.get("success", False) else "error",
                content=json.dumps(result, indent=2),
                content_type="json",
                metadata={
                    "tool_name": self.get_name(),
                    "command": command,
                    "working_directory": str(working_dir),
                    "timeout": timeout,
                },
            )
            
            return [TextContent(type="text", text=tool_output.model_dump_json())]
                
        except Exception as e:
            error_result = {"success": False, "error": f"Shell execution error: {str(e)}"}
            tool_output = ToolOutput(
                status="error",
                content=json.dumps(error_result, indent=2),
                content_type="json",
                metadata={"tool_name": self.get_name()},
            )
            return [TextContent(type="text", text=tool_output.model_dump_json())]

    async def _execute_command(
        self,
        command: str,
        working_dir: Path,
        timeout: int,
        capture_output: bool,
        use_shell: bool,
        env: dict
    ) -> dict[str, Any]:
        """Execute the shell command with proper error handling"""
        
        start_time = datetime.now()
        
        try:
            # Prepare command execution
            if use_shell:
                # Use shell execution
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE if capture_output else None,
                    stderr=asyncio.subprocess.PIPE if capture_output else None,
                    cwd=working_dir,
                    env=env
                )
            else:
                # Use direct command execution (split command into args)
                import shlex
                args = shlex.split(command)
                process = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE if capture_output else None,
                    stderr=asyncio.subprocess.PIPE if capture_output else None,
                    cwd=working_dir,
                    env=env
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
                    "error": f"Command timed out after {timeout} seconds",
                    "command": command,
                    "working_directory": str(working_dir),
                    "timeout": timeout,
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                }
            
            # Process output
            stdout_text = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr_text = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "command": command,
                "working_directory": str(working_dir),
                "timeout": timeout,
                "duration_seconds": duration,
                "timestamp": start_time.isoformat()
            }
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return {
                "success": False,
                "error": f"Command execution failed: {str(e)}",
                "command": command,
                "working_directory": str(working_dir),
                "timeout": timeout,
                "duration_seconds": duration,
                "timestamp": start_time.isoformat()
            }
