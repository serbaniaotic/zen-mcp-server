"""
Server integration for intelligent routing.
Provides routing suggestions and analytics logging for tool executions.
"""

import logging
import time
from typing import Any, Dict, Optional

from routing.intelligent_router import IntelligentRouter
from utils.analytics import ZenAnalytics

logger = logging.getLogger(__name__)


class RouterIntegration:
    """
    Integration layer between intelligent router and MCP server.
    Provides routing suggestions and logs all tool executions to analytics.
    """
    
    def __init__(self, enable_analytics: bool = True, enable_suggestions: bool = True):
        """
        Initialize router integration.
        
        Args:
            enable_analytics: Whether to log executions to analytics
            enable_suggestions: Whether to provide routing suggestions
        """
        self.enable_analytics = enable_analytics
        self.enable_suggestions = enable_suggestions
        
        # Initialize analytics if enabled
        self.analytics = None
        if self.enable_analytics:
            try:
                self.analytics = ZenAnalytics()
                logger.info("Analytics enabled for router integration")
            except Exception as e:
                logger.warning(f"Failed to initialize analytics: {e}")
                self.analytics = None
        
        # Initialize router
        self.router = IntelligentRouter(analytics=self.analytics)
        logger.info("Router integration initialized")
    
    def get_routing_suggestion(
        self,
        user_query: str,
        context: Optional[Dict] = None,
        files: Optional[list] = None,
    ) -> Optional[str]:
        """
        Get a routing suggestion for a user query.
        
        Args:
            user_query: User's query
            context: Optional context dictionary
            files: Optional file list
            
        Returns:
            Human-readable suggestion or None if suggestions disabled
        """
        if not self.enable_suggestions:
            return None
        
        try:
            return self.router.get_routing_suggestion(user_query, context, files)
        except Exception as e:
            logger.error(f"Failed to get routing suggestion: {e}")
            return None
    
    def log_tool_execution(
        self,
        tool_name: str,
        model: Optional[str] = None,
        tokens_used: Optional[int] = None,
        execution_time_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        status: str = "completed",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Log a tool execution to analytics.
        
        Args:
            tool_name: Name of the tool executed
            model: Model used
            tokens_used: Number of tokens
            execution_time_ms: Execution time in milliseconds
            success: Whether execution succeeded
            error_message: Error message if failed
            status: Execution status
            metadata: Additional metadata
        """
        if not self.enable_analytics or not self.analytics:
            return
        
        try:
            self.analytics.log_tool_execution(
                tool_name=tool_name,
                model=model,
                tokens_used=tokens_used,
                execution_time_ms=execution_time_ms,
                success=success,
                error_message=error_message,
                status=status,
                metadata=metadata
            )
            logger.debug(f"Logged execution for {tool_name}")
        except Exception as e:
            logger.error(f"Failed to log tool execution: {e}")
    
    def log_routing_decision(
        self,
        user_intent: str,
        chosen_tool: str,
        chosen_strategy: str,
        detected_complexity: int,
        detected_risk: int,
        outcome: str = "pending",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Log a routing decision to analytics.
        
        Args:
            user_intent: User's original query
            chosen_tool: Tool selected
            chosen_strategy: Strategy used
            detected_complexity: Complexity score
            detected_risk: Risk score
            outcome: Outcome status
            metadata: Additional metadata
        """
        if not self.enable_analytics or not self.analytics:
            return
        
        try:
            self.analytics.log_routing_decision(
                user_intent=user_intent,
                chosen_tool=chosen_tool,
                chosen_strategy=chosen_strategy,
                detected_complexity=detected_complexity,
                detected_risk=detected_risk,
                outcome=outcome,
                metadata=metadata
            )
            logger.debug(f"Logged routing decision for {chosen_tool}")
        except Exception as e:
            logger.error(f"Failed to log routing decision: {e}")
    
    def close(self):
        """Close analytics connection"""
        if self.analytics:
            self.analytics.close()
            logger.info("Router integration closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global router integration instance (singleton)
_router_integration: Optional[RouterIntegration] = None


def get_router_integration() -> RouterIntegration:
    """
    Get the global router integration instance.
    Creates it if it doesn't exist.
    
    Returns:
        RouterIntegration instance
    """
    global _router_integration
    
    if _router_integration is None:
        # Check environment variables for configuration
        import os
        enable_analytics = os.getenv("ENABLE_ROUTING_ANALYTICS", "true").lower() == "true"
        enable_suggestions = os.getenv("ENABLE_ROUTING_SUGGESTIONS", "true").lower() == "true"
        
        _router_integration = RouterIntegration(
            enable_analytics=enable_analytics,
            enable_suggestions=enable_suggestions
        )
    
    return _router_integration


def shutdown_router_integration():
    """Shutdown the global router integration"""
    global _router_integration
    
    if _router_integration:
        _router_integration.close()
        _router_integration = None

