"""
Zen MCP Tool: Content Memory Validator
Validates content memory against filesystem truth to prevent contamination
Fixes TICKET-030 triple collision bug
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import Field
from datetime import datetime

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from .simple.base import SimpleTool

# Import content memory validator
sys.path.insert(0, str(Path(__file__).parent.parent))
from content_memory_validator import ContentMemoryValidator, MemoryConflict

FIELD_DESCRIPTIONS = {
    "action": "Action: store, retrieve, validate, health_check, resolve_conflict",
    "identifier": "Identifier to validate (e.g., TICKET-030, ISSUE-123)",
    "concept_summary": "Brief summary of what this identifier represents",
    "content": "Full content for hash calculation and validation",
    "file_path": "Absolute path to source file for validation",
    "session_id": "Session ID that created this memory",
    "validate_filesystem": "Whether to validate against filesystem (default: true)",
    "force_update": "Force update memory from filesystem even if not stale",
}


class MemoryValidatorRequest(ToolRequest):
    """Request model for Memory Validator tool"""

    action: str = Field(description=FIELD_DESCRIPTIONS["action"])
    identifier: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["identifier"])
    concept_summary: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["concept_summary"])
    content: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["content"])
    file_path: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["file_path"])
    session_id: Optional[str] = Field("default", description=FIELD_DESCRIPTIONS["session_id"])
    validate_filesystem: bool = Field(True, description=FIELD_DESCRIPTIONS["validate_filesystem"])
    force_update: bool = Field(False, description=FIELD_DESCRIPTIONS["force_update"])


class MemoryValidatorTool(SimpleTool):
    """
    Content Memory Validator - Prevents persistent memory contamination

    This tool validates content memory against filesystem truth to prevent the
    TICKET-030 triple collision bug where multiple competing memories exist
    for the same identifier.

    Features:
    - Detects stale memories (file newer than memory)
    - Identifies conflicts (multiple concepts for same ID)
    - Validates against filesystem as source of truth
    - Provides health checks and recommendations
    """

    def get_name(self) -> str:
        return "memory_validator"

    def get_description(self) -> str:
        return "Validates content memory against filesystem truth to prevent contamination"

    def get_system_prompt(self) -> str:
        return """You are a content memory validation system that prevents persistent memory contamination.

Your role is to:
1. Validate memories against filesystem truth
2. Detect and report conflicts (multiple concepts for same ID)
3. Identify stale memories (file newer than memory)
4. Recommend resolution actions
5. Maintain memory health and integrity

CRITICAL PRINCIPLE: Filesystem is ALWAYS source of truth. Memory is a cache for performance.

When conflicts are detected:
- ALWAYS warn the user
- ALWAYS show competing concepts
- ALWAYS recommend using filesystem state
- NEVER silently overwrite real work with stale memory"""

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """Return tool-specific field definitions"""
        return {
            "action": {
                "type": "string",
                "description": "Action to perform: store, retrieve, validate, health_check, resolve_conflict",
                "enum": ["store", "retrieve", "validate", "health_check", "resolve_conflict"]
            },
            "identifier": {
                "type": "string",
                "description": "Identifier to validate (e.g., TICKET-030, ISSUE-123)"
            },
            "concept_summary": {
                "type": "string",
                "description": "Brief summary of what this identifier represents"
            },
            "content": {
                "type": "string",
                "description": "Full content for hash calculation and validation"
            },
            "file_path": {
                "type": "string",
                "description": "Absolute path to source file for validation"
            },
            "session_id": {
                "type": "string",
                "description": "Session ID that created this memory",
                "default": "default"
            },
            "validate_filesystem": {
                "type": "boolean",
                "description": "Whether to validate against filesystem (default: true)",
                "default": True
            },
            "force_update": {
                "type": "boolean",
                "description": "Force update memory from filesystem even if not stale",
                "default": False
            }
        }

    def prepare_prompt(self, request: MemoryValidatorRequest, **kwargs) -> str:
        """Prepare the prompt for memory validation"""

        if request.action == "store":
            return f"""Store content memory for validation.

Identifier: {request.identifier}
Concept: {request.concept_summary}
File Path: {request.file_path or 'N/A'}
Session: {request.session_id}

This will:
1. Store memory with current timestamp
2. Detect conflicts with existing memories
3. Calculate content hash for validation
4. Record file modification time if file exists
5. Warn if competing memories exist

Execute memory storage with conflict detection."""

        elif request.action == "retrieve":
            return f"""Retrieve and validate memory.

