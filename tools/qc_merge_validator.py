"""
QC Merge Validator Tool - Detect contradictions when loading multiple QCs

Analyzes multiple QC sessions to detect semantic contradictions, terminology drift,
and conflicting decisions. Provides resolution suggestions and builds vocabulary map.

Design: Day 6 Task-1 (qc-workflow-scripts)
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.shared.base_tool import BaseTool
from tools.models import ToolOutput
from mcp.types import TextContent

logger = logging.getLogger(__name__)


class QCMergeValidatorRequest(ToolRequest):
    """Request model for QC Merge Validator tool"""
    qc_ids: list[str] = Field(..., description="List of QC IDs to validate together (e.g., ['QC-002', 'QC-005'])")
    auto_resolve: Optional[bool] = Field(False, description="Auto-apply common resolution patterns (default: False)")
    update_vocab: Optional[bool] = Field(True, description="Update vocabulary map with findings (default: True)")


class QCMergeValidatorTool(BaseTool):
    """
    QC Merge Validator tool for detecting contradictions.
    
    Analyzes multiple QC sessions and detects:
    - Semantic contradictions
    - Terminology variations
    - Conflicting decisions
    - Pattern inconsistencies
    
    Does not require AI model calls - rule-based analysis.
    """
    
    def __init__(self):
        super().__init__()
        self.qc_dir = Path.home() / "code" / "qc"
        self.vocab_file = self.qc_dir / ".vocabulary_map.json"
        self.vocab_map = None
    
    def get_name(self) -> str:
        return "qc_merge_validator"
    
    def get_description(self) -> str:
        return (
            "Validate multiple QC sessions for contradictions, terminology conflicts, and decision inconsistencies. "
            "Use when loading multiple QCs to ensure coherent context. Returns detected conflicts and resolution suggestions."
        )
    
    def get_system_prompt(self) -> str:
        return """You are a QC merge validator.

