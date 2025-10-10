"""
WebFetch tool - Fetch and convert web content to markdown

This tool fetches content from URLs and converts HTML to markdown for easy consumption
by AI models. It handles redirects, HTTP/HTTPS upgrades, and provides clean markdown output.
"""

import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from pydantic import Field

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from .simple.base import SimpleTool

logger = logging.getLogger(__name__)

WEBFETCH_FIELD_DESCRIPTIONS = {
    "url": "The URL to fetch content from (HTTP/HTTPS)",
    "prompt": "What information you want to extract from the page",
    "timeout": "Request timeout in seconds (default: 30)",
}


class WebFetchRequest(ToolRequest):
    """Request model for WebFetch tool"""

    url: str = Field(..., description=WEBFETCH_FIELD_DESCRIPTIONS["url"])
    prompt: str = Field(..., description=WEBFETCH_FIELD_DESCRIPTIONS["prompt"])
    timeout: Optional[int] = Field(30, description=WEBFETCH_FIELD_DESCRIPTIONS["timeout"])


class WebFetchTool(SimpleTool):
    """
    Fetch web content and convert to markdown for AI consumption.

    Features:
    - Automatic HTTP -> HTTPS upgrade
    - Redirect handling
    - HTML to Markdown conversion
    - Clean, AI-friendly output
    """

    def get_name(self) -> str:
        return "webfetch"

    def get_description(self) -> str:
        return (
            "Fetches content from a specified URL and processes it using an AI model. "
            "Takes a URL and a prompt as input, fetches the URL content, converts HTML to markdown, "
            "and processes the content with the prompt. "
            "Use this tool when you need to retrieve and analyze web content."
        )

    def get_system_prompt(self) -> str:
        return """You are a web content analyzer that helps users extract and understand information from web pages.

Your role is to:
1. Receive web page content in markdown format
2. Answer the user's specific question about the content
3. Extract relevant information clearly and concisely
4. Cite specific sections when helpful
5. Indicate if the content doesn't contain the requested information

Be direct and factual. Focus on answering the user's question with information from the page.
If the page content is unclear or incomplete, say so."""

    def get_model_category(self):
        """WebFetch uses fast models for efficiency"""
        from tools.models import ToolModelCategory
        return ToolModelCategory.FAST_RESPONSE

    def get_default_temperature(self) -> float:
        return 0.3  # Lower temperature for factual information extraction

    def get_request_model(self):
        return WebFetchRequest

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """Define tool-specific fields for WebFetch"""
        return {
            "url": {
                "type": "string",
                "format": "uri",
                "description": WEBFETCH_FIELD_DESCRIPTIONS["url"],
            },
            "prompt": {
                "type": "string",
                "description": WEBFETCH_FIELD_DESCRIPTIONS["prompt"],
            },
            "timeout": {
                "type": "integer",
                "minimum": 1,
                "maximum": 120,
                "description": WEBFETCH_FIELD_DESCRIPTIONS["timeout"],
            },
        }

    def get_required_fields(self) -> list[str]:
        """Required fields for WebFetch"""
        return ["url", "prompt"]

    def get_input_schema(self) -> dict[str, Any]:
        """Generate input schema for WebFetch tool"""
        required_fields = ["url", "prompt"]
        if self.is_effective_auto_mode():
            required_fields.append("model")

        schema = {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": WEBFETCH_FIELD_DESCRIPTIONS["url"],
                },
                "prompt": {
                    "type": "string",
                    "description": WEBFETCH_FIELD_DESCRIPTIONS["prompt"],
                },
                "timeout": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 120,
                    "description": WEBFETCH_FIELD_DESCRIPTIONS["timeout"],
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

    def _fetch_url(self, url: str, timeout: int) -> tuple[str, str, Optional[str]]:
        """
        Fetch content from URL.

        Returns:
            tuple: (content, final_url, error_message)
        """
        # Upgrade HTTP to HTTPS automatically
        parsed = urlparse(url)
        if parsed.scheme == "http":
            url = url.replace("http://", "https://", 1)
            logger.info(f"Auto-upgraded HTTP to HTTPS: {url}")

        try:
            response = requests.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ZenMCP/1.0; +https://github.com/serbaniaotic/zen-mcp-server)"
                }
            )
            response.raise_for_status()

            # Check for redirect to different host
            final_url = response.url
            if urlparse(final_url).netloc != urlparse(url).netloc:
                logger.info(f"Redirected from {url} to {final_url}")
                # Return redirect notice in special format
                return "", final_url, f"REDIRECT: {final_url}"

            return response.text, final_url, None

        except requests.exceptions.Timeout:
            return "", url, f"Request timeout after {timeout} seconds"
        except requests.exceptions.ConnectionError as e:
            return "", url, f"Connection error: {str(e)}"
        except requests.exceptions.HTTPError as e:
            return "", url, f"HTTP error: {e.response.status_code} {e.response.reason}"
        except Exception as e:
            return "", url, f"Error fetching URL: {str(e)}"

    def _html_to_markdown(self, html: str) -> str:
        """
        Convert HTML to markdown.

        Simple conversion focusing on readability:
        - Remove scripts, styles
        - Convert common tags
        - Preserve structure
        """
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Convert headings
        html = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n', html, flags=re.DOTALL | re.IGNORECASE)

        # Convert links
        html = re.sub(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'[\2](\1)', html, flags=re.IGNORECASE)

        # Convert bold/strong
        html = re.sub(r'<(b|strong)[^>]*>(.*?)</\1>', r'**\2**', html, flags=re.IGNORECASE)

        # Convert italic/em
        html = re.sub(r'<(i|em)[^>]*>(.*?)</\1>', r'*\2*', html, flags=re.IGNORECASE)

        # Convert code
        html = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', html, flags=re.IGNORECASE)

        # Convert lists
        html = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', html, flags=re.DOTALL | re.IGNORECASE)

        # Convert paragraphs
        html = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', html, flags=re.DOTALL | re.IGNORECASE)

        # Convert breaks
        html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)

        # Remove remaining HTML tags
        html = re.sub(r'<[^>]+>', '', html)

        # Decode common HTML entities
        html = html.replace('&nbsp;', ' ')
        html = html.replace('&amp;', '&')
        html = html.replace('&lt;', '<')
        html = html.replace('&gt;', '>')
        html = html.replace('&quot;', '"')
        html = html.replace('&#39;', "'")

        # Clean up whitespace
        html = re.sub(r'\n\n\n+', '\n\n', html)
        html = re.sub(r' +', ' ', html)

        return html.strip()

    async def prepare_prompt(self, request: WebFetchRequest) -> str:
        """
        Fetch URL and prepare prompt with content.
        """
        # Fetch the URL
        content, final_url, error = self._fetch_url(request.url, request.timeout or 30)

        if error:
            if error.startswith("REDIRECT:"):
                # Special redirect handling
                redirect_url = error.split(":", 1)[1].strip()
                return f"""The URL redirected to a different host: {redirect_url}

To fetch content from the redirect URL, make a new WebFetch request with:
url: {redirect_url}
prompt: {request.prompt}"""
            else:
                # Regular error
                return f"Error fetching {request.url}: {error}"

        # Convert HTML to markdown
        markdown = self._html_to_markdown(content)

        # Limit content size (roughly 100K tokens = ~400K chars)
        max_chars = 400_000
        if len(markdown) > max_chars:
            markdown = markdown[:max_chars] + f"\n\n[Content truncated - original was {len(markdown):,} characters]"
            logger.warning(f"Content truncated from {len(markdown):,} to {max_chars:,} chars")

        # Build prompt
        prompt_parts = [
            f"Web page content from: {final_url}",
            "",
            "---",
            "",
            markdown,
            "",
            "---",
            "",
            f"User question: {request.prompt}",
        ]

        return "\n".join(prompt_parts)
