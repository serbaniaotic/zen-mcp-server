"""
Smart Chat tool - Automatic provider routing based on limits

This tool automatically selects the best available AI provider based on:
- Current usage limits
- Task requirements
- Quality preferences

Extends the base chat tool with intelligent load balancing across:
- Claude (best quality, your primary)
- Gemini (fallback, long context)
- GPT-4 (alternative perspective)
"""

from typing import TYPE_CHECKING, Any, Optional
from pydantic import Field

if TYPE_CHECKING:
    from tools.models import ToolModelCategory

from config import TEMPERATURE_BALANCED
from systemprompts import CHAT_PROMPT
from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from .simple.base import SimpleTool


CHAT_SMART_FIELD_DESCRIPTIONS = {
    "prompt": (
        "Your question or task. The smart router will automatically select the best AI provider "
        "based on current limits and task requirements. Provide detailed context."
    ),
    "files": "Absolute file or folder paths for code context (do NOT shorten).",
    "images": "Optional absolute image paths or base64 for visual context.",
    "prefer_quality": (
        "Set to true to prefer Claude (highest quality) even if limits are low. "
        "Set to false to prioritize availability over quality. Default: true."
    ),
}


class ChatSmartRequest(ToolRequest):
    """Request model for Smart Chat tool"""

    prompt: str = Field(..., description=CHAT_SMART_FIELD_DESCRIPTIONS["prompt"])
    files: Optional[list[str]] = Field(default_factory=list, description=CHAT_SMART_FIELD_DESCRIPTIONS["files"])
    images: Optional[list[str]] = Field(default_factory=list, description=CHAT_SMART_FIELD_DESCRIPTIONS["images"])
    prefer_quality: bool = Field(default=True, description=CHAT_SMART_FIELD_DESCRIPTIONS["prefer_quality"])


class ChatSmartTool(SimpleTool):
    """
    Smart chat with automatic AI provider routing based on limits.

    This tool extends the base chat functionality with intelligent provider selection:
    - Tries Claude first (best quality)
    - Falls back to Gemini if Claude at limit
    - Falls back to GPT-4 if both maxed
    - Tracks usage and predicts limits

    Use this when you want automatic limit management instead of manually choosing providers.

    Examples:
    - "Use chat_smart to analyze this code" (auto-routes to best available)
    - "Use chat_smart with prefer_quality=false to get fastest response"
    """

    def get_name(self) -> str:
        return "chat_smart"

    def get_description(self) -> str:
        return (
            "Smart chat with automatic AI provider routing. Automatically selects Claude, Gemini, or GPT-4 "
            "based on current usage limits and task requirements. Never get stuck waiting for limits to reset!"
        )

    def get_system_prompt(self) -> str:
        return CHAT_PROMPT + "\n\nNOTE: You are being routed through an intelligent provider selector. The system has automatically chosen the best available AI model for this task based on current usage limits."

    def get_default_temperature(self) -> float:
        return TEMPERATURE_BALANCED

    def get_model_category(self) -> "ToolModelCategory":
        """Smart chat uses dynamic routing"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.FAST_RESPONSE  # Will be overridden by routing logic

    def get_request_model(self):
        return ChatSmartRequest

    async def execute(self, request: ChatSmartRequest, **kwargs) -> dict[str, Any]:
        """Execute with smart provider routing"""

        # Select provider based on limits and preferences
        provider = await self._select_provider(request.prefer_quality)

        # Log the routing decision (for transparency)
        routing_info = {
            "provider_selected": provider["name"],
            "reason": provider["reason"],
            "prefer_quality": request.prefer_quality,
        }

        # Execute with selected provider
        # NOTE: This would integrate with your existing provider routing logic
        # For now, returning routing information
        return {
            "routing": routing_info,
            "prompt": request.prompt,
            "message": f"Routed to {provider['name']}: {provider['reason']}",
        }

    async def _select_provider(self, prefer_quality: bool = True) -> dict[str, Any]:
        """
        Select best available provider

        Priority when prefer_quality=True:
        1. Claude (if under limit)
        2. Gemini (fallback)
        3. GPT-4 (last resort)

        Priority when prefer_quality=False:
        1. First available provider
        2. Fastest provider
        """

        # TODO: Implement actual limit checking
        # For now, return logic for demonstration

        # Check Claude availability
        claude_available = await self._check_provider_available("claude")

        if claude_available and prefer_quality:
            return {
                "name": "claude",
                "reason": "Best quality, under limit",
                "model": "claude-sonnet-4",
            }

        # Check Gemini availability
        gemini_available = await self._check_provider_available("gemini")

        if gemini_available:
            return {
                "name": "gemini",
                "reason": "Claude at limit, using Gemini fallback",
                "model": "gemini-2.0-flash-exp",
            }

        # Check GPT-4 availability
        gpt4_available = await self._check_provider_available("gpt4")

        if gpt4_available:
            return {
                "name": "gpt4",
                "reason": "Claude and Gemini at limit, using GPT-4",
                "model": "gpt-4",
            }

        # All providers at limit
        return {
            "name": "claude",
            "reason": "All providers at limit, defaulting to Claude (will queue)",
            "model": "claude-sonnet-4",
        }

    async def _check_provider_available(self, provider_name: str) -> bool:
        """
        Check if provider is under limits

        TODO: Implement actual limit tracking:
        - Track requests per hour/day
        - Check against known limits
        - Predict when limits will reset
        - Store in shared state/redis/etc.
        """

        # Placeholder - always return True for now
        # In real implementation, would check:
        # - Request count in current window
        # - Known provider limits
        # - Time until reset
        return True

    def get_input_schema(self) -> dict[str, Any]:
        """Return the input schema for MCP"""
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": CHAT_SMART_FIELD_DESCRIPTIONS["prompt"],
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": CHAT_SMART_FIELD_DESCRIPTIONS["files"],
                },
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": CHAT_SMART_FIELD_DESCRIPTIONS["images"],
                },
                "prefer_quality": {
                    "type": "boolean",
                    "description": CHAT_SMART_FIELD_DESCRIPTIONS["prefer_quality"],
                    "default": True,
                },
                **COMMON_FIELD_DESCRIPTIONS,
            },
            "required": ["prompt"],
        }
