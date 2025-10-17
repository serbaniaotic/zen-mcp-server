"""
Dataset RAG Tool - Query HuggingFace datasets via GraphRAG

This tool provides access to reasoning datasets (HotpotQA, MuSiQue) through
hybrid vector + graph search using smartmemoryapi's GraphRAG engine.
"""

import logging
import httpx
from typing import Any, Optional
from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.simple.base import SimpleTool

logger = logging.getLogger(__name__)

# Field descriptions
DATASET_RAG_FIELD_DESCRIPTIONS = {
    "query": "Your question to answer using reasoning dataset knowledge (HotpotQA, MuSiQue)",
    "dataset": "Dataset to query: 'hotpotqa' | 'musique' | 'all' (default: 'all')",
    "use_graph_reasoning": "Enable multi-hop graph traversal for complex reasoning (default: True)",
    "max_hops": "Maximum reasoning hops for graph traversal (1-5, default: 3)",
}


class DatasetRAGRequest(ToolRequest):
    """Request model for Dataset RAG tool"""
    
    query: str = Field(..., description=DATASET_RAG_FIELD_DESCRIPTIONS["query"])
    dataset: str = Field(default="all", description=DATASET_RAG_FIELD_DESCRIPTIONS["dataset"])
    use_graph_reasoning: bool = Field(default=True, description=DATASET_RAG_FIELD_DESCRIPTIONS["use_graph_reasoning"])
    max_hops: int = Field(default=3, ge=1, le=5, description=DATASET_RAG_FIELD_DESCRIPTIONS["max_hops"])


class DatasetRAGTool(SimpleTool):
    """
    Query reasoning datasets using GraphRAG (vector + graph hybrid search)
    
    This tool enables agents to access multi-hop reasoning knowledge from
    datasets like HotpotQA and MuSiQue through smartmemoryapi's GraphRAG engine.
    
    Features:
    - Vector search in Pinecone for semantic similarity
    - Graph traversal in Memgraph for reasoning chains
    - Combined context for LLM reasoning
    """
    
    def __init__(self):
        super().__init__()
        self.smartmemory_url = "http://localhost:8099"  # Default smartmemoryapi URL
    
    def get_name(self) -> str:
        return "dataset_rag"
    
    def get_description(self) -> str:
        return (
            "Query reasoning datasets (HotpotQA, MuSiQue) using hybrid vector+graph search. "
            "Provides multi-hop reasoning chains and supporting facts from knowledge graph."
        )
    
    def get_request_model(self):
        return DatasetRAGRequest
    
    def get_system_prompt(self) -> str:
        return """You are a reasoning assistant with access to multi-hop question-answering datasets.

When analyzing the retrieved context:
1. Examine both vector search results (semantic similarity) and graph reasoning paths
2. Follow multi-hop reasoning chains from the knowledge graph
3. Cite specific facts and their relationships
4. Explain the reasoning steps clearly

The context includes:
- Vector Search Results: Semantically similar content from Pinecone
- Graph Reasoning Paths: Multi-hop chains from Memgraph knowledge graph

Use this structured knowledge to provide well-reasoned, evidence-based answers."""
    
    async def prepare_prompt(self, arguments: dict[str, Any]) -> tuple[str, list]:
        """
        Prepare prompt with GraphRAG context
        
        Calls smartmemoryapi /api/v2/rag/graph-search to retrieve
        vector + graph context, then formats for LLM
        """
        query = arguments.get("query", "")
        use_graph = arguments.get("use_graph_reasoning", True)
        max_hops = arguments.get("max_hops", 3)
        
        logger.info(f"DatasetRAG query: {query}")
        
        try:
            # Call smartmemoryapi GraphRAG endpoint
            graphrag_context = await self._query_graphrag(query, max_hops)
            
            # Format prompt with context
            if graphrag_context.get("success"):
                vector_results = graphrag_context.get("vector_results", [])
                graph_paths = graphrag_context.get("graph_paths", [])
                combined_context = graphrag_context.get("combined_context", "")
                
                prompt = f"""Based on reasoning dataset knowledge, answer this question:

**Question**: {query}

**Retrieved Context (Vector + Graph Search)**:

{combined_context}

**Analysis Instructions**:
1. Use both vector search results and graph reasoning paths
2. Follow the multi-hop reasoning chains
3. Cite specific facts and relationships
4. Provide a well-reasoned answer

**Your Response**:"""
                
                logger.info(f"GraphRAG returned {len(vector_results)} vector results, {len(graph_paths)} graph paths")
            
            else:
                # Fallback if GraphRAG fails
                error = graphrag_context.get("error", "Unknown error")
                logger.warning(f"GraphRAG query failed: {error}")
                
                prompt = f"""Question: {query}

Note: GraphRAG search unavailable ({error}). Please answer based on your general knowledge and indicate that dataset-specific context was not available."""
        
        except Exception as e:
            logger.error(f"Failed to query GraphRAG: {e}")
            prompt = f"""Question: {query}

Note: Failed to retrieve dataset context ({str(e)}). Please answer based on your general knowledge."""
        
        return prompt, []
    
    async def _query_graphrag(self, query: str, max_hops: int) -> dict:
        """
        Query smartmemoryapi via existing /search endpoint

        Phase 1: Uses vector search from smartmemoryapi + Pinecone
        Future: Will add graph traversal via Memgraph for multi-hop reasoning

        Returns:
            Dict with vector_results, combined_context
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Query smartmemoryapi /search endpoint (Mem0-compatible)
                response = await client.post(
                    f"{self.smartmemory_url}/search",
                    json={
                        "query": query,
                        "limit": 10,
                        "user_id": "datasets",  # Namespace for HF datasets
                        "categories": None  # Search all categories
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    memories = data.get("memories", [])

                    # Format results for compatibility with GraphRAG format
                    vector_results = [
                        {
                            "content": mem.get("content", ""),
                            "metadata": mem.get("metadata", {}),
                            "score": mem.get("score", 0.0)
                        }
                        for mem in memories
                    ]

                    # Combine into context text
                    combined_context = self._format_context(vector_results)

                    return {
                        "success": True,
                        "vector_results": vector_results,
                        "graph_paths": [],  # Empty for Phase 1, will add Memgraph in Phase 2
                        "combined_context": combined_context
                    }
                else:
                    logger.error(f"SmartMemoryAPI error: {response.status_code}")
                    return {"success": False, "error": f"API returned {response.status_code}"}

        except httpx.ConnectError:
            logger.error("Failed to connect to smartmemoryapi (is it running on port 8099?)")
            return {"success": False, "error": "smartmemoryapi not available"}

        except Exception as e:
            logger.error(f"Dataset RAG query error: {e}")
            return {"success": False, "error": str(e)}

    def _format_context(self, vector_results: list) -> str:
        """Format vector search results into readable context"""
        if not vector_results:
            return "No relevant examples found in datasets."

        lines = ["**Examples from Reasoning Datasets:**\n"]

        for i, result in enumerate(vector_results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            score = result.get("score", 0.0)

            # Extract metadata if available
            dataset = metadata.get("dataset", "unknown")
            answer = metadata.get("answer", "")

            lines.append(f"\n**Example {i}** (score: {score:.2f}, source: {dataset})")
            lines.append(f"Question: {content}")
            if answer:
                lines.append(f"Answer: {answer}")
            lines.append("")

        return "\n".join(lines)
    
    def wants_line_numbers_by_default(self) -> bool:
        """Dataset RAG doesn't use file context"""
        return False
    
    def default_conversation_turns(self) -> int:
        """Support multi-turn conversations about reasoning"""
        return 10

