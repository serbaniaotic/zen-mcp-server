"""
Zen MCP Tool: Spatial Memory with Domain Colors
Implements spatial awareness in embeddings using metadata "colors" for cross-domain retrieval
"""

import os
import json
import requests
from typing import Any, Dict, Optional, List
from pydantic import Field
from datetime import datetime

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from .simple.base import SimpleTool

# smartmemoryapi endpoint
SMARTMEMORY_URL = os.getenv("SMARTMEMORY_URL", "http://localhost:8099")

FIELD_DESCRIPTIONS = {
    "content": "Content to store with spatial awareness",
    "domain": "Domain color: technical, legal, business, infrastructure, devops, database, etc",
    "pattern": "Abstract pattern: resource_contention, deadlock, race_condition, config_error, etc",
    "status": "Solution status: production_ready, experimental, deprecated, failed_attempt",
    "language": "Programming languages involved: python, csharp, sql, javascript, etc",
    "root_cause": "Root cause category for classification",
    "query": "Search query with spatial awareness",
    "color_filter": "Filter by domain colors (comma-separated)",
    "pattern_filter": "Filter by abstract patterns (comma-separated)",
    "cross_domain": "Allow cross-domain jumps via pattern matching",
    "hybrid_mode": "Use hybrid search (semantic + keyword/metadata)",
}

class SpatialMemoryRequest(ToolRequest):
    """Request model for Spatial Memory tool"""
    
    content: str = Field(description=FIELD_DESCRIPTIONS["content"])
    domain: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["domain"])
    pattern: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["pattern"])
    status: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["status"])
    language: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["language"])
    root_cause: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["root_cause"])
    
    # Search parameters
    query: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["query"])
    color_filter: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["color_filter"])
    pattern_filter: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["pattern_filter"])
    cross_domain: bool = Field(default=True, description=FIELD_DESCRIPTIONS["cross_domain"])
    hybrid_mode: bool = Field(default=True, description=FIELD_DESCRIPTIONS["hybrid_mode"])