Identifier: {request.identifier}
Validate Filesystem: {request.validate_filesystem}

This will:
1. Retrieve most recent memory
2. Check for competing memories (conflicts)
3. Validate against filesystem if file exists
4. Compare file mtime vs memory timestamp
5. Mark as stale if file is newer
6. Warn about any conflicts detected

Execute memory retrieval with validation."""

        elif request.action == "validate":
            return f"""Validate existing memory against filesystem.

Identifier: {request.identifier}
Force Update: {request.force_update}

This will:
1. Check if file exists at recorded path
2. Compare file modification time vs memory timestamp
3. Calculate current content hash
4. Detect if content has changed
5. Recommend update if stale or changed

Execute memory validation check."""

        elif request.action == "health_check":
            return f"""Perform memory health check.

This will:
1. Count total memories and stale memories
2. Detect identifiers with multiple memories
3. Identify conflicts (different concepts, same ID)
4. Calculate memory health score (0-100)
5. Provide recommendations for cleanup

Execute memory health check."""

        elif request.action == "resolve_conflict":
            return f"""Resolve memory conflict for identifier.

Identifier: {request.identifier}

This will:
1. Get all competing memories
2. Check filesystem state (source of truth)
3. Recommend resolution action
4. Update memory from filesystem if file exists
5. Mark old memories as stale

