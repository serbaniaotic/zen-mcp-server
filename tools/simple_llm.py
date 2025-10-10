"""
Simple LLM Helper - For quick LLM calls without full tool overhead

Used for internal operations like gap identification and answer merging.
"""

import logging
import os
from typing import Any, Dict, List, Optional

# Import provider classes
try:
    from providers.anthropic_provider import AnthropicProvider
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from providers.openai_provider import OpenAIProvider  
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class SimpleLLM:
    """
    Simple LLM helper for internal operations
    
    Uses available providers (Anthropic, OpenAI) for quick calls.
    Designed for internal use, not exposed via MCP.
    """
    
    def __init__(self):
        self.provider = None
        
        # Try Anthropic first (usually faster for small tasks)
        if ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
            try:
                self.provider = AnthropicProvider()
                logger.info("✅ LLM initialized: Anthropic")
            except Exception as e:
                logger.warning(f"Anthropic init failed: {e}")
        
        # Fallback to OpenAI
        if not self.provider and OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.provider = OpenAIProvider()
                logger.info("✅ LLM initialized: OpenAI")
            except Exception as e:
                logger.warning(f"OpenAI init failed: {e}")
        
        if not self.provider:
            logger.warning("⚠️  No LLM provider available. Using fallback heuristics.")
    
    async def identify_gaps(self, current_answer: str, query: str) -> List[str]:
        """
        Identify knowledge gaps in current answer
        
        Returns:
            List of gap descriptions (e.g., "Need examples of X", "Missing Y details")
        """
        
        if not self.provider:
            # Fallback to heuristics
            return self._heuristic_gaps(current_answer, query)
        
        prompt = f"""Analyze this answer to identify knowledge gaps:

Query: {query}

Current Answer:
{current_answer}

List specific knowledge gaps that need to be filled. Be concise.
Format: One gap per line, starting with "- "

Example:
- Need concrete examples
- Missing best practices
- Unclear about implementation details"""
        
        try:
            # Use a small, fast model
            response = await self.provider.generate(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3  # Low temperature for analytical tasks
            )
            
            # Parse response
            gaps = []
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('- ') or line.startswith('* '):
                    gap = line[2:].strip()
                    if gap:
                        gaps.append(gap)
            
            return gaps[:5]  # Max 5 gaps
            
        except Exception as e:
            logger.error(f"Gap identification failed: {e}")
            return self._heuristic_gaps(current_answer, query)
    
    async def merge_answers(self, current_answer: str, new_info: str, query: str) -> str:
        """
        Merge new information into current answer intelligently
        
        Returns:
            Synthesized answer combining both sources
        """
        
        if not self.provider:
            # Fallback to concatenation
            return f"{current_answer}\n\n{new_info}"
        
        prompt = f"""Synthesize these information sources into a coherent answer:

Query: {query}

Current Answer:
{current_answer}

New Information:
{new_info}

Synthesize into a single, well-structured answer. Remove redundancy, organize logically.
Keep it concise but comprehensive."""
        
        try:
            response = await self.provider.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0.5  # Medium temperature for creative synthesis
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Answer merging failed: {e}")
            return f"{current_answer}\n\n{new_info}"
    
    async def extract_decisions(self, session_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract decisions from QC session history
        
        Returns:
            List of {topic, decision, rationale, confidence}
        """
        
        if not self.provider or not session_history:
            return []
        
        # Format session
        session_text = []
        for item in session_history:
            if item.get("type") == "query":
                session_text.append(f"Q: {item['content']}")
            elif item.get("type") == "answer":
                session_text.append(f"A: {item['content'][:300]}")  # Truncate long answers
        
        session_str = "\n".join(session_text[:10])  # Max 10 exchanges
        
        prompt = f"""Extract key decisions from this QC session:

{session_str}

For each decision, provide:
- Topic (2-5 words)
- Decision (1 sentence)
- Rationale (1 sentence)
- Confidence (high/medium/low)

Format as:
1. Topic: X
   Decision: Y
   Rationale: Z
   Confidence: high"""
        
        try:
            response = await self.provider.generate(
                prompt=prompt,
                max_tokens=400,
                temperature=0.3
            )
            
            # Parse response (simplified)
            decisions = []
            current = {}
            
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith(('1.', '2.', '3.', '4.', '5.')):
                    if current:
                        decisions.append(current)
                    current = {}
                elif ': ' in line:
                    key, value = line.split(': ', 1)
                    key = key.strip().lower()
                    if key in ['topic', 'decision', 'rationale', 'confidence']:
                        current[key] = value.strip()
            
            if current:
                decisions.append(current)
            
            return decisions[:5]  # Max 5 decisions
            
        except Exception as e:
            logger.error(f"Decision extraction failed: {e}")
            return []
    
    def _heuristic_gaps(self, answer: str, query: str) -> List[str]:
        """Fallback heuristic gap identification"""
        
        if len(answer) < 100:
            return ["Need more detail", "Need examples", "Need best practices"]
        elif len(answer) < 300:
            return ["Need examples", "Need best practices"]
        elif len(answer) < 600:
            return ["Need best practices"]
        else:
            return []




