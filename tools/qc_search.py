"""
QC Search Tool - Discover relevant QC sessions

Provides semantic search and keyword matching to find relevant QC sessions.
Supports context filtering, ranking, and chain expansion.

Design: Day 6 Task-1 (qc-workflow-scripts)
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime
from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.shared.base_tool import BaseTool
from tools.models import ToolOutput
from mcp.types import TextContent

logger = logging.getLogger(__name__)


class QCSearchRequest(ToolRequest):
    """Request model for QC Search tool"""
    query: str = Field(..., description="Search query (topic, keyword, or question)")
    limit: Optional[int] = Field(5, description="Maximum number of results to return")
    context_filter: Optional[str] = Field(None, description="Filter by context (task-N, ticket-N, project name)")
    include_body: Optional[bool] = Field(False, description="Include full body in results (default: summaries only)")


class QCSearchTool(BaseTool):
    """
    QC Search tool for discovering relevant QC sessions.
    
    Provides keyword search, context filtering, and ranking.
    Does not require AI model calls - pure search functionality.
    """
    
    def __init__(self):
        super().__init__()
        self.qc_dir = Path.home() / "code" / "qc"
        self.cache_file = self.qc_dir / ".qc_search_index.json"
        self.index_cache = None
        self.cache_age = None
    
    def get_name(self) -> str:
        return "qc_search"
    
    def get_description(self) -> str:
        return (
            "Search for relevant QC (Quick Chat) sessions by topic, keyword, or context. "
            "Returns ranked results with summaries. Use for discovering past design decisions and patterns."
        )
    
    def get_system_prompt(self) -> str:
        return """You are a QC search assistant.

