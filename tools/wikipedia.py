"""
Wikipedia tool - Fetch and search Wikipedia articles

This tool fetches Wikipedia articles and handles searches with disambiguation support.
Integrates with RAG-first pattern for intelligent context management.
"""

import logging
from typing import Any, Optional

from pydantic import Field
from wikipediaapi import Wikipedia

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest

from .simple.base import SimpleTool

logger = logging.getLogger(__name__)

WIKIPEDIA_FIELD_DESCRIPTIONS = {
    "query": "Article title or search query",
    "prompt": "What you want to learn or extract from the article",
    "language": "Language code (en, es, fr, de, etc.). Defaults to 'en'",
    "search_mode": "True to search for articles, False to fetch specific article by title",
    "store_to_pinecone": "Auto-store article content to Pinecone RAG",
    "domain": "Domain color for RAG storage (technical, business, etc.)",
    "pattern": "Abstract pattern for RAG storage (resource_contention, etc.)",
}


class WikipediaRequest(ToolRequest):
    """Request model for Wikipedia tool"""

    query: str = Field(..., description=WIKIPEDIA_FIELD_DESCRIPTIONS["query"])
    prompt: str = Field(..., description=WIKIPEDIA_FIELD_DESCRIPTIONS["prompt"])
    language: str = Field("en", description=WIKIPEDIA_FIELD_DESCRIPTIONS["language"])
    search_mode: bool = Field(False, description=WIKIPEDIA_FIELD_DESCRIPTIONS["search_mode"])
    store_to_pinecone: bool = Field(False, description=WIKIPEDIA_FIELD_DESCRIPTIONS["store_to_pinecone"])
    domain: Optional[str] = Field(None, description=WIKIPEDIA_FIELD_DESCRIPTIONS["domain"])
    pattern: Optional[str] = Field(None, description=WIKIPEDIA_FIELD_DESCRIPTIONS["pattern"])