Execute conflict resolution."""

        return f"Unknown action: {request.action}"

    async def _call(self, request: MemoryValidatorRequest, **kwargs) -> Dict[str, Any]:
        """Execute the memory validation logic"""

        try:
            # Initialize validator
            db_path = os.path.join(os.path.expanduser("~"), ".zen-mcp", "content_memory.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

            validator = ContentMemoryValidator(db_path)

            # Execute based on action
            if request.action == "store":
                return await self._store_memory(request, validator)
            elif request.action == "retrieve":
                return await self._retrieve_memory(request, validator)
            elif request.action == "validate":
                return await self._validate_memory(request, validator)
            elif request.action == "health_check":
                return await self._health_check(request, validator)
            elif request.action == "resolve_conflict":
                return await self._resolve_conflict(request, validator)
            else:
                return {"success": False, "error": f"Unknown action: {request.action}"}

        except Exception as e:
            return {"success": False, "error": f"Memory validator error: {str(e)}"}

    async def _store_memory(self, request: MemoryValidatorRequest, validator: ContentMemoryValidator) -> Dict[str, Any]:
        """Store memory with conflict detection"""

        if not all([request.identifier, request.concept_summary, request.content]):
            return {"success": False, "error": "identifier, concept_summary, and content required"}

        memory = validator.store_memory(
            identifier=request.identifier,
            concept_summary=request.concept_summary,
            content=request.content,
            file_path=request.file_path,
            session_id=request.session_id
        )

        return {
            "success": True,
            "action": "store",
            "identifier": memory.identifier,
            "concept": memory.concept_summary,
            "timestamp": memory.memory_timestamp,
            "conflict_count": memory.conflict_count,
            "warning": f"⚠️ {memory.conflict_count} competing memories exist" if memory.conflict_count > 0 else None
        }

    async def _retrieve_memory(self, request: MemoryValidatorRequest, validator: ContentMemoryValidator) -> Dict[str, Any]:
        """Retrieve and validate memory"""

        if not request.identifier:
            return {"success": False, "error": "identifier required"}

        memory, conflict = validator.retrieve_memory(
            identifier=request.identifier,
            validate_filesystem=request.validate_filesystem
        )

        if not memory:
            return {
                "success": True,
                "action": "retrieve",
                "identifier": request.identifier,
                "found": False,
                "message": f"No memory found for {request.identifier}"
            }

        result = {
            "success": True,
            "action": "retrieve",
            "identifier": memory.identifier,
            "found": True,
            "concept": memory.concept_summary,
            "timestamp": memory.memory_timestamp,
            "session": memory.session_id,
            "is_stale": memory.is_stale,
            "file_path": memory.file_path,
            "file_mtime": memory.file_mtime
        }

        if conflict:
            result["conflict"] = {
                "severity": conflict.severity,
                "competing_count": len(conflict.competing_memories),
                "recommended_action": conflict.recommended_action,
                "concepts": [m.concept_summary for m in conflict.competing_memories],
                "warning": f"🔴 {conflict.severity.upper()} CONFLICT: {len(conflict.competing_memories)} competing memories"
            }

        if memory.is_stale:
            result["warning"] = f"⚠️ STALE MEMORY: File modified after memory stored (file: {memory.file_mtime}, memory: {memory.memory_timestamp})"

        return result

    async def _validate_memory(self, request: MemoryValidatorRequest, validator: ContentMemoryValidator) -> Dict[str, Any]:
        """Validate memory against filesystem"""

        if not request.identifier:
            return {"success": False, "error": "identifier required"}

        # Retrieve with validation
        memory, conflict = validator.retrieve_memory(request.identifier, validate_filesystem=True)

        if not memory:
            return {
                "success": True,
                "action": "validate",
                "identifier": request.identifier,
                "found": False,
                "message": "No memory to validate"
            }

        validation_result = {
            "success": True,
            "action": "validate",
            "identifier": memory.identifier,
            "concept": memory.concept_summary,
            "is_valid": not memory.is_stale and not conflict,
            "is_stale": memory.is_stale,
            "has_conflict": conflict is not None
        }

        if memory.is_stale:
            validation_result["recommendation"] = "UPDATE_MEMORY_FROM_FILESYSTEM"
            validation_result["reason"] = f"File modified at {memory.file_mtime}, memory from {memory.memory_timestamp}"

        if conflict:
            validation_result["conflict_details"] = {
                "severity": conflict.severity,
                "competing_memories": len(conflict.competing_memories),
                "recommended_action": conflict.recommended_action
            }

        return validation_result

    async def _health_check(self, request: MemoryValidatorRequest, validator: ContentMemoryValidator) -> Dict[str, Any]:
        """Perform memory health check"""

        health = validator.health_check()

        return {
            "success": True,
            "action": "health_check",
            "total_memories": health['total_memories'],
            "stale_memories": health['stale_memories'],
            "conflicts_detected": health['conflicts_detected'],
            "health_score": health['health_score'],
            "status": self._get_health_status(health['health_score']),
            "conflicts": health['conflicts'],
            "recommendations": self._generate_health_recommendations(health)
        }

    async def _resolve_conflict(self, request: MemoryValidatorRequest, validator: ContentMemoryValidator) -> Dict[str, Any]:
        """Resolve memory conflict"""

        if not request.identifier:
            return {"success": False, "error": "identifier required"}

        memories = validator.get_memories(request.identifier)

        if len(memories) <= 1:
            return {
                "success": True,
                "action": "resolve_conflict",
                "identifier": request.identifier,
                "message": "No conflict - only one memory exists"
            }

        # Get filesystem state
        file_path = next((m.file_path for m in memories if m.file_path), None)
        filesystem_concept = None

        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Read first few lines for concept detection
                    lines = content.split('\n')[:10]
                    for line in lines:
                        if line.strip() and not line.startswith('#'):
                            filesystem_concept = line.strip()[:100]
                            break
            except Exception as e:
                pass

        return {
            "success": True,
            "action": "resolve_conflict",
            "identifier": request.identifier,
            "competing_memories": len(memories),
            "concepts": [
                {
                    "concept": m.concept_summary,
                    "session": m.session_id,
                    "timestamp": m.memory_timestamp,
                    "is_stale": m.is_stale
                }
                for m in memories
            ],
            "filesystem_state": {
                "exists": file_path and os.path.exists(file_path),
                "path": file_path,
                "concept": filesystem_concept
            },
            "recommendation": "USE_FILESYSTEM_AS_SOURCE_OF_TRUTH" if file_path and os.path.exists(file_path) else "USE_MOST_RECENT_MEMORY",
            "action_required": "Update memory from filesystem or manually resolve"
        }

    def _get_health_status(self, score: int) -> str:
        """Get health status from score"""
        if score >= 90:
            return "✅ EXCELLENT"
        elif score >= 70:
            return "⚠️ GOOD"
        elif score >= 50:
            return "⚠️ WARNING"
        else:
            return "🔴 CRITICAL"

    def _generate_health_recommendations(self, health: Dict[str, Any]) -> list:
        """Generate health recommendations"""
        recommendations = []

        if health['stale_memories'] > 0:
            recommendations.append(
                f"Update {health['stale_memories']} stale memories from filesystem"
            )

        if health['conflicts_detected'] > 0:
            recommendations.append(
                f"Resolve {health['conflicts_detected']} conflicts by using filesystem as source of truth"
            )

        if health['health_score'] < 50:
            recommendations.append(
                "CRITICAL: Perform full memory cleanup and validation"
            )

        if not recommendations:
            recommendations.append("No action required - memory system is healthy")

        return recommendations
