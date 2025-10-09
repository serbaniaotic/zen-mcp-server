"""
Zen MCP Tool: Wiki Export
Exports conversations to wiki with hybrid database + pages approach
Implements LLM-powered summarization and auto-tagging
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List
from pydantic import Field
from datetime import datetime

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest
from .simple.base import SimpleTool

# Import notion client
try:
    from notion_client import Client
except ImportError:
    pass

FIELD_DESCRIPTIONS = {
    "action": "Action: export_from_conversation, sync_to_pages, query, update_wiki, get_status",
    "conversation_page_id": "Notion page ID from Conversation Archive",
    "wiki_page_id": "Wiki Pages database entry ID",
    "query_project": "Filter by project",
    "query_category": "Filter by category",
    "query_status": "Filter by status (draft, review, published)",
    "query_tags": "Filter by tags",
    "force_sync": "Force sync even if already synced",
}


class WikiExportRequest(ToolRequest):
    """Request model for Wiki Export tool"""

    action: str = Field(description=FIELD_DESCRIPTIONS["action"])
    conversation_page_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["conversation_page_id"])
    wiki_page_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["wiki_page_id"])
    query_project: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["query_project"])
    query_category: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["query_category"])
    query_status: Optional[str] = Field("published", description=FIELD_DESCRIPTIONS["query_status"])
    query_tags: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["query_tags"])
    force_sync: bool = Field(False, description=FIELD_DESCRIPTIONS["force_sync"])


class WikiExportTool(SimpleTool):
    """
    Wiki Export - Hybrid database + pages wiki system

    Features:
    - Export conversations to Wiki Pages database with LLM summary
    - Auto-detect project, category, related projects, tags
    - Sync Wiki Pages database → Regular Notion pages (themed)
    - Query wiki content
    - Track published page IDs
    """

    def __init__(self):
        super().__init__()
        self.notion_api_key = os.getenv("NOTION_API_KEY")

        # Load from .env.wiki if available
        env_wiki_path = Path.home() / "code/tamdac/.env.wiki"
        if env_wiki_path.exists():
            with open(env_wiki_path) as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value

        self.conversation_db_id = os.getenv("CONVERSATION_ARCHIVE_DB_ID")
        self.projects_db_id = os.getenv("PROJECTS_DB_ID")
        self.wiki_pages_db_id = os.getenv("WIKI_PAGES_DB_ID")

        if not self.notion_api_key:
            raise ValueError("NOTION_API_KEY must be set")

        self.notion = Client(auth=self.notion_api_key)

    def get_name(self) -> str:
        return "wiki_export"

    def get_description(self) -> str:
        return "Export conversations to wiki with LLM summary and sync to themed pages"

    def get_system_prompt(self) -> str:
        return """You are a wiki export system that converts conversations into structured wiki content.

Your role is to:
1. Export conversations from archive to Wiki Pages database
2. Use LLM to summarize conversations into wiki article format
3. Auto-detect: Primary Project, Related Projects, Category, Tags
4. Sync published wiki pages to regular Notion pages (themed)
5. Enable queries by project/category/tags

CRITICAL: Always use LLM summarization to create high-quality wiki articles, not raw transcripts.

When exporting conversations:
- Summarize key decisions, implementations, and outcomes
- Extract code snippets and technical specs
- Identify cross-project patterns
- Tag appropriately for future retrieval"""

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """Return tool-specific field definitions"""
        return {
            "action": {
                "type": "string",
                "description": "Action to perform",
                "enum": ["export_from_conversation", "sync_to_pages", "query", "update_wiki", "get_status"]
            },
            "conversation_page_id": {
                "type": "string",
                "description": "Notion page ID from Conversation Archive"
            },
            "wiki_page_id": {
                "type": "string",
                "description": "Wiki Pages database entry ID"
            },
            "query_project": {
                "type": "string",
                "description": "Filter by project"
            },
            "query_category": {
                "type": "string",
                "description": "Filter by category"
            },
            "query_status": {
                "type": "string",
                "description": "Filter by status",
                "default": "published"
            },
            "query_tags": {
                "type": "string",
                "description": "Filter by tags (comma-separated)"
            },
            "force_sync": {
                "type": "boolean",
                "description": "Force sync even if already synced",
                "default": False
            }
        }

    def prepare_prompt(self, request: WikiExportRequest, **kwargs) -> str:
        """Prepare the prompt for wiki export"""

        if request.action == "export_from_conversation":
            return f"""Export conversation to wiki with LLM summary.

Conversation ID: {request.conversation_page_id}

This will:
1. Fetch conversation content from Conversation Archive
2. Use LLM (Gemini Pro) to summarize into wiki article
3. Auto-detect: Primary Project, Related Projects, Category, Tags
4. Create entry in Wiki Pages database with status="draft"
5. Link to source conversation
6. Return wiki page ID for future updates

Execute export with LLM summarization."""

        elif request.action == "sync_to_pages":
            return f"""Sync Wiki Pages database to regular Notion pages.

Force Sync: {request.force_sync}

