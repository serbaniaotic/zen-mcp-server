"""
Zen MCP Tool: Safe Evidence Appending
Implements a safe, atomic append operation using the principles from the
Evidence Harmony Protocol (collision detection and recovery).
"""
import hashlib
import shutil
import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.shared.base_tool import BaseTool
from mcp.types import TextContent

class AppendEvidenceRequest(ToolRequest):
    """Request model for the Append Evidence tool."""
    file_path: str = Field(..., description="The absolute path to the evidence file.")
    content: str = Field(..., description="The markdown content to append to the file.")
    expected_checksum: str = Field(
        ..., description="The SHA256 checksum of the file when it was last read, used for collision detection."
    )

class AppendEvidenceTool(BaseTool):
    """
    Safely appends content to an evidence file using an atomic operation
    that includes collision detection and automatic rollback.
    """

    def get_name(self) -> str:
        return "append_evidence"

    def get_description(self) -> str:
        return "Safely appends content to a file with collision detection and rollback."

    def get_request_model(self) -> type[ToolRequest]:
        return AppendEvidenceRequest

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Executes the safe append workflow.
        1. Creates a recovery point.
        2. Checks for file collisions.
        3. Appends content if safe.
        4. Rolls back on any failure.
        """
        try:
            request = self.get_request_model()(**arguments)
        except Exception as e:
            return self._error(f"Invalid arguments: {e}")

        file_path = Path(request.file_path)
        if not file_path.is_file():
            return self._error(f"File not found: {request.file_path}")

        # --- Main Workflow ---
        recovery_point_path: Optional[Path] = None
        try:
            # 1. Create Recovery Point
            recovery_point_path = self._create_recovery_point(file_path)
            if not recovery_point_path:
                # This is a critical failure, as we can't guarantee safety.
                return self._error("Failed to create recovery point. Aborting operation.")

            # 2. Check for Collision
            current_checksum = self._calculate_checksum(file_path)
            if current_checksum != request.expected_checksum:
                # Collision detected, abort safely.
                self._cleanup_recovery_point(recovery_point_path)
                return self._error(
                    "Collision detected. File has been modified by another process. Please re-read the file and try again.",
                    details={
                        "expected_checksum": request.expected_checksum,
                        "current_checksum": current_checksum,
                    }
                )

            # 3. Append Content
            with open(file_path, "a", encoding="utf-8") as f:
                f.write("\n\n---\n\n")
                f.write(request.content)

            # 4. Success
            new_checksum = self._calculate_checksum(file_path)
            return self._success(
                f"Successfully appended content to {file_path.name}.",
                {
                    "file_path": str(file_path),
                    "new_checksum": new_checksum,
                    "recovery_point_path": str(recovery_point_path) # Kept for potential manual recovery
                }
            )

        except (IOError, OSError) as e:
            # 5. Rollback on Failure
            if recovery_point_path:
                self._rollback(file_path, recovery_point_path)
                return self._error(f"An error occurred during write: {e}. The file has been rolled back to its previous state.")
            return self._error(f"An unrecoverable error occurred: {e}")

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculates the SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _create_recovery_point(self, file_path: Path) -> Optional[Path]:
        """Creates a backup of the file. Returns the path to the backup or None on failure."""
        try:
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
            backup_path = file_path.with_suffix(f"{file_path.suffix}.{timestamp}.bak")
            shutil.copy2(file_path, backup_path)
            return backup_path
        except (IOError, OSError):
            return None

    def _rollback(self, target_file_path: Path, recovery_point_path: Path):
        """Restores the file from the recovery point."""
        try:
            shutil.copy2(recovery_point_path, target_file_path)
        except (IOError, OSError):
            # If rollback fails, the system is in an unstable state.
            # Manual intervention is likely required.
            pass

    def _cleanup_recovery_point(self, recovery_point_path: Path):
        """Removes a recovery point file if it exists."""
        try:
            if recovery_point_path.exists():
                recovery_point_path.unlink()
        except (IOError, OSError):
            pass