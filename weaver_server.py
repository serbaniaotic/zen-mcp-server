#!/usr/bin/env python3
"""
Standalone Weaver MCP Server

Simple MCP server that exposes only the Weaver tools:
- capture_curiosity
- capture_learning
- search_curiosity

This runs independently from the main zen-mcp server for easier debugging.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import MCP
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    logger.error("MCP package not installed. Run: pip install mcp")
    sys.exit(1)

# Import Weaver tools
try:
    from tools.weaver_tools import weaver_tools
except ImportError as e:
    logger.error(f"Failed to import Weaver tools: {e}")
    sys.exit(1)

# Initialize server
server = Server("weaver-server")

logger.info("✅ Weaver tools singleton loaded successfully")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Weaver tools"""
    return [
        Tool(
            name="capture_curiosity",
            description="Capture a 'Did you know...' curiosity moment in Weaver knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "discovery": {
                        "type": "string",
                        "description": "What you discovered or learned"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context (session, ticket, etc.)"
                    },
                    "feeling": {
                        "type": "string",
                        "description": "How this made you feel (e.g., 'mind_blown', 'excited', 'curious')"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    }
                },
                "required": ["discovery"]
            }
        ),
        Tool(
            name="capture_learning",
            description="Capture a learning reflection in Weaver knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "reflection": {
                        "type": "string",
                        "description": "What you learned today"
                    },
                    "depth": {
                        "type": "string",
                        "description": "Depth of learning: 'surface', 'medium', or 'deep'",
                        "enum": ["surface", "medium", "deep"],
                        "default": "medium"
                    },
                    "session_context": {
                        "type": "string",
                        "description": "Optional context about the session/work"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    }
                },
                "required": ["reflection"]
            }
        ),
        Tool(
            name="search_curiosity",
            description="Search past curiosity moments in Weaver knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find past curiosity moments"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="discover_learning_path",
            description="Discover learning paths between concepts in knowledge graph (Phase 6.2)",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_concept": {
                        "type": "string",
                        "description": "Starting concept to trace from"
                    },
                    "end_concept": {
                        "type": "string",
                        "description": "Ending concept (optional - shows all paths if omitted)"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum path depth (default: 3)",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 5
                    }
                },
                "required": ["start_concept"]
            }
        ),
        Tool(
            name="find_concept_clusters",
            description="Find concept clusters - concepts that frequently appear together (Phase 6.2)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "min_co_occurrence": {
                        "type": "integer",
                        "description": "Minimum times concepts must appear together (default: 2)",
                        "default": 2,
                        "minimum": 1
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum clusters to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="find_related_concepts",
            description="Find concepts related to a given concept (Phase 6.2)",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": "Concept to find relations for"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum related concepts to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": ["concept"]
            }
        ),
        Tool(
            name="trace_concept_evolution",
            description="Trace how your understanding of a concept evolved over time (Phase 6.2)",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": "Concept to trace evolution for"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    }
                },
                "required": ["concept"]
            }
        ),
        Tool(
            name="calculate_concept_importance",
            description="Calculate concept importance using PageRank-like algorithms (Phase 6.3)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum concepts to return (default: 20)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="detect_topic_communities",
            description="Detect topic communities using community detection algorithms (Phase 6.3)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "min_community_size": {
                        "type": "integer",
                        "description": "Minimum concepts per community (default: 2)",
                        "default": 2,
                        "minimum": 1
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="find_shortest_learning_path",
            description="Find shortest learning path between two concepts (Phase 6.3)",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_concept": {
                        "type": "string",
                        "description": "Starting concept"
                    },
                    "end_concept": {
                        "type": "string",
                        "description": "Ending concept"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum path length (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["start_concept", "end_concept"]
            }
        ),
        Tool(
            name="calculate_concept_centrality",
            description="Calculate concept centrality metrics (betweenness, degree, closeness) (Phase 6.3)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum concepts to return (default: 20)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "metric": {
                        "type": "string",
                        "description": "Centrality metric: 'degree', 'betweenness', or 'closeness'",
                        "enum": ["degree", "betweenness", "closeness"],
                        "default": "betweenness"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="export_graph_cytoscape",
            description="Export knowledge graph to Cytoscape.js JSON format for web visualization (Phase 6.4)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "include_style": {
                        "type": "boolean",
                        "description": "Include styling information (default: true)",
                        "default": True
                    },
                    "max_nodes": {
                        "type": "integer",
                        "description": "Maximum nodes to export (default: 100)",
                        "default": 100,
                        "minimum": 10,
                        "maximum": 500
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="export_graph_graphviz",
            description="Export knowledge graph to Graphviz DOT format for publication-quality diagrams (Phase 6.4)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "layout": {
                        "type": "string",
                        "description": "Layout algorithm: dot, neato, fdp, sfdp, circo, twopi (default: dot)",
                        "enum": ["dot", "neato", "fdp", "sfdp", "circo", "twopi"],
                        "default": "dot"
                    },
                    "max_nodes": {
                        "type": "integer",
                        "description": "Maximum nodes to export (default: 100)",
                        "default": 100,
                        "minimum": 10,
                        "maximum": 500
                    },
                    "min_edge_weight": {
                        "type": "integer",
                        "description": "Minimum edge weight to include (default: 2)",
                        "default": 2,
                        "minimum": 1
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="export_graph_d3",
            description="Export knowledge graph to D3.js JSON format for force-directed visualizations (Phase 6.4)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "max_nodes": {
                        "type": "integer",
                        "description": "Maximum nodes to export (default: 100)",
                        "default": 100,
                        "minimum": 10,
                        "maximum": 500
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="generate_graph_stats",
            description="Generate comprehensive statistical summary of the knowledge graph (Phase 6.4)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="identify_knowledge_gaps",
            description="Identify knowledge gaps - concepts you've touched on but haven't fully explored (Phase 6.5)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "min_mentions": {
                        "type": "integer",
                        "description": "Minimum mentions to consider (default: 2)",
                        "default": 2,
                        "minimum": 1
                    },
                    "max_connections": {
                        "type": "integer",
                        "description": "Maximum connections to qualify as gap (default: 3)",
                        "default": 3,
                        "minimum": 1
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum gaps to return (default: 20)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="suggest_learning_topics",
            description="Suggest learning topics based on your current knowledge (Phase 6.5)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum suggestions to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="track_learning_velocity",
            description="Track learning velocity - measure learning activity over time (Phase 6.5)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "time_window_days": {
                        "type": "integer",
                        "description": "Days to analyze (default: 30)",
                        "default": 30,
                        "minimum": 1,
                        "maximum": 365
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="predict_interests",
            description="Predict future learning interests based on patterns (Phase 6.5)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier (defaults to 'dingo')",
                        "default": "dingo"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum predictions to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": []
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a Weaver tool"""
    try:
        logger.info(f"Calling tool: {name} with args: {arguments}")

        if name == "capture_curiosity":
            result = await weaver_tools.capture_curiosity(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "capture_learning":
            result = await weaver_tools.capture_learning(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "search_curiosity":
            result = await weaver_tools.search_curiosity(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "discover_learning_path":
            result = await weaver_tools.discover_learning_path(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "find_concept_clusters":
            result = await weaver_tools.find_concept_clusters(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "find_related_concepts":
            result = await weaver_tools.find_related_concepts(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "trace_concept_evolution":
            result = await weaver_tools.trace_concept_evolution(**arguments)
            return [TextContent(type="text", text=str(result))]

        # Phase 6.3: Advanced Graph Algorithms
        elif name == "calculate_concept_importance":
            result = await weaver_tools.calculate_concept_importance(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "detect_topic_communities":
            result = await weaver_tools.detect_topic_communities(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "find_shortest_learning_path":
            result = await weaver_tools.find_shortest_learning_path(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "calculate_concept_centrality":
            result = await weaver_tools.calculate_concept_centrality(**arguments)
            return [TextContent(type="text", text=str(result))]

        # Phase 6.4: Graph Visualization
        elif name == "export_graph_cytoscape":
            result = await weaver_tools.export_graph_cytoscape(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "export_graph_graphviz":
            result = await weaver_tools.export_graph_graphviz(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "export_graph_d3":
            result = await weaver_tools.export_graph_d3(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "generate_graph_stats":
            result = await weaver_tools.generate_graph_stats(**arguments)
            return [TextContent(type="text", text=str(result))]

        # Phase 6.5: Learning Insights
        elif name == "identify_knowledge_gaps":
            result = await weaver_tools.identify_knowledge_gaps(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "suggest_learning_topics":
            result = await weaver_tools.suggest_learning_topics(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "track_learning_velocity":
            result = await weaver_tools.track_learning_velocity(**arguments)
            return [TextContent(type="text", text=str(result))]

        elif name == "predict_interests":
            result = await weaver_tools.predict_interests(**arguments)
            return [TextContent(type="text", text=str(result))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Start the Weaver MCP server"""
    logger.info("🌟 Starting Weaver MCP Server...")
    logger.info("✅ Phase 4-5 Tools: capture_curiosity, capture_learning, search_curiosity")
    logger.info("✅ Phase 6.2 Tools: discover_learning_path, find_concept_clusters, find_related_concepts, trace_concept_evolution")
    logger.info("✅ Phase 6.3 Tools: calculate_concept_importance, detect_topic_communities, find_shortest_learning_path, calculate_concept_centrality")
    logger.info("✅ Phase 6.4 Tools: export_graph_cytoscape, export_graph_graphviz, export_graph_d3, generate_graph_stats")
    logger.info("✅ Phase 6.5 Tools: identify_knowledge_gaps, suggest_learning_topics, track_learning_velocity, predict_interests")
    logger.info("🔗 Infrastructure: PostgreSQL (5433), Qdrant (6333), Memgraph (7687)")
    logger.info("🎓 Total Tools: 19 (3 core + 4 Phase 6.2 + 4 Phase 6.3 + 4 Phase 6.4 + 4 Phase 6.5)")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server crashed: {e}", exc_info=True)
        sys.exit(1)
