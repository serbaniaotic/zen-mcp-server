"""
MemGraph Query Tool for Zen MCP Server

Provides access to TAMDAC MemoryGraph for querying QC sessions, past decisions,
insights, and sequential thinking chains. Enables context-aware model routing
based on historical anchors.
"""

import os
from typing import Any, Dict, List

from tools.base import BaseTool
from tools.models import ToolOutput
from utils.memgraph_client import MemGraphClient


class MemGraphTool(BaseTool):
    """
    Tool for querying TAMDAC MemoryGraph database.
    
    Provides access to:
    - QC session insights and decisions
    - Sequential thinking chains
    - Past architectural decisions
    - Constraint hierarchy (what binds current work)
    
    Enables intelligent model routing based on historical context.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "memgraph_query"
        self.description = (
            "Query TAMDAC MemoryGraph for past QC sessions, decisions, insights, "
            "and architectural constraints. Use this to understand historical context, "
            "check past decisions, and ensure new work respects established anchors."
        )
        
        # Get MemGraph connection from environment or use default
        memgraph_uri = os.getenv("MEMGRAPH_URI", "bolt://localhost:7687")
        self.client = MemGraphClient(uri=memgraph_uri)
        
        # Test connection on init
        self._connection_ok = self.client.verify_connection()
        if not self._connection_ok:
            self.logger.warning(
                f"MemGraph connection failed. URI: {memgraph_uri}. "
                "Tool will return connection errors."
            )
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Define input parameters for the tool"""
        return {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": [
                        "session_insights",
                        "session_decisions", 
                        "sequential_thinking",
                        "decision_reasoning",
                        "binding_constraints",
                        "all_sessions"
                    ],
                    "description": "Type of query to execute against MemoryGraph"
                },
                "session_id": {
                    "type": "string",
                    "description": "QC session ID (e.g., 'qc-001'). Required for session-specific queries."
                },
                "decision_id": {
                    "type": "string",
                    "description": "Decision ID (e.g., 'decision-qc001-memorygraph-priority'). Required for decision_reasoning."
                },
                "scope": {
                    "type": "string",
                    "description": "Constraint scope to filter (e.g., 'all_technology_choices'). Optional for binding_constraints."
                }
            },
            "required": ["query_type"]
        }
    
    async def run(
        self,
        query_type: str,
        session_id: str = None,
        decision_id: str = None,
        scope: str = None,
        **kwargs
    ) -> ToolOutput:
        """Execute MemGraph query based on type"""
        
        # Check connection
        if not self._connection_ok:
            return ToolOutput(
                output="❌ MemGraph connection unavailable. Check if MemGraph is running at bolt://localhost:7687",
                error="Connection failed",
                metadata={"connection_ok": False}
            )
        
        try:
            result = None
            
            if query_type == "session_insights":
                if not session_id:
                    return ToolOutput(
                        output="❌ session_id required for session_insights query",
                        error="Missing required parameter"
                    )
                result = self._get_session_insights(session_id)
            
            elif query_type == "session_decisions":
                if not session_id:
                    return ToolOutput(
                        output="❌ session_id required for session_decisions query",
                        error="Missing required parameter"
                    )
                result = self._get_session_decisions(session_id)
            
            elif query_type == "sequential_thinking":
                if not session_id:
                    return ToolOutput(
                        output="❌ session_id required for sequential_thinking query",
                        error="Missing required parameter"
                    )
                result = self._get_sequential_thinking(session_id)
            
            elif query_type == "decision_reasoning":
                if not decision_id:
                    return ToolOutput(
                        output="❌ decision_id required for decision_reasoning query",
                        error="Missing required parameter"
                    )
                result = self._get_decision_reasoning(decision_id)
            
            elif query_type == "binding_constraints":
                result = self._get_binding_constraints(scope)
            
            elif query_type == "all_sessions":
                result = self._get_all_sessions()
            
            else:
                return ToolOutput(
                    output=f"❌ Unknown query_type: {query_type}",
                    error="Invalid query type"
                )
            
            return ToolOutput(
                output=result["formatted"],
                metadata={
                    "query_type": query_type,
                    "data": result.get("data", {}),
                    "count": result.get("count", 0)
                }
            )
            
        except Exception as e:
            self.logger.error(f"MemGraph query failed: {e}", exc_info=True)
            return ToolOutput(
                output=f"❌ MemGraph query error: {str(e)}",
                error=str(e)
            )
    
    def _get_session_insights(self, session_id: str) -> Dict[str, Any]:
        """Get all insights from a QC session"""
        insights = self.client.get_session_insights(session_id)
        
        if not insights:
            return {
                "formatted": f"No insights found for session {session_id}",
                "data": [],
                "count": 0
            }
        
        lines = [f"📊 **Insights from {session_id}** ({len(insights)} total)\n"]
        for ins in insights:
            lines.append(
                f"**{ins['sequence']}. [{ins['impact']}]** {ins['content']}\n"
                f"   Type: {ins['type']}\n"
            )
        
        return {
            "formatted": "\n".join(lines),
            "data": insights,
            "count": len(insights)
        }
    
    def _get_session_decisions(self, session_id: str) -> Dict[str, Any]:
        """Get all decisions from a QC session"""
        decisions = self.client.get_session_decisions(session_id)
        
        if not decisions:
            return {
                "formatted": f"No decisions found for session {session_id}",
                "data": [],
                "count": 0
            }
        
        lines = [f"⚖️  **Decisions from {session_id}** ({len(decisions)} total)\n"]
        for dec in decisions:
            scope_str = ", ".join(dec['binding_scope'])
            lines.append(
                f"**{dec['sequence']}. [{dec['status']}]** {dec['content']}\n"
                f"   Binding scope: {scope_str}\n"
            )
        
        return {
            "formatted": "\n".join(lines),
            "data": decisions,
            "count": len(decisions)
        }
    
    def _get_sequential_thinking(self, session_id: str) -> Dict[str, Any]:
        """Get the sequential thinking chain from a session"""
        thinking = self.client.get_sequential_thinking(session_id)
        
        if not thinking:
            return {
                "formatted": f"No thinking chain found for session {session_id}",
                "data": [],
                "count": 0
            }
        
        lines = [f"🔗 **Sequential Thinking from {session_id}**\n"]
        for i, thought in enumerate(thinking, 1):
            lines.append(f"{i}. {thought}\n")
        
        return {
            "formatted": "\n".join(lines),
            "data": thinking,
            "count": len(thinking)
        }
    
    def _get_decision_reasoning(self, decision_id: str) -> Dict[str, Any]:
        """Get the reasoning chain that led to a decision"""
        reasoning = self.client.why_was_decision_made(decision_id)
        
        if not reasoning:
            return {
                "formatted": f"No reasoning found for decision {decision_id}",
                "data": [],
                "count": 0
            }
        
        lines = [f"🎯 **Why was this decision made?**\n"]
        for r in reasoning:
            lines.append(f"**Insight**: {r['insight']}\n")
            lines.append(f"**Led to**: {r['decision']}\n")
        
        return {
            "formatted": "\n".join(lines),
            "data": reasoning,
            "count": len(reasoning)
        }
    
    def _get_binding_constraints(self, scope: str = None) -> Dict[str, Any]:
        """Get binding constraints (decisions that apply to current work)"""
        # Query for approved decisions with binding scopes
        with self.client.driver.session() as session:
            if scope:
                query = """
                MATCH (d:DECISION)
                WHERE d.status = 'approved' AND $scope IN d.binding_scope
                RETURN d.id AS id, d.content AS content, d.binding_scope AS scope
                ORDER BY d.sequence
                """
                result = session.run(query, scope=scope)
            else:
                query = """
                MATCH (d:DECISION)
                WHERE d.status = 'approved'
                RETURN d.id AS id, d.content AS content, d.binding_scope AS scope
                ORDER BY d.sequence
                """
                result = session.run(query)
            
            constraints = [dict(record) for record in result]
        
        if not constraints:
            scope_str = f" with scope '{scope}'" if scope else ""
            return {
                "formatted": f"No binding constraints found{scope_str}",
                "data": [],
                "count": 0
            }
        
        lines = [f"🔒 **Binding Constraints** ({len(constraints)} total)\n"]
        for c in constraints:
            scope_str = ", ".join(c['scope'])
            lines.append(
                f"**{c['id']}**: {c['content']}\n"
                f"   Applies to: {scope_str}\n"
            )
        
        return {
            "formatted": "\n".join(lines),
            "data": constraints,
            "count": len(constraints)
        }
    
    def _get_all_sessions(self) -> Dict[str, Any]:
        """Get list of all QC sessions"""
        with self.client.driver.session() as session:
            query = """
            MATCH (qc:QC_SESSION)
            RETURN qc.id AS id, qc.status AS status, 
                   qc.timestamp AS timestamp, qc.duration_minutes AS duration
            ORDER BY qc.timestamp DESC
            """
            result = session.run(query)
            sessions = [dict(record) for record in result]
        
        if not sessions:
            return {
                "formatted": "No QC sessions found in MemoryGraph",
                "data": [],
                "count": 0
            }
        
        lines = [f"📝 **All QC Sessions** ({len(sessions)} total)\n"]
        for s in sessions:
            lines.append(
                f"**{s['id']}** [{s['status']}] - {s['duration']} minutes\n"
                f"   {s['timestamp']}\n"
            )
        
        return {
            "formatted": "\n".join(lines),
            "data": sessions,
            "count": len(sessions)
        }
    
    def __del__(self):
        """Clean up connection on deletion"""
        try:
            if hasattr(self, 'client'):
                self.client.close()
        except:
            pass

