"""
Zen MCP Tool: Agent Routing Tracker
Integrates routing tracking with Zen MCP server for real-time monitoring
"""

import os
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import Field

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from tools.shared.tamdac import TamdacProject, MemoryManager, CommandManager
from .simple.base import SimpleTool

FIELD_DESCRIPTIONS = {
    "action": "Action to perform: track, report, dashboard, validate",
    "prompt_id": "Unique identifier for the prompt/routing decision",
    "prompt_text": "The actual prompt text being routed",
    "task_type": "Type of task: planning, review, implementation, coding, creative, analysis",
    "platform": "Target platform: cursor, copilot_chat, chatgpt, claude_code",
    "agent": "Target agent: pm, architect, dev, universal",
    "provider": "Target provider: gemini-2.5-flash, gpt-4.1, gpt-5, o3-pro, claude-3.5-sonnet",
    "predicted_tokens": "Predicted token usage",
    "actual_tokens": "Actual token usage (for validation)",
    "actual_cost": "Actual cost (for validation)",
    "success": "Whether the routing was successful",
    "days": "Number of days for reporting (default: 7)",
    "format": "Output format: text, json, html",
}

class RoutingTrackerRequest(ToolRequest):
    """Request model for Agent Routing Tracker tool"""

    action: str = Field(description=FIELD_DESCRIPTIONS["action"])
    prompt_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["prompt_id"])
    prompt_text: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["prompt_text"])
    task_type: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["task_type"])
    platform: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["platform"])
    agent: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["agent"])
    provider: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["provider"])
    predicted_tokens: Optional[int] = Field(None, description=FIELD_DESCRIPTIONS["predicted_tokens"])
    actual_tokens: Optional[int] = Field(None, description=FIELD_DESCRIPTIONS["actual_tokens"])
    actual_cost: Optional[float] = Field(None, description=FIELD_DESCRIPTIONS["actual_cost"])
    success: Optional[bool] = Field(None, description=FIELD_DESCRIPTIONS["success"])
    days: int = Field(default=7, description=FIELD_DESCRIPTIONS["days"])
    format: str = Field(default="text", description=FIELD_DESCRIPTIONS["format"])