This will:
1. Query Wiki Pages where Status="published"
2. For each page:
   - Create/update regular Notion page
   - Organize by Primary Project
   - Store Published Page ID in database
3. Result: Clean themed wiki tree

Execute wiki sync."""

        elif request.action == "query":
            return f"""Query wiki content.

Project: {request.query_project or 'all'}
Category: {request.query_category or 'all'}
Status: {request.query_status}
Tags: {request.query_tags or 'all'}

Execute wiki query."""

        elif request.action == "update_wiki":
            return f"""Update wiki page.

Wiki Page ID: {request.wiki_page_id}

This will update wiki page metadata or content.

Execute wiki update."""

        elif request.action == "get_status":
            return f"""Get wiki page status.

Wiki Page ID: {request.wiki_page_id}

This will retrieve current status and sync info.

Execute status check."""

        return f"Unknown action: {request.action}"

    async def _call(self, request: WikiExportRequest, **kwargs) -> Dict[str, Any]:
        """Execute the wiki export logic"""

        # Check if databases are configured
        if not self.wiki_pages_db_id:
            return {
                "success": False,
                "error": "Wiki Pages database not configured. Please create databases manually and set WIKI_PAGES_DB_ID in .env.wiki",
                "setup_guide": "See NOTION-WIKI-SETUP-GUIDE.md for instructions"
            }

        try:
            if request.action == "export_from_conversation":
                return await self._export_from_conversation(request)
            elif request.action == "sync_to_pages":
                return await self._sync_to_pages(request)
            elif request.action == "query":
                return await self._query_wiki(request)
            elif request.action == "update_wiki":
                return await self._update_wiki(request)
            elif request.action == "get_status":
                return await self._get_status(request)
            else:
                return {"success": False, "error": f"Unknown action: {request.action}"}

        except Exception as e:
            return {"success": False, "error": f"Wiki export error: {str(e)}"}

    async def _export_from_conversation(self, request: WikiExportRequest) -> Dict[str, Any]:
        """Export conversation to wiki with LLM summary"""

        if not request.conversation_page_id:
            return {"success": False, "error": "conversation_page_id required"}

        # TODO: Fetch conversation content from Conversation Archive
        # TODO: Call LLM (Gemini Pro) to summarize into wiki article
        # TODO: Auto-detect project, category, related projects, tags
        # TODO: Create entry in Wiki Pages database

        return {
            "success": False,
            "error": "Export from conversation not yet implemented. Please create databases first.",
            "next_steps": [
                "1. Create Projects database manually",
                "2. Create Wiki Pages database manually",
                "3. Save database IDs to .env.wiki",
                "4. Tool will be fully functional"
            ]
        }

    async def _sync_to_pages(self, request: WikiExportRequest) -> Dict[str, Any]:
        """Sync Wiki Pages database to regular Notion pages"""

        # TODO: Query Wiki Pages where Status="published"
        # TODO: For each, create/update regular Notion page
        # TODO: Store Published Page ID

        return {
            "success": False,
            "error": "Sync to pages not yet implemented. Please create databases first."
        }

    async def _query_wiki(self, request: WikiExportRequest) -> Dict[str, Any]:
        """Query wiki content"""

        if not self.wiki_pages_db_id:
            return {"success": False, "error": "Wiki Pages database not configured"}

        filters = []

        if request.query_status:
            filters.append({
                "property": "Status",
                "select": {"equals": request.query_status}
            })

        if request.query_project:
            # TODO: Query by Primary Project relation
            pass

        if request.query_category:
            filters.append({
                "property": "Category",
                "select": {"equals": request.query_category}
            })

        query = {"database_id": self.wiki_pages_db_id}
        if filters:
            query["filter"] = {"and": filters} if len(filters) > 1 else filters[0]

        response = self.notion.databases.query(**query)

        results = []
        for page in response["results"]:
            title_prop = page["properties"]["Title"]
            title = title_prop["title"][0]["plain_text"] if title_prop["title"] else "Untitled"

            results.append({
                "wiki_page_id": page["id"],
                "title": title,
                "url": f"https://notion.so/{page['id'].replace('-', '')}"
            })

        return {
            "success": True,
            "action": "query",
            "count": len(results),
            "results": results
        }

    async def _update_wiki(self, request: WikiExportRequest) -> Dict[str, Any]:
        """Update wiki page"""
        return {"success": False, "error": "Not yet implemented"}

    async def _get_status(self, request: WikiExportRequest) -> Dict[str, Any]:
        """Get wiki page status"""
        if not request.wiki_page_id:
            return {"success": False, "error": "wiki_page_id required"}

        page = self.notion.pages.retrieve(page_id=request.wiki_page_id)

        title_prop = page["properties"]["Title"]
        title = title_prop["title"][0]["plain_text"] if title_prop["title"] else "Untitled"

        status_prop = page["properties"]["Status"]
        status = status_prop["select"]["name"] if status_prop.get("select") else None

        return {
            "success": True,
            "wiki_page_id": request.wiki_page_id,
            "title": title,
            "status": status,
            "url": f"https://notion.so/{page['id'].replace('-', '')}"
        }
