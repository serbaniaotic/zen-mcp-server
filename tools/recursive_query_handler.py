"""
Recursive Query Handler - Python Implementation

Implements recursive refinement pattern using available MCP tools.
Inspired by TRM paper and task-7 design.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, AsyncGraphDatabase

from tools.simple_rag_client import SimpleRAGClient
from tools.simple_llm import SimpleLLM
from tools.vibe_check_tool import get_vibe_check_tool

logger = logging.getLogger(__name__)


class MemgraphClient:
    """Memgraph client for querying knowledge graph"""
    
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "", password: str = ""):
        self.driver = GraphDatabase.driver(uri, auth=(user, password) if user else None)
    
    def close(self):
        self.driver.close()
    
    def query_decisions(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query decisions related to query text"""
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (d:Decision)
                WHERE d.content CONTAINS $query OR d.decision CONTAINS $query
                RETURN d.decision as decision, 
                       d.rationale as rationale,
                       d.confidence as confidence,
                       d.timestamp as timestamp
                ORDER BY d.timestamp DESC
                LIMIT $limit
            """, query=query_text, limit=limit)
            
            return [dict(record) for record in result]
    
    def query_concepts(self, query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query concepts related to query text"""
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Concept)
                WHERE c.name CONTAINS $query OR c.description CONTAINS $query
                OPTIONAL MATCH (c)-[r:RELATES_TO]->(related:Concept)
                RETURN c.name as name,
                       c.description as description,
                       collect(related.name) as related_concepts
                LIMIT $limit
            """, query=query_text, limit=limit)
            
            return [dict(record) for record in result]


class RecursiveQueryHandler:
    """
    Python implementation of recursive query refinement
    
    Uses available MCP tools (webfetch, wikipedia, etc.) to progressively
    refine answers with early stopping based on confidence.
    """
    
    def __init__(self, tools_registry: Dict[str, Any], memgraph_uri: str = "bolt://localhost:7687"):
        self.tools = tools_registry
        self.max_iterations = 16
        self.confidence_threshold = 0.8
        self.token_budget = 5000
        
        # Initialize Memgraph client
        try:
            self.memgraph = MemgraphClient(memgraph_uri)
            logger.info("✅ Memgraph client initialized")
        except Exception as e:
            logger.warning(f"⚠️  Memgraph unavailable: {e}. Using fallback.")
            self.memgraph = None
        
        # Initialize RAG client
        try:
            self.rag = SimpleRAGClient()
            logger.info("✅ RAG client initialized")
        except Exception as e:
            logger.warning(f"⚠️  RAG unavailable: {e}. Using fallback.")
            self.rag = None
        
        # Initialize LLM for gap identification and merging
        try:
            self.llm = SimpleLLM()
            logger.info("✅ LLM helper initialized")
        except Exception as e:
            logger.warning(f"⚠️  LLM unavailable: {e}. Using fallback.")
            self.llm = None
        
        # Initialize Vibe-Check for hallucination detection
        try:
            self.vibe_check = get_vibe_check_tool()
            logger.info("✅ Vibe-Check initialized")
        except Exception as e:
            logger.warning(f"⚠️  Vibe-Check unavailable: {e}. Using fallback.")
            self.vibe_check = None
        
    async def answer(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Answer query using recursive refinement
        
        Returns:
            {
                "answer": str,
                "confidence": float,
                "iterations": int,
                "tokens_used": int,
                "tools_used": List[str],
                "stopped_early": bool
            }
        """
        
        state = {
            "query": query,
            "context": context,
            "answer": "",
            "confidence": 0.0,
            "iteration": 0,
            "tokens_used": 0,
            "tools_used": [],
            "gaps": [],
            "knowledge": []
        }
        
        logger.info(f"🔄 Starting recursive query: {query}")
        
        # Initial query to memory/RAG (Tier 1)
        state = await self._query_memory(state)
        
        # Recursive refinement loop
        for i in range(self.max_iterations):
            state["iteration"] = i + 1
            
            logger.info(f"  🔁 Iteration {state['iteration']}/{self.max_iterations}")
            logger.info(f"     Confidence: {state['confidence']:.1%}")
            logger.info(f"     Tokens: {state['tokens_used']}/{self.token_budget}")
            
            # Check stopping conditions (ACT - Adaptive Computational Time)
            if state["confidence"] >= self.confidence_threshold:
                logger.info(f"  ✅ Early stop: Confidence reached ({state['confidence']:.1%})")
                state["stopped_early"] = True
                break
            
            if len(state["gaps"]) == 0:
                logger.info(f"  ✅ Early stop: No remaining gaps")
                state["stopped_early"] = True
                break
            
            if state["tokens_used"] >= self.token_budget:
                logger.info(f"  ⚠️  Token budget reached")
                break
            
            # Select and query ONE tool (TRM principle: small + focused)
            state = await self._refine_iteration(state)
        
        logger.info(f"📊 Query complete:")
        logger.info(f"   Iterations: {state['iteration']}")
        logger.info(f"   Confidence: {state['confidence']:.1%}")
        logger.info(f"   Tokens: {state['tokens_used']}")
        logger.info(f"   Tools: {', '.join(state['tools_used'])}")
        
        # Final validation with Vibe-Check
        final_validation = await self._validate_answer(
            state["answer"], 
            state["query"], 
            state["iteration"]
        )
        
        # Apply final confidence adjustment
        final_confidence = min(
            state["confidence"] + final_validation["confidence_adjustment"], 
            0.95
        )
        
        if final_validation["risk_level"] == "high":
            logger.warning(f"   ⚠️  Final Vibe-Check: HIGH RISK - confidence reduced")
        elif final_validation["risk_level"] == "low":
            logger.info(f"   ✅ Final Vibe-Check: Low risk")
        
        return {
            "answer": state["answer"],
            "confidence": final_confidence,
            "iterations": state["iteration"],
            "tokens_used": state["tokens_used"],
            "tools_used": state["tools_used"],
            "stopped_early": state.get("stopped_early", False),
            "vibe_check": {
                "risk_level": final_validation["risk_level"],
                "questions": final_validation["questions"][:3],  # Top 3 questions
                "validations_count": len(state.get("validations", []))
            }
        }
    
    async def _query_memory(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Query memory/RAG for initial context"""
        
        query_text = state["query"]
        context_parts = []
        
        # Try Memgraph first (structure)
        if self.memgraph:
            try:
                decisions = self.memgraph.query_decisions(query_text, limit=3)
                concepts = self.memgraph.query_concepts(query_text, limit=3)
                
                if decisions:
                    context_parts.append("📋 Past Decisions (Memgraph):")
                    for d in decisions:
                        context_parts.append(f"  - {d.get('decision', 'N/A')}")
                        if d.get('rationale'):
                            context_parts.append(f"    Rationale: {d['rationale']}")
                
                if concepts:
                    context_parts.append("\n🧠 Related Concepts (Memgraph):")
                    for c in concepts:
                        context_parts.append(f"  - {c.get('name', 'N/A')}")
                        if c.get('description'):
                            context_parts.append(f"    {c['description']}")
                
                logger.info(f"  ✅ Memgraph: {len(decisions)} decisions, {len(concepts)} concepts")
                    
            except Exception as e:
                logger.warning(f"  ⚠️  Memgraph query failed: {e}")
        
        # Try RAG/file-based search (content)
        if self.rag:
            try:
                results = self.rag.search(query_text, limit=3)
                
                if results:
                    context_parts.append("\n📚 Memory Search (RAG):")
                    for r in results:
                        score = r['score']
                        if score > 0.1:  # Only show relevant results
                            context_parts.append(f"  - {r['title']} (relevance: {score:.0%})")
                            # Show first 200 chars of content
                            content_preview = r['content'][:200].replace('\n', ' ')
                            context_parts.append(f"    {content_preview}...")
                
                logger.info(f"  ✅ RAG: {len(results)} results")
                    
            except Exception as e:
                logger.warning(f"  ⚠️  RAG search failed: {e}")
        
        # Combine results
        if context_parts:
            initial_answer = "\n".join(context_parts)
            confidence = 0.6  # Higher confidence with both sources
            tokens = 400  # More tokens with combined results
            tools_used = []
            if self.memgraph:
                tools_used.append("memgraph")
            if self.rag:
                tools_used.append("rag")
        else:
            # Fallback to mock
            initial_answer = f"Initial context for: {query_text}\n(No data sources available)"
            confidence = 0.2
            tokens = 150
            tools_used = ["memory-fallback"]
        
        state["answer"] = initial_answer
        state["confidence"] = confidence
        state["tokens_used"] += tokens
        state["tools_used"].extend(tools_used)
        state["gaps"] = self._identify_gaps(initial_answer, query_text)
        state["knowledge"].append(initial_answer)
        
        return state
    
    async def _refine_iteration(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """One iteration of refinement"""
        
        # Select best tool for current gaps
        tool_name = self._select_tool(state)
        
        if not tool_name:
            # No more tools to use
            state["confidence"] = min(state["confidence"] + 0.1, 0.95)
            return state
        
        logger.info(f"     → Querying {tool_name}")
        
        # Query the tool
        tool_result = await self._query_tool(tool_name, state)
        
        # Merge result
        state["answer"] = self._merge_answers(state["answer"], tool_result)
        state["knowledge"].append(tool_result)
        state["tools_used"].append(tool_name)
        state["tokens_used"] += 200  # Approximate
        
        # Validate answer with Vibe-Check (hallucination detection)
        validation = await self._validate_answer(
            state["answer"], 
            state["query"], 
            state["iteration"]
        )
        
        # Update confidence with Vibe-Check adjustment
        base_confidence_increase = 0.15
        adjusted_increase = base_confidence_increase + validation["confidence_adjustment"]
        state["confidence"] = min(state["confidence"] + adjusted_increase, 0.95)
        
        # Store validation results
        if "validations" not in state:
            state["validations"] = []
        state["validations"].append({
            "iteration": state["iteration"],
            "risk_level": validation["risk_level"],
            "confidence_adjustment": validation["confidence_adjustment"]
        })
        
        # Update gaps
        state["gaps"] = self._identify_gaps(state["answer"], state["query"])
        
        return state
    
    def _identify_gaps(self, answer: str, query: str) -> List[str]:
        """Identify knowledge gaps in current answer"""
        
        # Try LLM-based gap identification
        if self.llm:
            try:
                import asyncio
                # Run async function in sync context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in async context, use create_task
                    task = asyncio.create_task(self.llm.identify_gaps(answer, query))
                    gaps = asyncio.run(asyncio.wait_for(task, timeout=10))
                else:
                    gaps = asyncio.run(self.llm.identify_gaps(answer, query))
                
                if gaps:
                    return gaps
            except Exception as e:
                logger.warning(f"LLM gap identification failed: {e}")
        
        # Fallback to heuristic
        if len(answer) < 100:
            return ["Need more detail", "Need examples", "Need best practices"]
        elif len(answer) < 300:
            return ["Need examples", "Need best practices"]
        elif len(answer) < 600:
            return ["Need best practices"]
        else:
            return []
    
    def _select_tool(self, state: Dict[str, Any]) -> Optional[str]:
        """Select best tool for current iteration (intent-based routing)"""
        
        query = state["query"].lower()
        used_tools = set(state["tools_used"])
        gaps = state["gaps"]
        
        if not gaps:
            return None
        
        first_gap = gaps[0].lower()
        
        # Intent detection (simplified)
        available_tools = ["wikipedia", "webfetch", "context-awesome"]
        available_tools = [t for t in available_tools if t not in used_tools]
        
        if not available_tools:
            return None
        
        # Route based on query intent
        if "api" in query or "schema" in first_gap:
            if "context7" in self.tools and "context7" not in used_tools:
                return "context7"
        
        if "best practices" in first_gap or "libraries" in query:
            if "context-awesome" in available_tools:
                return "context-awesome"
        
        if "how does" in query or "what is" in query:
            if "wikipedia" in available_tools:
                return "wikipedia"
        
        # Default: webfetch
        if "webfetch" in available_tools:
            return "webfetch"
        
        return available_tools[0] if available_tools else None
    
    async def _query_tool(self, tool_name: str, state: Dict[str, Any]) -> str:
        """Query a specific tool"""
        
        # TODO: Actual tool invocation via MCP
        # For now, return mock responses
        
        query = state["query"]
        gap = state["gaps"][0] if state["gaps"] else query
        
        mock_responses = {
            "wikipedia": f"Wikipedia says: {gap} is a concept in computer science...",
            "webfetch": f"Documentation shows: {gap} can be implemented using...",
            "context-awesome": f"Recommended libraries for {gap}: library-a, library-b",
            "context7": f"API schema for {gap}: GET /api/v1/..."
        }
        
        return mock_responses.get(tool_name, f"Result from {tool_name}: {gap}")
    
    def _merge_answers(self, current: str, new_info: str) -> str:
        """Merge new information into current answer"""
        
        # Try LLM-based merging
        if self.llm and len(current) > 50 and len(new_info) > 50:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    task = asyncio.create_task(self.llm.merge_answers(current, new_info, ""))
                    merged = asyncio.run(asyncio.wait_for(task, timeout=15))
                else:
                    merged = asyncio.run(self.llm.merge_answers(current, new_info, ""))
                
                if merged and len(merged) > len(current) * 0.5:  # Sanity check
                    return merged
            except Exception as e:
                logger.warning(f"LLM answer merging failed: {e}")
        
        # Fallback to simple concatenation
        if not current:
            return new_info
        
        return f"{current}\n\n{new_info}"
    
    async def _validate_answer(self, answer: str, query: str, iteration: int) -> Dict[str, Any]:
        """
        Validate answer using Vibe-Check for hallucination detection
        
        Returns:
            {
                "risk_level": "low" | "medium" | "high",
                "questions": List[str],
                "recommendations": List[str],
                "confidence_adjustment": float  # -0.2 to +0.1
            }
        """
        
        if not self.vibe_check:
            # Fallback: No validation
            return {
                "risk_level": "medium",
                "questions": [],
                "recommendations": [],
                "confidence_adjustment": 0.0
            }
        
        try:
            # Call Vibe-Check for metacognitive oversight
            result = self.vibe_check.vibe_check(
                goal=query,
                plan=f"Iteration {iteration}: Providing answer based on gathered information",
                context=answer[:500],  # First 500 chars to avoid token overload
                status="reviewing"
            )
            
            # Adjust confidence based on risk level
            confidence_adjustment = {
                "low": 0.1,      # Boost confidence
                "medium": 0.0,   # No change
                "high": -0.2     # Lower confidence
            }.get(result["risk_level"], 0.0)
            
            if result["risk_level"] == "high":
                logger.warning(f"  ⚠️  Vibe-Check: HIGH RISK detected")
                for q in result.get("questions", [])[:2]:
                    logger.warning(f"     ? {q}")
            elif result["risk_level"] == "low":
                logger.info(f"  ✅ Vibe-Check: Low risk, good quality")
            
            return {
                "risk_level": result["risk_level"],
                "questions": result.get("questions", []),
                "recommendations": result.get("recommendations", []),
                "confidence_adjustment": confidence_adjustment
            }
            
        except Exception as e:
            logger.error(f"Vibe-Check validation failed: {e}")
            return {
                "risk_level": "medium",
                "questions": [],
                "recommendations": [],
                "confidence_adjustment": 0.0
            }

