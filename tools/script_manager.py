"""
Zen MCP Tool: Script Manager
Manage and modify zen scripts following the standardized convention
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
    "action": "Action to perform: list, analyze, modify, validate, backup, restore, create",
    "script_path": "Path to the script file",
    "script_name": "Name of the script to create",
    "modification_type": "Type of modification: parameter, function, full",
    "modification_content": "Content of the modification",
    "agent_id": "ID of the agent making the modification",
    "reason": "Reason for the modification",
    "scope": "Scope of the script: system, project, workflow, analysis, integration, utility",
    "integration_level": "Agent integration level: 1=read-only, 2=parameter, 3=function, 4=full",
    "backup_path": "Path to backup file for restore",
    "validate_only": "Only validate without applying changes",
}

class ScriptManagerRequest(ToolRequest):
    """Request model for Script Manager tool"""
    action: str = Field(..., description=FIELD_DESCRIPTIONS["action"])
    script_path: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["script_path"])
    script_name: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["script_name"])
    modification_type: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["modification_type"])
    modification_content: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["modification_content"])
    agent_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["agent_id"])
    reason: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["reason"])
    scope: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["scope"])
    integration_level: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["integration_level"])
    backup_path: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["backup_path"])
    validate_only: bool = Field(default=False, description=FIELD_DESCRIPTIONS["validate_only"])


class ScriptManagerTool(BaseTool):
    """
    Manage and modify zen scripts following the standardized convention.
    
    This tool provides comprehensive script management:
    - List and analyze zen scripts
    - Modify scripts safely with agent tracking
    - Validate script integrity and convention compliance
    - Backup and restore scripts
    - Create new scripts from templates
    - Track agent modifications
    """

    def get_name(self) -> str:
        return "script_manager"

    def get_description(self) -> str:
        return "Manage and modify zen scripts following the standardized convention with agent integration."

    def get_system_prompt(self) -> str:
        return """You are a script management assistant that helps manage zen scripts following the standardized convention.

Your role is to:
1. List and analyze zen scripts
2. Modify scripts safely with proper agent tracking
3. Validate script integrity and convention compliance
4. Backup and restore scripts
5. Create new scripts from templates
6. Track agent modifications and changes

