"""
Intelligent routing module for Zen MCP Server.
Automatically selects optimal tools based on task characteristics.
"""

from .intelligent_router import IntelligentRouter, RoutingDecision, RoutingStrategy
from .server_integration import RouterIntegration, get_router_integration, shutdown_router_integration

__all__ = [
    "IntelligentRouter",
    "RoutingDecision",
    "RoutingStrategy",
    "RouterIntegration",
    "get_router_integration",
    "shutdown_router_integration",
]

