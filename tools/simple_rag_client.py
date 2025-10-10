"""
Simple RAG Client - File-based semantic search

Since Pinecone isn't configured yet, this implements a simple
file-based RAG using existing .claude/memory.md files.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SimpleRAGClient:
    """
    Simple RAG client for searching .claude/memory.md
    
    Uses keyword matching and basic scoring. Can be replaced with
    proper vector search (Pinecone) when configured.
    """
    
    def __init__(self, memory_dir: str = None):
        if memory_dir is None:
            # Default to ~/.claude or /home/dingo/code/.claude
            home = os.path.expanduser("~")
            self.memory_dir = Path(home) / ".claude"
        else:
            self.memory_dir = Path(memory_dir)
        
        self.memory_file = self.memory_dir / "memory.md"
        
        logger.info(f"SimpleRAGClient initialized: {self.memory_file}")
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search memory for relevant entries
        
        Returns:
            List of {
                "content": str,
                "score": float,
                "metadata": dict
            }
        """
        
        if not self.memory_file.exists():
            logger.warning(f"Memory file not found: {self.memory_file}")
            return []
        
        try:
            content = self.memory_file.read_text(encoding='utf-8')
            entries = self._parse_memory_file(content)
            scored_entries = self._score_entries(entries, query)
            
            # Sort by score and return top N
            scored_entries.sort(key=lambda x: x['score'], reverse=True)
            return scored_entries[:limit]
            
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []
    
    def _parse_memory_file(self, content: str) -> List[Dict[str, Any]]:
        """Parse memory.md into structured entries"""
        
        entries = []
        
        # Split by headers (## sections)
        sections = re.split(r'\n## ', content)
        
        for section in sections[1:]:  # Skip first empty section
            lines = section.split('\n')
            title = lines[0].strip()
            body = '\n'.join(lines[1:])
            
            # Extract metadata
            metadata = {}
            for line in lines[1:10]:  # Check first 10 lines for metadata
                if line.startswith('**') and '**:' in line:
                    key = line.split('**:')[0].replace('**', '').strip()
                    value = line.split('**:')[1].strip()
                    metadata[key.lower()] = value
            
            entries.append({
                "title": title,
                "content": body,
                "metadata": metadata
            })
        
        return entries
    
    def _score_entries(self, entries: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Score entries by relevance to query"""
        
        query_words = set(self._tokenize(query.lower()))
        
        scored = []
        for entry in entries:
            # Tokenize content
            content_words = set(self._tokenize(entry['content'].lower()))
            title_words = set(self._tokenize(entry['title'].lower()))
            
            # Calculate overlap
            content_overlap = len(query_words & content_words)
            title_overlap = len(query_words & title_words)
            
            # Title matches are worth more
            score = (content_overlap + (title_overlap * 3)) / len(query_words) if query_words else 0
            
            # Boost recent entries
            if 'date' in entry['metadata']:
                # Simple boost for 2025 dates
                if '2025' in entry['metadata']['date']:
                    score *= 1.2
            
            scored.append({
                "content": entry['content'],
                "title": entry['title'],
                "score": min(score, 1.0),  # Cap at 1.0
                "metadata": entry['metadata']
            })
        
        return scored
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        
        # Filter short words and common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = [w for w in words if len(w) > 2 and w not in stop_words]
        
        return words
    
    def get_recent_decisions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent decisions from memory"""
        
        if not self.memory_file.exists():
            return []
        
        try:
            content = self.memory_file.read_text(encoding='utf-8')
            entries = self._parse_memory_file(content)
            
            # Filter for entries with decisions
            decision_entries = [
                e for e in entries 
                if 'decisions' in e['metadata'] or 'decision' in e['content'].lower()[:200]
            ]
            
            # Return most recent
            return decision_entries[:limit]
            
        except Exception as e:
            logger.error(f"Error getting recent decisions: {e}")
            return []