Your role is to help find relevant QC sessions based on search queries.
Return ranked results with clear summaries."""
    
    def get_default_temperature(self) -> float:
        return 0.0  # Deterministic search
    
    def get_model_category(self) -> "ToolModelCategory":
        from tools.models import ToolModelCategory
        return ToolModelCategory.FAST_RESPONSE
    
    def get_request_model(self):
        return QCSearchRequest
    
    def requires_model(self) -> bool:
        """Search doesn't require AI model - pure file search"""
        return False
    
    def get_input_schema(self) -> dict[str, Any]:
        """Return input schema for QC Search"""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (topic, keyword, or question)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5
                },
                "context_filter": {
                    "type": "string",
                    "description": "Filter by context (task-N, ticket-N, project name)"
                },
                "include_body": {
                    "type": "boolean",
                    "description": "Include full body in results (default: summaries only)",
                    "default": False
                }
            },
            "required": ["query"]
        }
    
    async def prepare_prompt(
        self,
        arguments: dict[str, Any],
        system_prompts: list[str],
        conversation_history: Optional[list[dict[str, Any]]] = None
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Search tool doesn't use AI model, so this is a no-op.
        Returns empty prompt and history.
        """
        return "", []
    
    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute QC search"""
        
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        context_filter = arguments.get("context_filter")
        include_body = arguments.get("include_body", False)
        
        if not query:
            error_output = ToolOutput(
                status="error", 
                content="Query parameter is required", 
                content_type="text"
            )
            return [TextContent(type="text", text=error_output.model_dump_json())]
        
        try:
            # Build/refresh index if needed
            await self._ensure_index_fresh()
            
            # Search index
            results = await self._search(query, limit, context_filter)
            
            # Format results
            output = self._format_results(results, include_body)
            
            result = ToolOutput(
                status="success",
                content=output,
                content_type="markdown"
            )
            
            return [TextContent(type="text", text=result.model_dump_json())]
            
        except Exception as e:
            logger.error(f"Error in QC search: {e}", exc_info=True)
            error_output = ToolOutput(
                status="error",
                content=f"Search failed: {str(e)}",
                content_type="text"
            )
            return [TextContent(type="text", text=error_output.model_dump_json())]
    
    async def _ensure_index_fresh(self, max_age_seconds: int = 3600) -> None:
        """Ensure search index is fresh (rebuild if older than max_age)"""
        
        # Check if cache exists and is fresh
        if self.index_cache and self.cache_age:
            age = (datetime.now() - self.cache_age).total_seconds()
            if age < max_age_seconds:
                return  # Cache is fresh
        
        # Build/rebuild index
        await self._build_index()
    
    async def _build_index(self) -> None:
        """Build search index from all QC files"""
        
        logger.info("Building QC search index...")
        
        if not self.qc_dir.exists():
            logger.warning(f"QC directory not found: {self.qc_dir}")
            self.index_cache = []
            self.cache_age = datetime.now()
            return
        
        index = []
        
        # Find all QC files
        for year_dir in sorted(self.qc_dir.glob("20*"), reverse=True):
            if not year_dir.is_dir():
                continue
            
            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir():
                    continue
                
                for day_dir in sorted(month_dir.iterdir(), reverse=True):
                    if not day_dir.is_dir():
                        continue
                    
                    for qc_file in day_dir.glob("QC-*.md"):
                        try:
                            entry = await self._parse_qc_file(qc_file)
                            if entry:
                                index.append(entry)
                        except Exception as e:
                            logger.warning(f"Failed to parse {qc_file}: {e}")
                            continue
        
        # Cache index
        self.index_cache = index
        self.cache_age = datetime.now()
        
        # Save to disk
        try:
            cache_data = {
                'generated': self.cache_age.isoformat(),
                'count': len(index),
                'entries': index
            }
            self.cache_file.write_text(json.dumps(cache_data, indent=2), encoding='utf-8')
            logger.info(f"✅ Indexed {len(index)} QC sessions")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    async def _parse_qc_file(self, qc_file: Path) -> Optional[dict[str, Any]]:
        """Parse a QC file and extract searchable metadata"""
        
        try:
            content = qc_file.read_text(encoding='utf-8')
            
            # Must have YAML frontmatter
            if not content.startswith('---'):
                return None
            
            parts = content.split('---', 2)
            if len(parts) < 3:
                return None
            
            frontmatter = parts[1]
            body = parts[2]
            
            # Extract QC ID from filename
            qc_id = qc_file.stem.split('-')[0] + '-' + qc_file.stem.split('-')[1]
            
            # Parse YAML fields
            metadata = {'id': qc_id, 'file': str(qc_file)}
            
            for line in frontmatter.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"')
                    
                    # Skip empty values
                    if not value or value.lower() in ['null', 'none', '[]']:
                        continue
                    
                    # Handle lists
                    if key in ['context', 'participants']:
                        # For now, just store as comma-separated string
                        if value.startswith('[') and value.endswith(']'):
                            value = value[1:-1].strip()
                    
                    metadata[key] = value
            
            # Extract title from first h1
            title = "Untitled"
            for line in body.split('\n'):
                if line.startswith('# '):
                    title = line[2:].strip()
                    # Remove QC-XXX: prefix if present
                    if ':' in title:
                        title = title.split(':', 1)[1].strip()
                    break
            
            metadata['title'] = title
            
            # Extract searchable text (title + key sections)
            searchable = f"{title} {qc_id} "
            
            # Add context keywords
            if 'context' in metadata:
                searchable += f"{metadata['context']} "
            
            # Extract key sections
            for section in ['## Session Context', '## Key Questions', '## Insights']:
                if section in body:
                    section_content = body.split(section, 1)[1]
                    section_content = section_content.split('##', 1)[0]
                    # First 200 chars
                    searchable += section_content[:200] + " "
            
            metadata['searchable_text'] = searchable.lower()
            
            # Extract summary (first paragraph of Session Context)
            if '## Session Context' in body:
                context_section = body.split('## Session Context', 1)[1]
                context_section = context_section.split('##', 1)[0]
                paragraphs = [p.strip() for p in context_section.split('\n\n') if p.strip() and not p.strip().startswith('#')]
                if paragraphs:
                    metadata['summary'] = paragraphs[0][:300]
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error parsing {qc_file}: {e}")
            return None
    
    async def _search(
        self, 
        query: str, 
        limit: int, 
        context_filter: Optional[str]
    ) -> list[dict[str, Any]]:
        """Search index for matching QC sessions"""
        
        if not self.index_cache:
            return []
        
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        results = []
        
        for entry in self.index_cache:
            # Apply context filter
            if context_filter:
                context_match = False
                entry_context = entry.get('context', '')
                if isinstance(entry_context, str):
                    if context_filter.lower() in entry_context.lower():
                        context_match = True
                
                # Also check action field
                if not context_match:
                    action = entry.get('action', '')
                    if context_filter.lower() in action.lower():
                        context_match = True
                
                if not context_match:
                    continue
            
            # Calculate relevance score
            searchable = entry.get('searchable_text', '')
            
            score = 0.0
            
            # Exact phrase match (highest score)
            if query_lower in searchable:
                score += 10.0
            
            # Term matching
            for term in query_terms:
                if term in searchable:
                    score += 1.0
            
            # Boost for matches in title
            title = entry.get('title', '').lower()
            for term in query_terms:
                if term in title:
                    score += 2.0
            
            # Boost for matches in QC ID
            qc_id = entry.get('id', '').lower()
            if query_lower in qc_id:
                score += 5.0
            
            if score > 0:
                entry['_score'] = score
                results.append(entry)
        
        # Sort by score (descending)
        results.sort(key=lambda x: x.get('_score', 0), reverse=True)
        
        # Apply limit
        return results[:limit]
    
    def _format_results(self, results: list[dict[str, Any]], include_body: bool) -> str:
        """Format search results as markdown"""
        
        if not results:
            return "# No Results\n\nNo QC sessions found matching your query."
        
        output = [f"# QC Search Results ({len(results)} found)\n"]
        
        for i, result in enumerate(results, 1):
            qc_id = result.get('id', 'Unknown')
            title = result.get('title', 'Untitled')
            date = result.get('date', 'Unknown')
            qc_type = result.get('type', 'Unknown')
            status = result.get('status', 'Unknown')
            score = result.get('_score', 0)
            
            output.append(f"## {i}. {qc_id}: {title}")
            output.append(f"**Score**: {score:.1f} | **Date**: {date} | **Type**: {qc_type} | **Status**: {status}")
            
            # Add summary
            summary = result.get('summary', 'No summary available')
            output.append(f"\n{summary}\n")
            
            # Add context
            context = result.get('context', '')
            if context:
                output.append(f"**Context**: {context}")
            
            # Add action
            action = result.get('action', '')
            if action and action not in ['none', 'null']:
                output.append(f"**Action**: {action}")
            
            # Add file path
            file_path = result.get('file', '')
            if file_path:
                output.append(f"**File**: `{file_path}`")
            
            output.append("")  # Blank line
        
        return "\n".join(output)