class AgentRoutingTrackerTool(SimpleTool):
    """
    Track and validate agent routing decisions across four platforms.
    
    This tool integrates with the agent routing tracking system to:
    - Track routing decisions in real-time
    - Validate token usage and cost predictions
    - Generate comprehensive reports
    - Monitor platform efficiency and cost optimization
    - Provide live dashboard data
    """

    def get_name(self) -> str:
        return "agent_routing_tracker"

    def get_description(self) -> str:
        return "Track and validate agent routing decisions across Claude Code, Cursor, Copilot Chat, and ChatGPT."

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """Return tool-specific field definitions"""
        return {
            "action": {
                "type": "string",
                "description": "Action to perform: track, report, dashboard, validate",
                "enum": ["track", "report", "dashboard", "validate"]
            },
            "prompt_id": {
                "type": "string",
                "description": "Unique identifier for the prompt/routing decision"
            },
            "prompt_text": {
                "type": "string",
                "description": "The actual prompt text being routed"
            },
            "task_type": {
                "type": "string",
                "description": "Type of task: planning, review, implementation, coding, creative, analysis",
                "enum": ["planning", "review", "implementation", "coding", "creative", "analysis"]
            },
            "platform": {
                "type": "string",
                "description": "Target platform: cursor, copilot_chat, chatgpt, claude_code",
                "enum": ["cursor", "copilot_chat", "chatgpt", "claude_code"]
            },
            "agent": {
                "type": "string",
                "description": "Target agent: pm, architect, dev, universal",
                "enum": ["pm", "architect", "dev", "universal"]
            },
            "provider": {
                "type": "string",
                "description": "Target provider: gemini-2.5-flash, gpt-4.1, gpt-5, o3-pro, claude-3.5-sonnet",
                "enum": ["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4.1", "gpt-5", "gpt-5-codex", "o3-pro", "o3-mini", "claude-3.5-sonnet"]
            },
            "predicted_tokens": {
                "type": "integer",
                "description": "Predicted token usage"
            },
            "actual_tokens": {
                "type": "integer",
                "description": "Actual token usage (for validation)"
            },
            "actual_cost": {
                "type": "number",
                "description": "Actual cost (for validation)"
            },
            "success": {
                "type": "boolean",
                "description": "Whether the routing was successful"
            },
            "days": {
                "type": "integer",
                "description": "Number of days for reporting (default: 7)",
                "default": 7
            },
            "format": {
                "type": "string",
                "description": "Output format: text, json, html",
                "enum": ["text", "json", "html"],
                "default": "text"
            }
        }

    def prepare_prompt(self, request: RoutingTrackerRequest, **kwargs) -> str:
        """Prepare the prompt for routing tracking"""
        
        if request.action == "track":
            prompt = f"""Track a new agent routing decision.

Prompt ID: {request.prompt_id}
Prompt Text: {request.prompt_text}
Task Type: {request.task_type}
Platform: {request.platform}
Agent: {request.agent}
Provider: {request.provider}
Predicted Tokens: {request.predicted_tokens}

This tool will:
1. Log the routing decision to the tracking database
2. Calculate predicted costs based on provider pricing
3. Record the decision for later validation
4. Update platform usage statistics

Please execute the routing tracking workflow."""

        elif request.action == "validate":
            prompt = f"""Validate a routing decision with actual results.

Prompt ID: {request.prompt_id}
Actual Tokens: {request.actual_tokens}
Actual Cost: {request.actual_cost}
Success: {request.success}

This tool will:
1. Update the routing decision with actual results
2. Calculate token and cost variances
3. Update efficiency scores
4. Generate validation metrics

Please execute the routing validation workflow."""

        elif request.action == "report":
            prompt = f"""Generate a comprehensive routing report.

Period: Last {request.days} days
Format: {request.format}

This tool will:
1. Analyze platform usage metrics
2. Calculate routing accuracy
3. Generate cost optimization report
4. Provide recommendations for improvement

Please execute the routing report generation."""

        elif request.action == "dashboard":
            prompt = f"""Generate live dashboard data for agent routing.

Format: {request.format}

This tool will:
1. Collect current live statistics
2. Analyze platform distribution
3. Calculate hourly rates and trends
4. Generate alerts and recommendations

Please execute the dashboard data generation."""

        else:
            prompt = f"""Unknown action: {request.action}

Available actions:
- track: Log a new routing decision
- validate: Update routing decision with actual results
- report: Generate comprehensive routing report
- dashboard: Generate live dashboard data

Please specify a valid action."""

        return prompt

    async def _call(self, request: RoutingTrackerRequest, **kwargs) -> Dict[str, Any]:
        """Execute the routing tracking logic."""
        
        try:
            # Import the tracking system
            import sys
            from pathlib import Path
            
            # Add the current directory to Python path
            current_dir = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(current_dir))
            
            from agent_routing_tracker import AgentRoutingTracker, RoutingDecision
            from datetime import datetime
            
            # Initialize tracker
            db_path = os.path.join(os.getcwd(), "agent_routing_tracker.db")
            tracker = AgentRoutingTracker(db_path)
            
            if request.action == "track":
                return await self._track_decision(request, tracker)
            elif request.action == "validate":
                return await self._validate_decision(request, tracker)
            elif request.action == "report":
                return await self._generate_report(request, tracker)
            elif request.action == "dashboard":
                return await self._generate_dashboard(request, tracker)
            else:
                return {"success": False, "error": f"Unknown action: {request.action}"}
                
        except Exception as e:
            return {"success": False, "error": f"Routing tracking error: {str(e)}"}

    async def _track_decision(self, request: RoutingTrackerRequest, tracker: AgentRoutingTracker) -> Dict[str, Any]:
        """Track a new routing decision"""
        
        if not all([request.prompt_id, request.prompt_text, request.task_type, 
                   request.platform, request.agent, request.provider, request.predicted_tokens]):
            return {"success": False, "error": "Missing required fields for tracking"}
        
        # Calculate predicted cost
        provider_costs = {
            "claude-3.5-sonnet": 0.30,
            "gemini-2.5-flash": 0.075,
            "gemini-2.5-pro": 0.15,
            "gpt-4.1": 0.30,
            "gpt-5": 0.25,
            "gpt-5-codex": 0.20,
            "o3-pro": 0.35,
            "o3-mini": 0.20
        }
        
        cost_per_1m = provider_costs.get(request.provider, 0.30)
        predicted_cost = (request.predicted_tokens / 1_000_000) * cost_per_1m
        
        # Create routing decision
        decision = RoutingDecision(
            timestamp=datetime.now().isoformat(),
            prompt_id=request.prompt_id,
            prompt_text=request.prompt_text,
            prompt_length=len(request.prompt_text),
            task_type=request.task_type,
            complexity_score=self._calculate_complexity(request.prompt_text),
            platform=request.platform,
            agent=request.agent,
            provider=request.provider,
            command=self._get_command_for_agent(request.agent),
            predicted_tokens=request.predicted_tokens,
            predicted_cost=predicted_cost,
            cost_per_1m=cost_per_1m
        )
        
        # Log the decision
        tracker.log_routing_decision(decision)
        
        return {
            "success": True,
            "action": "track",
            "prompt_id": request.prompt_id,
            "predicted_cost": predicted_cost,
            "cost_per_1m": cost_per_1m,
            "message": f"Routing decision logged for {request.platform} + {request.agent} + {request.provider}"
        }

    async def _validate_decision(self, request: RoutingTrackerRequest, tracker: AgentRoutingTracker) -> Dict[str, Any]:
        """Validate a routing decision with actual results"""
        
        if not all([request.prompt_id, request.actual_tokens, request.actual_cost, 
                   request.success is not None]):
            return {"success": False, "error": "Missing required fields for validation"}
        
        # Update execution result
        success = tracker.update_execution_result(
            request.prompt_id,
            request.actual_tokens,
            request.actual_cost,
            execution_time=2.0,  # Default execution time
            success=request.success
        )
        
        if success:
            return {
                "success": True,
                "action": "validate",
                "prompt_id": request.prompt_id,
                "actual_tokens": request.actual_tokens,
                "actual_cost": request.actual_cost,
                "success": request.success,
                "message": "Routing decision validated and updated"
            }
        else:
            return {
                "success": False,
                "error": f"Could not find routing decision for prompt_id: {request.prompt_id}"
            }

    async def _generate_report(self, request: RoutingTrackerRequest, tracker: AgentRoutingTracker) -> Dict[str, Any]:
        """Generate comprehensive routing report"""
        
        try:
            # Get platform metrics
            platform_metrics = tracker.get_platform_metrics(request.days)
            
            # Get routing accuracy
            accuracy = tracker.get_routing_accuracy(request.days)
            
            # Get cost optimization report
            cost_report = tracker.get_cost_optimization_report(request.days)
            
            # Generate text report
            report_text = tracker.generate_routing_report(request.days)
            
            if request.format == "json":
                return {
                    "success": True,
                    "action": "report",
                    "period_days": request.days,
                    "platform_metrics": [asdict(m) for m in platform_metrics],
                    "accuracy": accuracy,
                    "cost_report": cost_report,
                    "report_text": report_text
                }
            else:
                return {
                    "success": True,
                    "action": "report",
                    "period_days": request.days,
                    "report": report_text
                }
                
        except Exception as e:
            return {"success": False, "error": f"Report generation error: {str(e)}"}

    async def _generate_dashboard(self, request: RoutingTrackerRequest, tracker: AgentRoutingTracker) -> Dict[str, Any]:
        """Generate live dashboard data"""
        
        try:
            # Import dashboard
            from live_routing_dashboard import LiveRoutingDashboard
            
            dashboard = LiveRoutingDashboard(tracker)
            stats = dashboard._collect_live_stats()
            
            # Generate alerts
            alerts = dashboard.generate_alerts()
            
            # Generate trend analysis
            trends = dashboard.get_trend_analysis(6)
            
            if request.format == "json":
                return {
                    "success": True,
                    "action": "dashboard",
                    "timestamp": stats.timestamp,
                    "total_requests_today": stats.total_requests_today,
                    "total_tokens_today": stats.total_tokens_today,
                    "total_cost_today": stats.total_cost_today,
                    "cost_savings_today": stats.cost_savings_today,
                    "success_rate": stats.success_rate,
                    "platform_distribution": stats.platform_distribution,
                    "provider_distribution": stats.provider_distribution,
                    "alerts": alerts,
                    "trends": trends
                }
            else:
                dashboard_text = f"""
LIVE AGENT ROUTING DASHBOARD
Generated: {stats.timestamp}

TODAY'S SUMMARY:
- Requests: {stats.total_requests_today:,}
- Tokens: {stats.total_tokens_today:,}
- Cost: ${stats.total_cost_today:.4f}
- Savings: ${stats.cost_savings_today:.4f}
- Success Rate: {stats.success_rate:.1%}

PLATFORM DISTRIBUTION:
"""
                for platform, count in stats.platform_distribution.items():
                    percentage = (count / stats.total_requests_today * 100) if stats.total_requests_today > 0 else 0
                    dashboard_text += f"- {platform.title()}: {count} ({percentage:.1f}%)\n"
                
                dashboard_text += f"\nALERTS:\n"
                for alert in alerts:
                    dashboard_text += f"- {alert}\n"
                
                return {
                    "success": True,
                    "action": "dashboard",
                    "dashboard": dashboard_text
                }
                
        except Exception as e:
            return {"success": False, "error": f"Dashboard generation error: {str(e)}"}

    def _calculate_complexity(self, prompt_text: str) -> float:
        """Calculate complexity score for a prompt"""
        length = len(prompt_text)
        
        # Base complexity from length
        if length < 50:
            complexity = 0.3
        elif length < 100:
            complexity = 0.5
        elif length < 200:
            complexity = 0.7
        else:
            complexity = 0.9
        
        # Adjust based on keywords
        complex_keywords = ["analyze", "review", "implement", "design", "architecture", "complex", "advanced"]
        simple_keywords = ["simple", "basic", "quick", "easy", "help"]
        
        prompt_lower = prompt_text.lower()
        
        for keyword in complex_keywords:
            if keyword in prompt_lower:
                complexity = min(1.0, complexity + 0.1)
        
        for keyword in simple_keywords:
            if keyword in prompt_lower:
                complexity = max(0.1, complexity - 0.1)
        
        return complexity

    def _get_command_for_agent(self, agent: str) -> str:
        """Get the appropriate command for an agent"""
        commands = {
            "pm": "/pm-plan",
            "architect": "/architect-review", 
            "dev": "/dev-implement",
            "universal": "/chat"
        }
        return commands.get(agent, "/chat")