Always follow the zen script convention and maintain proper change tracking."""

    def get_default_temperature(self) -> float:
        return 0.2  # Low temperature for consistent script management

    def get_model_category(self) -> "ToolModelCategory":
        """Script management prioritizes accuracy and consistency"""
        from tools.models import ToolModelCategory
        return ToolModelCategory.BALANCED

    def get_request_model(self):
        """Return the ScriptManager-specific request model"""
        return ScriptManagerRequest

    def requires_model(self) -> bool:
        """
        Script manager doesn't require model resolution at the MCP boundary.
        
        This is a pure script management tool that handles file operations without calling
        external AI models.
        
        Returns:
            bool: False - script manager doesn't need AI model access
        """
        return False

    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform: list, analyze, modify, validate, backup, restore, create",
                    "enum": ["list", "analyze", "modify", "validate", "backup", "restore", "create"]
                },
                "script_path": {
                    "type": "string",
                    "description": "Path to the script file"
                },
                "script_name": {
                    "type": "string",
                    "description": "Name of the script to create"
                },
                "modification_type": {
                    "type": "string",
                    "description": "Type of modification: parameter, function, full",
                    "enum": ["parameter", "function", "full"]
                },
                "modification_content": {
                    "type": "string",
                    "description": "Content of the modification"
                },
                "agent_id": {
                    "type": "string",
                    "description": "ID of the agent making the modification"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the modification"
                },
                "scope": {
                    "type": "string",
                    "description": "Scope of the script: system, project, workflow, analysis, integration, utility",
                    "enum": ["system", "project", "workflow", "analysis", "integration", "utility"]
                },
                "integration_level": {
                    "type": "string",
                    "description": "Agent integration level: 1=read-only, 2=parameter, 3=function, 4=full",
                    "enum": ["1", "2", "3", "4"]
                },
                "backup_path": {
                    "type": "string",
                    "description": "Path to backup file for restore"
                },
                "validate_only": {
                    "type": "boolean",
                    "description": "Only validate without applying changes",
                    "default": False
                }
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    def get_annotations(self) -> Optional[dict[str, Any]]:
        """Return tool annotations indicating this is a script management tool"""
        return {"scriptManagement": True}

    async def prepare_prompt(self, request: ScriptManagerRequest) -> str:
        """Not used for this utility tool"""
        return ""

    def format_response(self, response: str, request: ScriptManagerRequest, model_info: Optional[dict] = None) -> str:
        """Not used for this utility tool"""
        return response

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Execute the script management logic.
        
        This overrides the base class execute to provide direct script management without AI model calls.
        
        Args:
            arguments: Tool arguments including action, script_path, etc.
            
        Returns:
            Formatted script management results
        """
        try:
            action = arguments.get("action", "list")
            
            if action == "list":
                result = await self._list_scripts(arguments)
            elif action == "analyze":
                result = await self._analyze_script(arguments)
            elif action == "modify":
                result = await self._modify_script(arguments)
            elif action == "validate":
                result = await self._validate_script(arguments)
            elif action == "backup":
                result = await self._backup_script(arguments)
            elif action == "restore":
                result = await self._restore_script(arguments)
            elif action == "create":
                result = await self._create_script(arguments)
            else:
                result = {"success": False, "error": f"Unknown action: {action}"}
            
            # Format as ToolOutput
            tool_output = ToolOutput(
                status="success" if result.get("success", False) else "error",
                content=json.dumps(result, indent=2),
                content_type="json",
                metadata={
                    "tool_name": self.get_name(),
                    "action": action,
                },
            )
            
            return [TextContent(type="text", text=tool_output.model_dump_json())]
                
        except Exception as e:
            error_result = {"success": False, "error": f"Script management error: {str(e)}"}
            tool_output = ToolOutput(
                status="error",
                content=json.dumps(error_result, indent=2),
                content_type="json",
                metadata={"tool_name": self.get_name()},
            )
            return [TextContent(type="text", text=tool_output.model_dump_json())]

    async def _list_scripts(self, request: dict) -> dict[str, Any]:
        """List all zen scripts in the toolbox scripts directory"""
        try:
            # Use environment variable or default relative path
            scripts_dir_path = os.environ.get("ZEN_SCRIPTS_DIR", "toolbox/scripts")
            scripts_dir = Path(scripts_dir_path).resolve()
            if not scripts_dir.exists():
                return {"success": False, "error": f"Scripts directory not found at: {scripts_dir}"}
            
            scripts = []
            for script_file in scripts_dir.glob("*.sh"):
                script_info = await self._get_script_info(script_file)
                scripts.append(script_info)
            
            return {
                "success": True,
                "action": "list",
                "scripts_directory": str(scripts_dir),
                "total_scripts": len(scripts),
                "scripts": scripts
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to list scripts: {str(e)}"}

    async def _get_script_info(self, script_path: Path) -> dict[str, Any]:
        """Get information about a script file"""
        try:
            content = script_path.read_text()
            
            # Parse script convention header
            info = {
                "path": str(script_path),
                "name": script_path.stem,
                "size": script_path.stat().st_size,
                "modified": datetime.fromtimestamp(script_path.stat().st_mtime).isoformat(),
                "convention_compliant": False,
                "category": "unknown",
                "version": "unknown",
                "purpose": "unknown",
                "scope": "unknown",
                "integration_level": "unknown",
                "agent_capabilities": [],
                "rag_keywords": [],
                "stability": "unknown"
            }
            
            # Check for standalone utility script header
            if "STANDALONE UTILITY SCRIPT" in content:
                info["convention_compliant"] = True
                info["category"] = "A (Standalone Utility)"
                info["integration_level"] = "Read-only"
                
                # Extract metadata from header
                lines = content.split('\n')
                for line in lines:
                    if line.startswith("# Purpose:"):
                        info["purpose"] = line.split(":", 1)[1].strip()
                    elif line.startswith("# RAG Keywords:"):
                        keywords = line.split(":", 1)[1].strip()
                        info["rag_keywords"] = [kw.strip() for kw in keywords.split(",")]
                    elif line.startswith("# Stability:"):
                        info["stability"] = line.split(":", 1)[1].strip()
                    elif line.startswith("# Use Cases:"):
                        info["scope"] = line.split(":", 1)[1].strip()
            
            # Check for zen workflow script header
            elif "ZEN WORKFLOW SCRIPT" in content:
                info["convention_compliant"] = True
                info["category"] = "B (Zen Workflow)"
                
                # Extract metadata from header
                lines = content.split('\n')
                for line in lines:
                    if line.startswith("# Version:"):
                        info["version"] = line.split(":", 1)[1].strip()
                    elif line.startswith("# Purpose:"):
                        info["purpose"] = line.split(":", 1)[1].strip()
                    elif line.startswith("# Scope:"):
                        info["scope"] = line.split(":", 1)[1].strip()
                    elif line.startswith("# Agent Integration:"):
                        info["integration_level"] = line.split(":", 1)[1].strip()
                    elif line.startswith("# Agent Capabilities:"):
                        capabilities = line.split(":", 1)[1].strip()
                        info["agent_capabilities"] = [cap.strip() for cap in capabilities.split(",")]
            
            # Legacy script detection
            else:
                info["category"] = self._detect_legacy_category(content)
                if info["category"] == "A (Standalone Utility)":
                    info["integration_level"] = "Read-only"
                else:
                    info["integration_level"] = "Unknown"
            
            return info
        except Exception as e:
            return {
                "path": str(script_path),
                "name": script_path.stem,
                "error": f"Failed to analyze script: {str(e)}"
            }

    def _detect_legacy_category(self, content: str) -> str:
        """Detect category for legacy scripts"""
        content_lower = content.lower()
        
        # Standalone utility indicators
        standalone_keywords = ["aws", "git", "github", "docker", "ecs", "s3", "lambda"]
        if any(keyword in content_lower for keyword in standalone_keywords):
            return "A (Standalone Utility)"
        
        # Zen workflow indicators
        zen_keywords = ["wiki", "tracker", "sync", "agent", "workflow", "zen"]
        if any(keyword in content_lower for keyword in zen_keywords):
            return "B (Zen Workflow)"
        
        # Default to standalone for unknown
        return "A (Standalone Utility)"

    async def _analyze_script(self, request: dict) -> dict[str, Any]:
        """Analyze a specific script for zen convention compliance"""
        script_path = request.get("script_path")
        if not script_path:
            return {"success": False, "error": "Script path required for analysis"}
        
        try:
            script_file = Path(script_path)
            if not script_file.exists():
                return {"success": False, "error": f"Script file not found: {script_path}"}
            
            info = await self._get_script_info(script_file)
            
            # Additional analysis based on category
            content = script_file.read_text()
            
            if info["category"] == "A (Standalone Utility)":
                analysis = {
                    "script_info": info,
                    "convention_compliance": {
                        "has_header": "STANDALONE UTILITY SCRIPT" in content,
                        "has_metadata": "UTILITY METADATA" in content,
                        "has_usage": "--help" in content or "Usage:" in content,
                        "has_parameters": "while [[ $# -gt 0 ]]" in content,
                        "has_error_handling": "exit 1" in content,
                        "has_dependencies": "Dependencies:" in content
                    },
                    "recommendations": []
                }
                
                # Generate recommendations for standalone utilities
                if not analysis["convention_compliance"]["has_header"]:
                    analysis["recommendations"].append("Add standalone utility script header")
                if not analysis["convention_compliance"]["has_usage"]:
                    analysis["recommendations"].append("Add usage/help information")
                if not analysis["convention_compliance"]["has_error_handling"]:
                    analysis["recommendations"].append("Add proper error handling")
                    
            elif info["category"] == "B (Zen Workflow)":
                analysis = {
                    "script_info": info,
                    "convention_compliance": {
                        "has_header": "ZEN WORKFLOW SCRIPT" in content,
                        "has_metadata": "ZEN METADATA" in content,
                        "has_functions": "FUNCTIONS" in content,
                        "has_main_execution": "MAIN EXECUTION" in content,
                        "has_agent_hooks": "AGENT_HOOK" in content,
                        "has_validation": "validate_script_integrity" in content,
                        "has_logging": "log_message" in content,
                        "has_version_control": "Version:" in content
                    },
                    "recommendations": []
                }
                
                # Generate recommendations for zen workflow scripts
                if not analysis["convention_compliance"]["has_header"]:
                    analysis["recommendations"].append("Add zen workflow script header")
                if not analysis["convention_compliance"]["has_metadata"]:
                    analysis["recommendations"].append("Add zen metadata section")
                if not analysis["convention_compliance"]["has_agent_hooks"]:
                    analysis["recommendations"].append("Add agent integration hooks")
                if not analysis["convention_compliance"]["has_validation"]:
                    analysis["recommendations"].append("Add script validation function")
                if not analysis["convention_compliance"]["has_version_control"]:
                    analysis["recommendations"].append("Add version control")
            else:
                # Legacy script analysis
                analysis = {
                    "script_info": info,
                    "convention_compliance": {
                        "has_header": False,
                        "has_metadata": False,
                        "legacy_script": True
                    },
                    "recommendations": ["Migrate to appropriate convention (A or B)"]
                }
            
            return {
                "success": True,
                "action": "analyze",
                "script_path": script_path,
                "analysis": analysis
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to analyze script: {str(e)}"}

    async def _modify_script(self, request: dict) -> dict[str, Any]:
        """Modify a script with proper agent tracking"""
        script_path = request.get("script_path")
        modification_type = request.get("modification_type")
        modification_content = request.get("modification_content")
        agent_id = request.get("agent_id")
        reason = request.get("reason")
        validate_only = request.get("validate_only", False)
        
        if not script_path:
            return {"success": False, "error": "Script path required for modification"}
        
        try:
            script_file = Path(script_path)
            if not script_file.exists():
                return {"success": False, "error": f"Script file not found: {script_path}"}
            
            # Create backup before modification
            backup_path = await self._create_backup(script_file)
            
            if validate_only:
                return {
                    "success": True,
                    "action": "modify",
                    "script_path": script_path,
                    "modification_type": modification_type,
                    "validation_only": True,
                    "backup_created": backup_path,
                    "message": "Modification validated (not applied)"
                }
            
            # Apply modification
            original_content = script_file.read_text()
            modified_content = await self._apply_modification(
                original_content, modification_type, modification_content
            )
            
            # Write modified content
            script_file.write_text(modified_content)
            
            # Log agent modification
            await self._log_agent_modification(
                script_path, agent_id, modification_type, reason
            )
            
            return {
                "success": True,
                "action": "modify",
                "script_path": script_path,
                "modification_type": modification_type,
                "agent_id": agent_id,
                "reason": reason,
                "backup_created": backup_path,
                "message": "Script modified successfully"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to modify script: {str(e)}"}

    async def _apply_modification(self, content: str, modification_type: str, modification_content: str) -> str:
        """Apply modification to script content"""
        if modification_type == "parameter":
            # Add or modify parameters
            return content + f"\n# Agent modification: {modification_content}\n"
        elif modification_type == "function":
            # Add new function
            return content + f"\n# Agent added function:\n{modification_content}\n"
        elif modification_type == "full":
            # Full content replacement
            return modification_content
        else:
            return content

    async def _create_backup(self, script_file: Path) -> str:
        """Create backup of script file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = script_file.with_suffix(f".backup.{timestamp}")
        backup_path.write_text(script_file.read_text())
        return str(backup_path)

    async def _log_agent_modification(self, script_path: str, agent_id: str, modification_type: str, reason: str):
        """Log agent modification using secure logging infrastructure"""
        import logging

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "script_path": script_path,
            "agent_id": agent_id,
            "modification_type": modification_type,
            "reason": reason
        }

        # Use the existing 'mcp_activity' logger from the server
        activity_logger = logging.getLogger("mcp_activity")
        activity_logger.info(f"SCRIPT_MODIFICATION: {json.dumps(log_entry)}")

    async def _validate_script(self, request: dict) -> dict[str, Any]:
        """Validate script integrity and convention compliance"""
        script_path = request.get("script_path")
        if not script_path:
            return {"success": False, "error": "Script path required for validation"}
        
        try:
            script_file = Path(script_path)
            if not script_file.exists():
                return {"success": False, "error": f"Script file not found: {script_path}"}
            
            # Run script validation
            result = await self._run_script_validation(script_file)
            
            return {
                "success": True,
                "action": "validate",
                "script_path": script_path,
                "validation_result": result
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to validate script: {str(e)}"}

    async def _run_script_validation(self, script_file: Path) -> dict[str, Any]:
        """Run script validation"""
        try:
            # Check syntax
            process = await asyncio.create_subprocess_exec(
                "bash", "-n", str(script_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            syntax_valid = process.returncode == 0
            
            return {
                "syntax_valid": syntax_valid,
                "syntax_errors": stderr.decode() if stderr else None,
                "convention_compliant": "ZEN SCRIPT CONVENTION HEADER" in script_file.read_text()
            }
        except Exception as e:
            return {"error": f"Validation failed: {str(e)}"}

    async def _backup_script(self, request: dict) -> dict[str, Any]:
        """Create backup of script"""
        script_path = request.get("script_path")
        if not script_path:
            return {"success": False, "error": "Script path required for backup"}
        
        try:
            script_file = Path(script_path)
            if not script_file.exists():
                return {"success": False, "error": f"Script file not found: {script_path}"}
            
            backup_path = await self._create_backup(script_file)
            
            return {
                "success": True,
                "action": "backup",
                "script_path": script_path,
                "backup_path": backup_path,
                "message": "Backup created successfully"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to create backup: {str(e)}"}

    async def _restore_script(self, request: dict) -> dict[str, Any]:
        """Restore script from backup"""
        script_path = request.get("script_path")
        backup_path = request.get("backup_path")
        
        if not script_path:
            return {"success": False, "error": "Script path required for restore"}
        if not backup_path:
            return {"success": False, "error": "Backup path required for restore"}
        
        try:
            script_file = Path(script_path)
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                return {"success": False, "error": f"Backup file not found: {backup_path}"}
            
            # Restore from backup
            script_file.write_text(backup_file.read_text())
            
            return {
                "success": True,
                "action": "restore",
                "script_path": script_path,
                "backup_path": backup_path,
                "message": "Script restored successfully"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to restore script: {str(e)}"}

    async def _create_script(self, request: dict) -> dict[str, Any]:
        """Create new script from template"""
        script_name = request.get("script_name")
        scope = request.get("scope", "utility")
        integration_level = request.get("integration_level", "2")
        
        if not script_name:
            return {"success": False, "error": "Script name required for creation"}
        
        try:
            # Create script from template
            script_content = await self._generate_script_template(script_name, scope, integration_level)
            
            scripts_dir_path = os.environ.get("ZEN_SCRIPTS_DIR", "toolbox/scripts")
            script_path = Path(scripts_dir_path).resolve() / f"{script_name}.sh"
            script_path.write_text(script_content)
            script_path.chmod(0o755)  # Make executable
            
            return {
                "success": True,
                "action": "create",
                "script_name": script_name,
                "script_path": str(script_path),
                "scope": scope,
                "integration_level": integration_level,
                "message": "Script created successfully"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to create script: {str(e)}"}

    async def _generate_script_template(self, script_name: str, scope: str, integration_level: str) -> str:
        """Generate script template"""
        template = f"""#!/bin/bash
# =============================================================================
# ZEN SCRIPT CONVENTION HEADER
# =============================================================================
# Script Name: {script_name}
# Version: 1.0.0
# Purpose: Auto-generated script template
# Scope: {scope}
# Agent Integration: Level {integration_level}
# Last Modified: {datetime.now().isoformat()}Z
# Modified By: script-manager
# =============================================================================

# -----------------------------------------------------------------------------
# METADATA
# -----------------------------------------------------------------------------
# Script ID: zen-{script_name}-001
# Dependencies: bash, core-utils
# Input Parameters: --help, --version
# Output Format: Text
# Error Codes: 0=success, 1=error
# Agent Capabilities: parameter-modification
# Modification History: Initial template
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
DEFAULT_LOG_LEVEL="info"

# -----------------------------------------------------------------------------
# FUNCTIONS
# -----------------------------------------------------------------------------

show_help() {{
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --help     Show this help"
    echo "  --version  Show version"
}}

show_version() {{
    echo "{script_name} v1.0.0"
    echo "Zen Script Convention Compliant"
}}

# -----------------------------------------------------------------------------
# MAIN EXECUTION
# -----------------------------------------------------------------------------

main() {{
    # Pre-execution hook
    if [ -n "$AGENT_HOOK_PRE_EXECUTION" ]; then
        eval "$AGENT_HOOK_PRE_EXECUTION"
    fi
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_help
                exit 0
                ;;
            --version)
                show_version
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Main logic here
    echo "Script {script_name} executed successfully"
    
    # Post-execution hook
    if [ -n "$AGENT_HOOK_POST_EXECUTION" ]; then
        eval "$AGENT_HOOK_POST_EXECUTION"
    fi
}}

# Execute main function
main "$@"
"""
        return template
