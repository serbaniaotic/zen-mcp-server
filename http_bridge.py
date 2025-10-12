"""
HTTP Bridge for Zen-MCP Server
Provides REST API access to zen-mcp tools for external applications like voice-QC
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Add zen-mcp to path
sys.path.insert(0, str(Path(__file__).parent))

from routing.intelligent_router import IntelligentRouter
from utils.analytics import ZenAnalytics
from tools import ChatTool, ThinkDeepTool, DebugIssueTool, CLinkTool, ConsensusTool, PlannerTool

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Zen-MCP HTTP Bridge",
    description="REST API for voice-QC and other applications to access zen-mcp tools",
    version="1.0.0"
)

# CORS for voice-QC frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
router: Optional[IntelligentRouter] = None
analytics: Optional[ZenAnalytics] = None

# Tool registry for HTTP bridge
TOOLS = {
    "chat": ChatTool,
    "thinkdeep": ThinkDeepTool,
    "debug": DebugIssueTool,
    "clink": CLinkTool,
    "consensus": ConsensusTool,
    "planner": PlannerTool,
}


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    transcript: str = Field(..., description="User transcript from voice input")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    auto_route: bool = Field(default=True, description="Use intelligent routing")
    tool_override: Optional[str] = Field(None, description="Force specific tool (chat, thinkdeep, debug, etc.)")
    model: Optional[str] = Field(None, description="Specific model to use")
    files: list[str] = Field(default_factory=list, description="File paths for context")
    
    # CLI Agent Selection (for clink)
    use_cli_agent: bool = Field(default=False, description="Route to CLI agent (cursor, gemini, etc.) via clink")
    cli_name: Optional[str] = Field(default="cursor", description="CLI agent to use (cursor, gemini, codex)")
    cli_role: Optional[str] = Field(default="default", description="CLI role preset (default, codereviewer, planner, etc.)")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    success: bool
    response: str
    tool_used: str
    strategy: str
    complexity: Optional[int] = None
    risk: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


@app.on_event("startup")
async def startup():
    """Initialize zen-mcp components"""
    global router, analytics
    
    logger.info("🚀 Starting Zen-MCP HTTP Bridge...")
    
    # Note: Model providers are configured by individual tools as needed
    
    # Initialize analytics
    try:
        analytics = ZenAnalytics()
        logger.info("✅ Analytics initialized")
    except Exception as e:
        logger.warning(f"⚠️  Analytics unavailable: {e}")
        analytics = None
    
    # Initialize intelligent router
    try:
        router = IntelligentRouter(analytics)
        logger.info("✅ Intelligent router initialized")
    except Exception as e:
        logger.error(f"❌ Router initialization failed: {e}")
        router = None
    
    logger.info("✅ Zen-MCP HTTP Bridge ready!")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "router_available": router is not None,
        "analytics_available": analytics is not None,
        "tools_count": len(TOOLS)
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint with intelligent routing
    
    This endpoint:
    1. Receives user transcript from voice-QC
    2. Uses IntelligentRouter to select best tool (if auto_route=True)
    3. Executes the tool
    4. Returns structured response
    """
    try:
        logger.info(f"📥 Received chat request: {request.transcript[:100]}...")
        
        # Check if user wants CLI agent (cursor, gemini, etc.)
        if request.use_cli_agent:
            tool_name = "clink"
            strategy = "CLI_AGENT"
            complexity = None
            risk = None
            logger.info(f"🔗 Routing to CLI agent: {request.cli_name} (role: {request.cli_role})")
        # Determine which tool to use
        elif request.tool_override:
            tool_name = request.tool_override
            strategy = "MANUAL"
            complexity = None
            risk = None
            logger.info(f"🎯 Manual tool selection: {tool_name}")
        elif request.auto_route and router:
            tool_name, strategy = router.route_request(
                user_query=request.transcript,
                context=request.context
            )
            complexity = router._analyze_complexity(request.transcript)
            risk = router._assess_risk(request.transcript, request.context)
            logger.info(f"🤖 Auto-routed to: {tool_name} (strategy: {strategy}, complexity: {complexity}, risk: {risk})")
        else:
            # Default to chat if no routing available
            tool_name = "chat"
            strategy = "FALLBACK"
            complexity = None
            risk = None
            logger.info("🔄 Fallback to chat tool")
        
        # Get the tool
        if tool_name not in TOOLS:
            raise HTTPException(status_code=400, detail=f"Tool '{tool_name}' not found")
        
        tool = TOOLS[tool_name]
        
        # Prepare tool arguments
        if tool_name == "clink":
            # Special args for clink (CLI agent routing)
            tool_args = {
                "prompt": request.transcript,
                "cli_name": request.cli_name,
                "role": request.cli_role,
                "files": request.files
            }
        else:
            # Standard tool args
            tool_args = {
                "prompt": request.transcript,
                "model": request.model or "auto",
                "files": request.files,
                **request.context
            }
        
        # Execute tool
        logger.info(f"⚙️  Executing {tool_name} with model: {tool_args.get('model')}")
        result = await tool.execute(tool_args)
        
        # Extract response text
        if isinstance(result, list):
            response_text = "\n".join([item.text for item in result if hasattr(item, 'text')])
        elif isinstance(result, dict):
            response_text = result.get("response", str(result))
        else:
            response_text = str(result)
        
        logger.info(f"✅ Response generated: {len(response_text)} chars")
        
        # Log to analytics
        if analytics:
            try:
                analytics.log_tool_execution(
                    tool=tool_name,
                    model=request.model or "auto",
                    tokens=len(response_text) // 4,  # Rough estimate
                    duration=0,  # TODO: Track actual duration
                    success=True
                )
            except Exception as e:
                logger.warning(f"Analytics logging failed: {e}")
        
        return ChatResponse(
            success=True,
            response=response_text,
            tool_used=tool_name,
            strategy=strategy,
            complexity=complexity,
            risk=risk,
            metadata={
                "model": request.model or "auto",
                "auto_routed": request.auto_route
            }
        )
    
    except Exception as e:
        logger.error(f"❌ Chat request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_tools():
    """List available zen-mcp tools"""
    return {
        "tools": [
            {
                "name": name,
                "description": tool.description
            }
            for name, tool in TOOLS.items()
        ]
    }


@app.get("/router/stats")
async def router_stats():
    """Get router statistics"""
    if not analytics:
        raise HTTPException(status_code=503, detail="Analytics not available")
    
    try:
        stats = analytics.get_tool_performance(days=7)
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the HTTP bridge server"""
    port = int(os.getenv("HTTP_BRIDGE_PORT", "8766"))
    host = os.getenv("HTTP_BRIDGE_HOST", "0.0.0.0")
    
    logger.info(f"🌐 Starting HTTP Bridge on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()

