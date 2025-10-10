"""
Zen MCP Tool: Evidence Versioning & Collision Detection
Implements Gap #2 (Version Control) from the Evidence Harmony Protocol.
"""
import hashlib
from pathlib import Path
from typing import Any, Dict

from tools.shared.base_tool import BaseTool
from mcp.types import TextContent


class EvidenceVersioningTool(BaseTool):
    """
    Provides utilities for evidence versioning and collision detection.
    This tool helps prevent data corruption by checking for file modifications
    before an agent performs a write operation.
    """

    def get_name(self) -> str:
        return "evidence_versioning"

    def get_description(self) -> str:
        return "Provides file checksum and collision detection utilities for evidence files."

    def requires_model(self) -> bool:
        """File versioning utility - no AI model needed"""
        return False

    def get_input_schema(self) -> dict[str, Any]:
        """Generate input schema for evidence versioning"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_checksum", "check_collision"],
                    "description": "Action to perform: get_checksum or check_collision"
                },
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the evidence file"
                },
                "expected_checksum": {
                    "type": "string",
                    "description": "Expected SHA256 checksum (required for check_collision)"
                }
            },
            "required": ["action", "file_path"]
        }

    def get_system_prompt(self) -> str:
        """Not used - evidence versioning doesn't use AI"""
        return ""

    async def prepare_prompt(self, request) -> str:
        """Not used - evidence versioning doesn't use AI prompts"""
        return ""

    def get_request_model(self):
        """Evidence versioning uses dict arguments directly"""
        from tools.shared.base_models import ToolRequest
        return ToolRequest

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Executes a versioning action, like getting a checksum or checking for a collision.

        Args:
            arguments (dict): A dictionary containing:
                - action (str): 'get_checksum' or 'check_collision'.
                - file_path (str): The absolute path to the evidence file.
                - expected_checksum (str, optional): The expected checksum for 'check_collision'.
        """
        action = arguments.get("action")
        file_path_str = arguments.get("file_path")

        if not all([action, file_path_str]):
            return self._error("Missing required arguments: action, file_path")

        file_path = Path(file_path_str)
        if not file_path.exists() or not file_path.is_file():
            return self._error(f"File not found or is not a regular file: {file_path_str}")

        if action == "get_checksum":
            return self._get_checksum(file_path)
        elif action == "check_collision":
            expected_checksum = arguments.get("expected_checksum")
            if not expected_checksum:
                return self._error("Missing required argument for 'check_collision': expected_checksum")
            return self._check_collision(file_path, expected_checksum)
        else:
            return self._error(f"Invalid action: {action}. Valid actions are 'get_checksum', 'check_collision'.")

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculates the SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _get_checksum(self, file_path: Path) -> list[TextContent]:
        """Handles the 'get_checksum' action."""
        try:
            checksum = self._calculate_checksum(file_path)
            return self._success(
                f"Checksum for {file_path.name} is {checksum}",
                {"file_path": str(file_path), "checksum": checksum}
            )
        except Exception as e:
            return self._error(f"Failed to calculate checksum for {file_path}: {e}")

    def _check_collision(self, file_path: Path, expected_checksum: str) -> list[TextContent]:
        """Handles the 'check_collision' action."""
        try:
            current_checksum = self._calculate_checksum(file_path)
            collision_detected = current_checksum != expected_checksum

            if collision_detected:
                summary = f"Collision DETECTED for {file_path.name}. File has been modified."
            else:
                summary = f"No collision detected for {file_path.name}. File is up to date."

            return self._success(
                summary,
                {
                    "file_path": str(file_path),
                    "collision_detected": collision_detected,
                    "expected_checksum": expected_checksum,
                    "current_checksum": current_checksum,
                }
            )
        except Exception as e:
            return self._error(f"Failed to check for collision on {file_path}: {e}")