Your role is to detect contradictions and inconsistencies when multiple QC sessions are loaded together.
Identify conflicts clearly and suggest resolutions."""
    
    def get_default_temperature(self) -> float:
        return 0.0  # Deterministic validation
    
    def get_model_category(self) -> "ToolModelCategory":
        from tools.models import ToolModelCategory
        return ToolModelCategory.FAST_RESPONSE
    
    def get_request_model(self):
        return QCMergeValidatorRequest
    
    def requires_model(self) -> bool:
        """Validation is rule-based, doesn't require AI model"""
        return False
    
    def get_input_schema(self) -> dict[str, Any]:
        """Return input schema for QC Merge Validator"""
        return {
            "type": "object",
            "properties": {
                "qc_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of QC IDs to validate together (e.g., ['QC-002', 'QC-005'])"
                },
                "auto_resolve": {
                    "type": "boolean",
                    "description": "Auto-apply common resolution patterns (default: False)",
                    "default": False
                },
                "update_vocab": {
                    "type": "boolean",
                    "description": "Update vocabulary map with findings (default: True)",
                    "default": True
                }
            },
            "required": ["qc_ids"]
        }
    
    async def prepare_prompt(
        self,
        arguments: dict[str, Any],
        system_prompts: list[str],
        conversation_history: Optional[list[dict[str, Any]]] = None
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Validator tool doesn't use AI model, so this is a no-op.
        Returns empty prompt and history.
        """
        return "", []
    
    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute QC merge validation"""
        
        qc_ids = arguments.get("qc_ids", [])
        auto_resolve = arguments.get("auto_resolve", False)
        update_vocab = arguments.get("update_vocab", True)
        
        if not qc_ids or len(qc_ids) < 2:
            error_output = ToolOutput(
                status="error",
                content="At least 2 QC IDs required for merge validation",
                content_type="text"
            )
            return [TextContent(type="text", text=error_output.model_dump_json())]
        
        try:
            # Load QC sessions
            sessions = await self._load_qc_sessions(qc_ids)
            
            if len(sessions) < 2:
                error_output = ToolOutput(
                    status="error",
                    content=f"Could not load sufficient QC sessions. Found {len(sessions)}, need at least 2.",
                    content_type="text"
                )
                return [TextContent(type="text", text=error_output.model_dump_json())]
            
            # Load vocabulary map
            await self._load_vocab_map()
            
            # Detect conflicts
            conflicts = await self._detect_conflicts(sessions)
            
            # Generate suggestions
            suggestions = await self._generate_suggestions(conflicts, sessions)
            
            # Update vocabulary map if requested
            if update_vocab and conflicts:
                await self._update_vocab_map(conflicts, sessions)
            
            # Format output
            output = self._format_validation_report(sessions, conflicts, suggestions)
            
            # Note: ToolOutput only accepts specific status values, so we use "success" even when conflicts exist
            # The conflicts are clearly communicated in the content/report
            result = ToolOutput(
                status="success",
                content=output,
                content_type="markdown"
            )
            
            return [TextContent(type="text", text=result.model_dump_json())]
            
        except Exception as e:
            logger.error(f"Error in QC merge validation: {e}", exc_info=True)
            error_output = ToolOutput(
                status="error",
                content=f"Validation failed: {str(e)}",
                content_type="text"
            )
            return [TextContent(type="text", text=error_output.model_dump_json())]
    
    async def _load_qc_sessions(self, qc_ids: list[str]) -> list[dict[str, Any]]:
        """Load QC session files"""
        
        sessions = []
        
        for qc_id in qc_ids:
            try:
                # Find QC file (could be in any date folder)
                qc_files = list(self.qc_dir.rglob(f"{qc_id}-*.md"))
                
                if not qc_files:
                    logger.warning(f"QC session not found: {qc_id}")
                    continue
                
                qc_file = qc_files[0]
                content = qc_file.read_text(encoding='utf-8')
                
                # Parse YAML header
                if not content.startswith('---'):
                    logger.warning(f"QC file has no YAML header: {qc_file}")
                    continue
                
                parts = content.split('---', 2)
                if len(parts) < 3:
                    logger.warning(f"QC file has invalid format: {qc_file}")
                    continue
                
                frontmatter = parts[1]
                body = parts[2]
                
                # Parse metadata
                metadata = {'id': qc_id, 'file': str(qc_file), 'body': body}
                
                for line in frontmatter.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip().strip('"')
                        
                        if key in ['id', 'date', 'time', 'duration', 'type', 'action', 'outcome', 'status', 'context']:
                            metadata[key] = value
                
                # Extract title
                title = "Untitled"
                for line in body.split('\n'):
                    if line.startswith('# '):
                        title = line[2:].strip()
                        if ':' in title:
                            title = title.split(':', 1)[1].strip()
                        break
                
                metadata['title'] = title
                
                # Extract key sections
                metadata['insights'] = self._extract_section(body, '## Insights')
                metadata['anchors'] = self._extract_section(body, '## Anchors')
                metadata['decisions'] = self._extract_section(body, '## Discussion Notes')
                
                sessions.append(metadata)
                
            except Exception as e:
                logger.error(f"Failed to load {qc_id}: {e}")
                continue
        
        return sessions
    
    def _extract_section(self, body: str, section_header: str) -> str:
        """Extract a markdown section"""
        
        if section_header not in body:
            return ""
        
        section = body.split(section_header, 1)[1]
        section = section.split('##', 1)[0]
        return section.strip()
    
    async def _load_vocab_map(self) -> None:
        """Load vocabulary map from disk"""
        
        if self.vocab_file.exists():
            try:
                data = json.loads(self.vocab_file.read_text(encoding='utf-8'))
                self.vocab_map = data.get('vocabulary', {})
            except Exception as e:
                logger.warning(f"Failed to load vocabulary map: {e}")
                self.vocab_map = {}
        else:
            self.vocab_map = {}
    
    async def _detect_conflicts(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect conflicts between QC sessions"""
        
        conflicts = []
        
        # Check for type conflicts
        types = [(s['id'], s.get('type', 'unknown')) for s in sessions]
        if len(set(t for _, t in types)) > 1:
            conflicts.append({
                'type': 'type_mismatch',
                'severity': 'low',
                'description': f"Mixed QC types: {', '.join(f'{id}={type}' for id, type in types)}",
                'sessions': [id for id, _ in types]
            })
        
        # Check for status conflicts
        statuses = [(s['id'], s.get('status', 'unknown')) for s in sessions]
        # Flag if mixing completed/actioned with thinking
        thinking = [id for id, status in statuses if status == 'thinking']
        actioned = [id for id, status in statuses if status in ['actioned', 'dead-end', 'offline']]
        
        if thinking and actioned:
            conflicts.append({
                'type': 'status_conflict',
                'severity': 'medium',
                'description': f"Mixing active thinking sessions with completed/closed sessions",
                'sessions': thinking + actioned,
                'details': {
                    'thinking': thinking,
                    'completed': actioned
                }
            })
        
        # Check for action conflicts
        actions = [(s['id'], s.get('action', 'none')) for s in sessions]
        action_tasks = []
        for qc_id, action in actions:
            if action and action not in ['none', 'null']:
                # Extract task/ticket reference
                if 'task-' in action or 'ticket-' in action:
                    action_tasks.append((qc_id, action))
        
        # If multiple different tasks/tickets, that's a conflict
        unique_actions = set(action for _, action in action_tasks)
        if len(unique_actions) > 1:
            conflicts.append({
                'type': 'action_conflict',
                'severity': 'high',
                'description': f"Multiple different actions across sessions: {', '.join(unique_actions)}",
                'sessions': [id for id, _ in action_tasks]
            })
        
        # Check for temporal conflicts (actioned sessions referencing each other)
        # Sessions that are "actioned" should not reference later sessions
        for i, session1 in enumerate(sessions):
            if session1.get('status') == 'actioned':
                # Check if it references any of the other sessions
                body1 = session1.get('body', '')
                for session2 in sessions[i+1:]:
                    if session2['id'] in body1:
                        # Check if session2 is newer
                        date1 = session1.get('date', '')
                        date2 = session2.get('date', '')
                        if date2 > date1:
                            conflicts.append({
                                'type': 'temporal_conflict',
                                'severity': 'medium',
                                'description': f"{session1['id']} (actioned) references later session {session2['id']}",
                                'sessions': [session1['id'], session2['id']]
                            })
        
        # Check for contradictory patterns/anchors
        all_anchors = []
        for session in sessions:
            anchors_text = session.get('anchors', '')
            if anchors_text:
                all_anchors.append((session['id'], anchors_text))
        
        # Simple keyword-based contradiction detection
        if len(all_anchors) >= 2:
            # Look for obvious contradictions
            contradiction_keywords = [
                ('should', 'should not'),
                ('must', 'must not'),
                ('always', 'never'),
                ('stateless', 'stateful'),
                ('sync', 'async'),
                ('client-side', 'server-side'),
            ]
            
            for kw1, kw2 in contradiction_keywords:
                sessions_with_kw1 = [id for id, text in all_anchors if kw1 in text.lower()]
                sessions_with_kw2 = [id for id, text in all_anchors if kw2 in text.lower()]
                
                if sessions_with_kw1 and sessions_with_kw2:
                    conflicts.append({
                        'type': 'semantic_conflict',
                        'severity': 'high',
                        'description': f"Potential contradiction: '{kw1}' vs '{kw2}'",
                        'sessions': sessions_with_kw1 + sessions_with_kw2,
                        'details': {
                            'keyword1': kw1,
                            'sessions1': sessions_with_kw1,
                            'keyword2': kw2,
                            'sessions2': sessions_with_kw2
                        }
                    })
        
        return conflicts
    
    async def _generate_suggestions(
        self, 
        conflicts: list[dict[str, Any]], 
        sessions: list[dict[str, Any]]
    ) -> list[str]:
        """Generate resolution suggestions"""
        
        suggestions = []
        
        for conflict in conflicts:
            conflict_type = conflict['type']
            severity = conflict['severity']
            
            if conflict_type == 'type_mismatch':
                suggestions.append(
                    "✓ Consider focusing on QCs of the same type for coherent context. "
                    "Mixed types are acceptable but may provide less focused guidance."
                )
            
            elif conflict_type == 'status_conflict':
                suggestions.append(
                    "⚠️ Mixing active thinking sessions with completed ones. "
                    "Completed sessions may have outdated or superseded decisions. "
                    "Consider prioritizing the more recent or actively thinking sessions."
                )
            
            elif conflict_type == 'action_conflict':
                suggestions.append(
                    "❌ Multiple different actions across sessions indicates unrelated contexts. "
                    "These QCs may not be relevant to the same work. "
                    "Consider loading only QCs related to your current task."
                )
            
            elif conflict_type == 'temporal_conflict':
                suggestions.append(
                    "⚠️ Temporal inconsistency detected (completed session referencing future session). "
                    "This may indicate improper cross-references or mislabeled status. "
                    "Verify the status and references are correct."
                )
            
            elif conflict_type == 'semantic_conflict':
                kw1 = conflict['details']['keyword1']
                kw2 = conflict['details']['keyword2']
                suggestions.append(
                    f"❌ CONFLICT: Sessions have contradictory patterns ('{kw1}' vs '{kw2}'). "
                    f"Review decisions in these sessions and choose which approach to follow. "
                    f"Document your choice in the new QC session."
                )
        
        if not conflicts:
            suggestions.append("✅ No conflicts detected. Sessions appear compatible.")
        
        return suggestions
    
    async def _update_vocab_map(
        self, 
        conflicts: list[dict[str, Any]], 
        sessions: list[dict[str, Any]]
    ) -> None:
        """Update vocabulary map with findings"""
        
        # Track terminology from sessions
        for session in sessions:
            # Extract key terms from anchors
            anchors = session.get('anchors', '')
            if anchors:
                # Look for pattern markers (💡, 💭, 🎯)
                for line in anchors.split('\n'):
                    if line.strip() and any(emoji in line for emoji in ['💭', '💡', '🎯']):
                        # Extract the term/pattern
                        # This is a simple extraction - could be enhanced
                        term = line.strip().lstrip('💭💡🎯').strip()
                        if len(term) > 10 and len(term) < 200:
                            # Store in vocab map
                            key = term[:50].lower().replace(' ', '_')
                            if key not in self.vocab_map:
                                self.vocab_map[key] = {
                                    'term': term,
                                    'first_seen': session['id'],
                                    'occurrences': [session['id']]
                                }
                            else:
                                if session['id'] not in self.vocab_map[key]['occurrences']:
                                    self.vocab_map[key]['occurrences'].append(session['id'])
        
        # Save vocabulary map
        try:
            vocab_data = {
                'generated': datetime.now().isoformat(),
                'vocabulary': self.vocab_map
            }
            self.vocab_file.write_text(json.dumps(vocab_data, indent=2), encoding='utf-8')
            logger.info(f"✅ Updated vocabulary map with {len(self.vocab_map)} terms")
        except Exception as e:
            logger.warning(f"Failed to save vocabulary map: {e}")
    
    def _format_validation_report(
        self, 
        sessions: list[dict[str, Any]], 
        conflicts: list[dict[str, Any]], 
        suggestions: list[str]
    ) -> str:
        """Format validation report as markdown"""
        
        output = ["# QC Merge Validation Report\n"]
        
        # Sessions summary
        output.append(f"## Sessions Analyzed ({len(sessions)})\n")
        for session in sessions:
            qc_id = session['id']
            title = session.get('title', 'Untitled')
            date = session.get('date', 'Unknown')
            qc_type = session.get('type', 'Unknown')
            status = session.get('status', 'Unknown')
            
            output.append(f"- **{qc_id}**: {title}")
            output.append(f"  - Date: {date} | Type: {qc_type} | Status: {status}")
        
        output.append("")
        
        # Conflicts section
        if conflicts:
            output.append(f"## ⚠️ Conflicts Detected ({len(conflicts)})\n")
            
            for i, conflict in enumerate(conflicts, 1):
                severity = conflict['severity'].upper()
                conflict_type = conflict['type'].replace('_', ' ').title()
                description = conflict['description']
                sessions_involved = ', '.join(conflict['sessions'])
                
                severity_emoji = {
                    'LOW': '⚠️',
                    'MEDIUM': '⚠️',
                    'HIGH': '❌'
                }.get(severity, '⚠️')
                
                output.append(f"### {i}. {severity_emoji} {conflict_type} [{severity}]")
                output.append(f"{description}")
                output.append(f"**Sessions**: {sessions_involved}\n")
        else:
            output.append("## ✅ No Conflicts Detected\n")
            output.append("All sessions appear compatible and can be safely used together.\n")
        
        # Suggestions section
        output.append("## Resolution Suggestions\n")
        for suggestion in suggestions:
            output.append(f"{suggestion}\n")
        
        # Summary
        if conflicts:
            high_severity = sum(1 for c in conflicts if c['severity'] == 'high')
            medium_severity = sum(1 for c in conflicts if c['severity'] == 'medium')
            low_severity = sum(1 for c in conflicts if c['severity'] == 'low')
            
            output.append("## Summary\n")
            output.append(f"- **Total Conflicts**: {len(conflicts)}")
            output.append(f"- **High Severity**: {high_severity}")
            output.append(f"- **Medium Severity**: {medium_severity}")
            output.append(f"- **Low Severity**: {low_severity}")
            
            if high_severity > 0:
                output.append("\n⚠️ **ACTION REQUIRED**: High severity conflicts detected. Review and resolve before proceeding.")
            elif medium_severity > 0:
                output.append("\n⚠️ **RECOMMENDED**: Review medium severity conflicts for potential issues.")
            else:
                output.append("\n✓ Only low severity issues. Proceed with caution.")
        
        return "\n".join(output)