class SpatialMemoryTool(SimpleTool):
    """
    Spatial memory with domain "colors" for intelligent cross-domain retrieval.

    Implements the "color/metaphor" concept for embeddings:
    - Vector embeddings = spatial position (semantic meaning)
    - Metadata colors = domain context (technical, legal, business, etc)
    - Abstract patterns = cross-domain bridges (deadlock, race condition, etc)
    - Hybrid search = semantic + keyword/metadata for better retrieval

    Example:
      "Database deadlock" (technical domain, deadlock pattern)
      Can be found when searching for "thread contention" (different domain, same pattern)
    """

    def get_name(self) -> str:
        return "spatial_memory"

    def get_description(self) -> str:
        return "Store and retrieve with spatial awareness using domain colors and abstract patterns"

    def requires_model(self) -> bool:
        """Spatial memory is a utility tool - no AI model needed"""
        return False

    def get_required_fields(self) -> list[str]:
        """Required fields for spatial memory operations"""
        return ["action", "content"]

    async def execute(self, arguments: dict[str, Any]) -> list:
        """
        Execute spatial memory operation without AI model.
        This is a utility tool that directly calls Pinecone APIs.
        """
        import json
        from mcp.types import TextContent

        try:
            # Call the existing run_tool method that has the logic
            result = self.run_tool(arguments)

            # Format as MCP response
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        except Exception as e:
            logger.error(f"Spatial memory execution failed: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e),
                    "message": "Spatial memory operation failed"
                }, indent=2)
            )]

    async def prepare_prompt(self, request) -> str:
        """Not used - spatial memory doesn't use AI prompts"""
        return ""

    def get_system_prompt(self) -> str:
        return """You are a spatial memory system that understands semantic embeddings WITH domain context.

Your role is to:
1. Add "color" (domain tags) to memories for spatial awareness
2. Identify abstract patterns that bridge domains
3. Enable cross-domain retrieval when patterns align
4. Use hybrid search (semantic + metadata) for better results
5. Prevent wrong-domain pollution while allowing smart jumps

Domain Colors:
- technical: Code, APIs, algorithms, infrastructure
- database: SQL, schemas, queries, transactions
- business: Workflows, processes, stakeholder needs
- legal: Compliance, contracts, regulations
- devops: Deployment, CI/CD, monitoring, automation
- infrastructure: Servers, networks, storage, scaling
- ux: User experience, interfaces, design patterns
- security: Authentication, authorization, vulnerabilities

Abstract Patterns (cross-domain bridges):
- resource_contention: Deadlocks, race conditions, locks
- config_error: Misconfigurations, wrong settings, env issues
- performance_degradation: Slow responses, bottlenecks, scaling issues
- data_corruption: Integrity issues, sync problems, validation failures
- auth_failure: Permission denied, token issues, access problems
- network_issue: Timeouts, connectivity, DNS problems

When storing:
  Always add domain color and abstract pattern
  Tag with languages/technologies involved
  Mark status (production_ready, experimental, failed_attempt)

When searching:
  Use hybrid mode by default (semantic + metadata)
  Filter by color to prevent wrong-domain results
  Use patterns to enable smart cross-domain jumps
  Example: "Database deadlock" can help with "Thread contention" (same pattern, different domain)"""

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """Return tool-specific field definitions"""
        return {
            "action": {
                "type": "string",
                "description": "Action: store, search, search_pattern, search_cross_domain",
                "enum": ["store", "search", "search_pattern", "search_cross_domain"]
            },
            "content": {
                "type": "string",
                "description": "Content to store or search query"
            },
            "domain": {
                "type": "string",
                "description": "Domain color for classification",
                "enum": ["technical", "database", "business", "legal", "devops", "infrastructure", "ux", "security"]
            },
            "pattern": {
                "type": "string",
                "description": "Abstract pattern for cross-domain bridging",
                "enum": ["resource_contention", "config_error", "performance_degradation", "data_corruption", "auth_failure", "network_issue", "state_management", "validation_error"]
            },
            "status": {
                "type": "string",
                "description": "Solution status",
                "enum": ["production_ready", "experimental", "deprecated", "failed_attempt", "needs_validation"]
            }
        }

    def store_with_color(self, content: str, domain: str, pattern: Optional[str] = None, 
                        status: str = "production_ready", language: Optional[str] = None,
                        root_cause: Optional[str] = None, context: Optional[Dict] = None) -> Dict:
        """
        Store content in Pinecone with domain color and abstract pattern
        
        The "color" (domain + pattern) allows for:
        - Same-domain retrieval (exact color match)
        - Cross-domain retrieval (same pattern, different domain)
        - Hybrid search (semantic + keyword/metadata)
        """
        metadata = {
            "type": "spatial_memory",
            "domain": domain,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        if pattern:
            metadata["pattern"] = pattern
        if language:
            metadata["language"] = language
        if root_cause:
            metadata["root_cause"] = root_cause
        if context:
            metadata.update(context)
        
        # Enhanced content with color tags for hybrid search
        enhanced_content = f"[DOMAIN:{domain}] "
        if pattern:
            enhanced_content += f"[PATTERN:{pattern}] "
        enhanced_content += content
        
        try:
            response = requests.post(
                f"{SMARTMEMORY_URL}/extract",
                json={
                    "user_message": enhanced_content,
                    "recent_history": [],
                    "metadata": metadata
                },
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "stored": True,
                "domain": domain,
                "pattern": pattern,
                "metadata": metadata,
                "message": f"Stored with color [{domain}] and pattern [{pattern}]"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to store in Pinecone"
            }

    def search_with_awareness(self, query: str, color_filter: Optional[str] = None,
                             pattern_filter: Optional[str] = None, cross_domain: bool = True,
                             limit: int = 5) -> Dict:
        """
        Search with spatial awareness
        
        Modes:
        1. Same-domain search: color_filter="database" → only database results
        2. Pattern-based search: pattern_filter="resource_contention" → all domains with this pattern
        3. Cross-domain search: Find similar patterns in different domains
        """
        
        # Build enhanced query for hybrid search
        enhanced_query = query
        if color_filter:
            enhanced_query = f"[DOMAIN:{color_filter}] {query}"
        if pattern_filter:
            enhanced_query = f"[PATTERN:{pattern_filter}] {enhanced_query}"
        
        try:
            response = requests.post(
                f"{SMARTMEMORY_URL}/search",
                json={
                    "query": enhanced_query,
                    "limit": limit * 2 if cross_domain else limit  # Get more for cross-domain filtering
                },
                timeout=10
            )
            response.raise_for_status()
            results = response.json()
            
            if not results.get("results"):
                return {
                    "success": True,
                    "results": [],
                    "message": "No results found"
                }
            
            # Filter and rank results
            filtered_results = []
            cross_domain_results = []
            
            for item in results["results"]:
                metadata = item.get("metadata", {})
                item_domain = metadata.get("domain")
                item_pattern = metadata.get("pattern")
                
                # Same domain + same pattern = highest priority
                if color_filter and item_domain == color_filter:
                    if pattern_filter and item_pattern == pattern_filter:
                        item["relevance"] = "exact_match"
                        filtered_results.insert(0, item)
                    elif not pattern_filter:
                        item["relevance"] = "same_domain"
                        filtered_results.append(item)
                
                # Different domain but same pattern = cross-domain match
                elif cross_domain and pattern_filter and item_pattern == pattern_filter:
                    item["relevance"] = "cross_domain_pattern"
                    cross_domain_results.append(item)
                
                # No filter specified, just semantic
                elif not color_filter and not pattern_filter:
                    item["relevance"] = "semantic_only"
                    filtered_results.append(item)
            
            # Combine results: exact matches first, then cross-domain
            final_results = filtered_results[:limit]
            if len(final_results) < limit and cross_domain:
                final_results.extend(cross_domain_results[:limit - len(final_results)])
            
            return {
                "success": True,
                "results": final_results[:limit],
                "total_found": len(final_results),
                "cross_domain_found": len(cross_domain_results),
                "message": f"Found {len(final_results)} results with spatial awareness"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Search failed"
            }

    def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute spatial memory operation"""
        action = params.get("action", "search")
        
        if action == "store":
            return self.store_with_color(
                content=params["content"],
                domain=params.get("domain", "technical"),
                pattern=params.get("pattern"),
                status=params.get("status", "production_ready"),
                language=params.get("language"),
                root_cause=params.get("root_cause"),
                context=params.get("context")
            )
        
        elif action in ["search", "search_pattern", "search_cross_domain"]:
            cross_domain = action == "search_cross_domain" or params.get("cross_domain", True)
            
            return self.search_with_awareness(
                query=params["query"],
                color_filter=params.get("color_filter"),
                pattern_filter=params.get("pattern_filter"),
                cross_domain=cross_domain,
                limit=params.get("limit", 5)
            )
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }


# Example usage in agent system prompts:

CURATOR_ENHANCEMENT = """
When classifying tickets, add domain colors and patterns:

Example 1 - Database Issue:
  store_with_color(
    content="SQL deadlock resolved by adding NOLOCK hints",
    domain="database",
    pattern="resource_contention",
    status="production_ready",
    language="sql, csharp"
  )

Example 2 - Thread Safety Issue:
  store_with_color(
    content="Thread contention fixed with lock optimization",
    domain="technical",
    pattern="resource_contention",  # Same pattern as deadlock!
    status="production_ready",
    language="csharp"
  )

Now when someone searches for "database locking issue", they can find:
1. Same domain: SQL deadlock (exact color match)
2. Cross domain: Thread contention (same pattern, different color)
"""

SEARCH_ENHANCEMENT = """
When searching, use spatial awareness:

Same-Domain Search:
  search_with_awareness(
    query="locking issue",
    color_filter="database",  # Only database domain
    cross_domain=False
  )
  → Returns only database solutions

Cross-Domain Search:
  search_with_awareness(
    query="locking issue",
    pattern_filter="resource_contention",  # Pattern-based
    cross_domain=True
  )
  → Returns deadlocks (database) AND thread contention (technical)
  → Smart jump across domains via shared pattern!

Hybrid Search:
  search_with_awareness(
    query="VB.net app crashing on database commit",
    color_filter="database",
    pattern_filter="resource_contention"
  )
  → Combines semantic similarity + metadata filtering + pattern matching
  → Finds relevant solutions even if exact keywords don't match
"""