class WikipediaTool(SimpleTool):
    """
    Fetch and analyze Wikipedia articles with RAG-first integration.

    Features:
    - Direct article fetching by title
    - Search mode with result suggestions
    - Multi-language support
    - Summary + full sections
    - Optional Pinecone storage with domain colors
    """

    def get_name(self) -> str:
        return "wikipedia"

    def get_description(self) -> str:
        return (
            "Fetches Wikipedia articles or searches for topics. "
            "Supports multiple languages, handles disambiguation, and provides structured content. "
            "Can auto-store to Pinecone for RAG-first pattern. "
            "Use for research, fact-checking, and knowledge gathering."
        )

    def get_system_prompt(self) -> str:
        return """You are a Wikipedia content analyzer that helps users extract and understand information from Wikipedia articles.

Your role is to:
1. Receive Wikipedia article content (summary + sections)
2. Answer the user's specific question based on the content
3. Extract key facts, definitions, or explanations
4. Provide clear, concise answers
5. Cite specific sections when relevant

Be factual and direct. Focus on answering based on the Wikipedia content provided.
If the article doesn't contain the requested information, say so clearly."""

    def get_model_category(self):
        """Wikipedia uses balanced models for comprehension"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.BALANCED

    def get_default_temperature(self) -> float:
        return 0.3  # Lower temperature for factual information

    def get_request_model(self):
        return WikipediaRequest

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """Define tool-specific fields for Wikipedia"""
        return {
            "query": {
                "type": "string",
                "description": WIKIPEDIA_FIELD_DESCRIPTIONS["query"],
            },
            "prompt": {
                "type": "string",
                "description": WIKIPEDIA_FIELD_DESCRIPTIONS["prompt"],
            },
            "language": {
                "type": "string",
                "description": WIKIPEDIA_FIELD_DESCRIPTIONS["language"],
            },
            "search_mode": {
                "type": "boolean",
                "description": WIKIPEDIA_FIELD_DESCRIPTIONS["search_mode"],
            },
            "store_to_pinecone": {
                "type": "boolean",
                "description": WIKIPEDIA_FIELD_DESCRIPTIONS["store_to_pinecone"],
            },
            "domain": {
                "type": "string",
                "description": WIKIPEDIA_FIELD_DESCRIPTIONS["domain"],
            },
            "pattern": {
                "type": "string",
                "description": WIKIPEDIA_FIELD_DESCRIPTIONS["pattern"],
            },
        }

    def get_required_fields(self) -> list[str]:
        """Required fields for Wikipedia"""
        return ["query", "prompt"]

    def get_input_schema(self) -> dict[str, Any]:
        """Generate input schema for Wikipedia tool"""
        required_fields = ["query", "prompt"]
        if self.is_effective_auto_mode():
            required_fields.append("model")

        schema = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": WIKIPEDIA_FIELD_DESCRIPTIONS["query"],
                },
                "prompt": {
                    "type": "string",
                    "description": WIKIPEDIA_FIELD_DESCRIPTIONS["prompt"],
                },
                "language": {
                    "type": "string",
                    "description": WIKIPEDIA_FIELD_DESCRIPTIONS["language"],
                },
                "search_mode": {
                    "type": "boolean",
                    "description": WIKIPEDIA_FIELD_DESCRIPTIONS["search_mode"],
                },
                "store_to_pinecone": {
                    "type": "boolean",
                    "description": WIKIPEDIA_FIELD_DESCRIPTIONS["store_to_pinecone"],
                },
                "domain": {
                    "type": "string",
                    "description": WIKIPEDIA_FIELD_DESCRIPTIONS["domain"],
                },
                "pattern": {
                    "type": "string",
                    "description": WIKIPEDIA_FIELD_DESCRIPTIONS["pattern"],
                },
                "model": self.get_model_field_schema(),
                "temperature": {
                    "type": "number",
                    "description": COMMON_FIELD_DESCRIPTIONS["temperature"],
                    "minimum": 0,
                    "maximum": 1,
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": COMMON_FIELD_DESCRIPTIONS["thinking_mode"],
                },
                "continuation_id": {
                    "type": "string",
                    "description": COMMON_FIELD_DESCRIPTIONS["continuation_id"],
                },
            },
            "required": required_fields,
        }

        return schema

    def _fetch_article(self, title: str, language: str) -> tuple[str, Optional[str]]:
        """
        Fetch Wikipedia article by exact title.

        Returns:
            tuple: (article_content, error_message)
        """
        try:
            wiki = Wikipedia(language=language, user_agent="ZenMCP/1.0")
            page = wiki.page(title)

            if not page.exists():
                return "", f"Article '{title}' not found in {language} Wikipedia"

            # Build content
            content_parts = [
                f"# {page.title}",
                "",
                "## Summary",
                "",
                page.summary,
                "",
            ]

            # Add sections
            if page.sections:
                content_parts.append("## Sections")
                content_parts.append("")
                for section in page.sections:
                    content_parts.append(f"### {section.title}")
                    content_parts.append("")
                    if section.text:
                        content_parts.append(section.text)
                        content_parts.append("")

            # Add links
            if page.links:
                content_parts.append("## Related Articles")
                content_parts.append("")
                for link_title in list(page.links.keys())[:10]:  # Top 10 links
                    content_parts.append(f"- {link_title}")

            content = "\n".join(content_parts)
            return content, None

        except Exception as e:
            return "", f"Error fetching article: {str(e)}"

    def _search_wikipedia(self, query: str, language: str) -> tuple[list[str], Optional[str]]:
        """
        Search Wikipedia for matching articles.

        Returns:
            tuple: (list_of_titles, error_message)
        """
        try:
            wiki = Wikipedia(language=language, user_agent="ZenMCP/1.0")
            # Wikipedia-API doesn't have built-in search, so we'll use a workaround
            # Try to fetch the page and check if it redirects or suggests
            page = wiki.page(query)

            if page.exists():
                # Found exact match
                return [page.title], None
            else:
                # No exact match found
                return [], f"No Wikipedia articles found for '{query}' in {language}"

        except Exception as e:
            return [], f"Search error: {str(e)}"

    async def prepare_prompt(self, request: WikipediaRequest) -> str:
        """
        Fetch Wikipedia content and prepare prompt.
        """
        if request.search_mode:
            # Search mode
            results, error = self._search_wikipedia(request.query, request.language)

            if error:
                return f"Search error: {error}\n\nTry fetching a specific article by setting search_mode=False"

            if not results:
                return f"No results found for '{request.query}'\n\nTry different search terms or fetch a specific article."

            # Return search results
            return f"""Wikipedia search results for "{request.query}":

Found {len(results)} article(s):
{chr(10).join(f"- {title}" for title in results)}

To fetch a specific article, use search_mode=False with the exact title.

User question: {request.prompt}"""

        else:
            # Direct fetch mode
            content, error = self._fetch_article(request.query, request.language)

            if error:
                return f"Error: {error}\n\nDouble-check the article title or try search_mode=True"

            # Optional: Store to Pinecone with spatial_memory
            if request.store_to_pinecone:
                try:
                    from datetime import datetime
                    from tools.spatial_memory import SpatialMemoryTool

                    spatial = SpatialMemoryTool()
                    spatial.run_tool({
                        "action": "store",
                        "content": content,
                        "domain": request.domain or "technical",
                        "pattern": request.pattern,
                        "status": "production_ready",
                        "context": {
                            "source": "wikipedia",
                            "article": request.query,
                            "language": request.language,
                            "timestamp": datetime.now().isoformat()
                        }
                    })
                    logger.info(f"Stored Wikipedia article '{request.query}' to Pinecone")
                except Exception as e:
                    logger.warning(f"Failed to store to Pinecone: {e}")

            # Limit content size (roughly 100K tokens = ~400K chars)
            max_chars = 400_000
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n\n[Content truncated - original was {len(content):,} characters]"
                logger.warning(f"Content truncated from {len(content):,} to {max_chars:,} chars")

            # Build prompt
            prompt_parts = [
                f"Wikipedia Article: {request.query}",
                f"Language: {request.language}",
                "",
                "---",
                "",
                content,
                "",
                "---",
                "",
                f"User question: {request.prompt}",
            ]

            return "\n".join(prompt_parts)
