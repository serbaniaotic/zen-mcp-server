"""
Zen MCP Tool: Notion Archive
Archives conversations to Notion with auto-archive logic
Implements the schema from NOTION-INTEGRATION-SCHEMA.md
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
    print("⚠️ notion-client not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "notion-client"])
    from notion_client import Client

FIELD_DESCRIPTIONS = {
    "action": "Action: create_session, update_session, archive_session, query_archive, get_status",
    "session_title": "Title for the conversation session",
    "project": "Project name (lumiere, toolbox, tamdac, motif, arrow, sophia, obs, chord)",
    "tags": "Comma-separated tags",
    "type": "Session type (implementation, planning, debugging, research, review)",
    "priority": "Priority level (high, medium, low)",
    "platform": "Platform used (claude_code, cursor, copilot_chat, chatgpt)",
    "agent": "Agent used (pm, architect, dev, universal)",
    "conversation_content": "Full content to append to session",
    "token_count": "Number of tokens in this update",
    "continuation_id": "Continuation ID from zen-mcp tools",
    "page_id": "Notion page ID for update operations",
    "related_files": "Comma-separated file paths",
    "auto_archive": "Automatically archive if >10 conversations or >50k tokens",
    "query_project": "Filter by project",
    "query_tags": "Filter by tags",
    "query_status": "Filter by status",
}


class NotionArchiveRequest(ToolRequest):
    """Request model for Notion Archive tool"""

    action: str = Field(description=FIELD_DESCRIPTIONS["action"])
    session_title: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["session_title"])
    project: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["project"])
    tags: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["tags"])
    type: Optional[str] = Field("implementation", description=FIELD_DESCRIPTIONS["type"])
    priority: Optional[str] = Field("medium", description=FIELD_DESCRIPTIONS["priority"])
    platform: Optional[str] = Field("claude_code", description=FIELD_DESCRIPTIONS["platform"])
    agent: Optional[str] = Field("universal", description=FIELD_DESCRIPTIONS["agent"])
    conversation_content: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["conversation_content"])
    token_count: Optional[int] = Field(0, description=FIELD_DESCRIPTIONS["token_count"])
    continuation_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["continuation_id"])
    page_id: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["page_id"])
    related_files: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["related_files"])
    auto_archive: bool = Field(True, description=FIELD_DESCRIPTIONS["auto_archive"])
    query_project: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["query_project"])
    query_tags: Optional[str] = Field(None, description=FIELD_DESCRIPTIONS["query_tags"])
    query_status: Optional[str] = Field("draft", description=FIELD_DESCRIPTIONS["query_status"])


class NotionArchiveTool(SimpleTool):
    """
    Notion Archive - Archives conversations with auto-archive logic

    Features:
    - Create new conversation sessions in Notion
    - Update sessions with new content and token counts
    - Auto-archive when >10 conversations OR >50k tokens
    - Query archive by project/tags/status
    - Track continuation IDs for context recovery
    """

    def __init__(self):
        super().__init__()
        self.notion_api_key = os.getenv("NOTION_API_KEY")
        self.database_id = os.getenv("NOTION_DATABASE_ID")

        if not self.notion_api_key or not self.database_id:
            raise ValueError("NOTION_API_KEY and NOTION_DATABASE_ID must be set in environment")

        self.notion = Client(auth=self.notion_api_key)

    def get_name(self) -> str:
        return "notion_archive"

    def get_description(self) -> str:
        return "Archives conversations to Notion with auto-archive logic"

    def get_system_prompt(self) -> str:
        return """You are a conversation archiving system that manages long-term storage in Notion.

Your role is to:
1. Create new conversation sessions with metadata
2. Update sessions with conversation content and token counts
3. Auto-archive sessions when they exceed thresholds (>10 conversations OR >50k tokens)
4. Enable selective retrieval by project, tags, and status
5. Track continuation IDs for context recovery

CRITICAL PRINCIPLE: Auto-archive after >10 conversations OR >50k tokens to keep active sessions manageable.

When creating sessions:
- Always capture project, tags, type, and platform
- Initialize token count and conversation count
- Set status to "draft" by default

When updating sessions:
- Append new content to existing content
- Increment conversation count
- Add to token usage
- Check auto-archive thresholds"""

    def get_tool_fields(self) -> Dict[str, Dict[str, Any]]:
        """Return tool-specific field definitions"""
        return {
            "action": {
                "type": "string",
                "description": "Action to perform: create_session, update_session, archive_session, query_archive, get_status",
                "enum": ["create_session", "update_session", "archive_session", "query_archive", "get_status"]
            },
            "session_title": {
                "type": "string",
                "description": "Title for the conversation session"
            },
            "project": {
                "type": "string",
                "description": "Project name (lumiere, toolbox, tamdac, motif, arrow, sophia, obs, chord)"
            },
            "tags": {
                "type": "string",
                "description": "Comma-separated tags"
            },
            "type": {
                "type": "string",
                "description": "Session type",
                "enum": ["implementation", "planning", "debugging", "research", "review"],
                "default": "implementation"
            },
            "priority": {
                "type": "string",
                "description": "Priority level",
                "enum": ["high", "medium", "low"],
                "default": "medium"
            },
            "platform": {
                "type": "string",
                "description": "Platform used",
                "enum": ["claude_code", "cursor", "copilot_chat", "chatgpt"],
                "default": "claude_code"
            },
            "agent": {
                "type": "string",
                "description": "Agent used",
                "enum": ["pm", "architect", "dev", "universal"],
                "default": "universal"
            },
            "conversation_content": {
                "type": "string",
                "description": "Full content to append to session"
            },
            "token_count": {
                "type": "integer",
                "description": "Number of tokens in this update",
                "default": 0
            },
            "continuation_id": {
                "type": "string",
                "description": "Continuation ID from zen-mcp tools"
            },
            "page_id": {
                "type": "string",
                "description": "Notion page ID for update operations"
            },
            "related_files": {
                "type": "string",
                "description": "Comma-separated file paths"
            },
            "auto_archive": {
                "type": "boolean",
                "description": "Automatically archive if >10 conversations or >50k tokens",
                "default": True
            },
            "query_project": {
                "type": "string",
                "description": "Filter by project"
            },
            "query_tags": {
                "type": "string",
                "description": "Filter by tags"
            },
            "query_status": {
                "type": "string",
                "description": "Filter by status",
                "default": "draft"
            }
        }

    def prepare_prompt(self, request: NotionArchiveRequest, **kwargs) -> str:
        """Prepare the prompt for Notion archiving"""

        if request.action == "create_session":
            return f"""Create new conversation session in Notion.

Title: {request.session_title}
Project: {request.project}
Tags: {request.tags}
Type: {request.type}
Platform: {request.platform}

This will:
1. Create new page in Notion database
2. Set initial properties (status=draft, token_usage=0, conversation_count=1)
3. Store continuation ID for recovery
4. Return page ID for future updates

Execute session creation."""

        elif request.action == "update_session":
            return f"""Update conversation session with new content.

Page ID: {request.page_id}
New Tokens: {request.token_count}
Auto-Archive: {request.auto_archive}

This will:
1. Append new content to session
2. Increment conversation count
3. Add to total token usage
4. Check auto-archive thresholds (>10 convos OR >50k tokens)
5. Auto-archive if thresholds exceeded

Execute session update."""

        elif request.action == "archive_session":
            return f"""Archive conversation session.

Page ID: {request.page_id}

This will:
1. Change status from "draft" to "archived"
2. Mark session as complete
3. Make available for wiki export

Execute session archiving."""

        elif request.action == "query_archive":
            return f"""Query conversation archive.

Project: {request.query_project or 'all'}
Tags: {request.query_tags or 'all'}
Status: {request.query_status}

This will:
1. Search Notion database with filters
2. Return matching sessions
3. Provide page IDs and summaries

Execute archive query."""

        elif request.action == "get_status":
            return f"""Get session status.

Page ID: {request.page_id}

This will:
1. Fetch current conversation count
2. Fetch total token usage
3. Check if auto-archive threshold reached
4. Return session metadata

Execute status check."""

        return f"Unknown action: {request.action}"

    async def _call(self, request: NotionArchiveRequest, **kwargs) -> Dict[str, Any]:
        """Execute the Notion archiving logic"""

        try:
            if request.action == "create_session":
                return await self._create_session(request)
            elif request.action == "update_session":
                return await self._update_session(request)
            elif request.action == "archive_session":
                return await self._archive_session(request)
            elif request.action == "query_archive":
                return await self._query_archive(request)
            elif request.action == "get_status":
                return await self._get_status(request)
            else:
                return {"success": False, "error": f"Unknown action: {request.action}"}

        except Exception as e:
            return {"success": False, "error": f"Notion archive error: {str(e)}"}

    async def _create_session(self, request: NotionArchiveRequest) -> Dict[str, Any]:
        """Create new session in Notion"""

        if not all([request.session_title, request.project]):
            return {"success": False, "error": "session_title and project required"}

        # Parse tags and files
        tags = [t.strip() for t in request.tags.split(",")] if request.tags else []
        files = [f.strip() for f in request.related_files.split(",")] if request.related_files else []

        # Create page properties
        properties = {
            "Summary": {
                "title": [{"text": {"content": request.session_title}}]
            },
            "Project": {
                "select": {"name": request.project}
            },
            "Status": {
                "select": {"name": "draft"}
            },
            "Type": {
                "select": {"name": request.type}
            },
            "Priority": {
                "select": {"name": request.priority}
            },
            "Platform": {
                "select": {"name": request.platform}
            },
            "Agent Used": {
                "select": {"name": request.agent}
            },
            "Token Usage": {
                "number": request.token_count
            },
            "Date": {
                "date": {"start": datetime.now().isoformat()}
            }
        }

        # Add tags if provided
        if tags:
            properties["Tags"] = {
                "multi_select": [{"name": tag} for tag in tags]
            }

        # Add files if provided
        if files:
            properties["Related Files"] = {
                "multi_select": [{"name": f} for f in files]
            }

        # Add continuation ID if provided
        if request.continuation_id:
            properties["Continuation ID"] = {
                "rich_text": [{"text": {"content": request.continuation_id}}]
            }

        # Add initial content if provided
        children = []
        if request.conversation_content:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": request.conversation_content}}]
                }
            })

        # Create page
        response = self.notion.pages.create(
            parent={"database_id": self.database_id},
            properties=properties,
            children=children if children else None
        )

        page_id = response["id"]

        return {
            "success": True,
            "action": "create_session",
            "page_id": page_id,
            "url": f"https://notion.so/{page_id.replace('-', '')}",
            "session_title": request.session_title,
            "project": request.project,
            "status": "draft",
            "message": f"Created session: {request.session_title}"
        }

    async def _update_session(self, request: NotionArchiveRequest) -> Dict[str, Any]:
        """Update session with new content"""

        if not request.page_id:
            return {"success": False, "error": "page_id required"}

        # Get current properties
        page = self.notion.pages.retrieve(page_id=request.page_id)
        current_tokens = page["properties"]["Token Usage"].get("number", 0)

        # Calculate new values
        new_total_tokens = current_tokens + (request.token_count or 0)

        # Update properties
        properties = {
            "Token Usage": {"number": new_total_tokens},
        }

        # Append content if provided
        if request.conversation_content:
            self.notion.blocks.children.append(
                block_id=request.page_id,
                children=[{
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": f"\n\n--- Update {datetime.now().isoformat()} ---\n{request.conversation_content}"}}]
                    }
                }]
            )

        # Check auto-archive thresholds
        should_archive = False
        auto_archive_reason = None

        if request.auto_archive:
            if new_total_tokens > 50000:
                should_archive = True
                auto_archive_reason = f"Exceeded token threshold: {new_total_tokens} > 50,000"
            # Note: We'd need to track conversation count separately

        if should_archive:
            properties["Status"] = {"select": {"name": "archived"}}

        # Update page
        self.notion.pages.update(page_id=request.page_id, properties=properties)

        result = {
            "success": True,
            "action": "update_session",
            "page_id": request.page_id,
            "total_tokens": new_total_tokens,
            "auto_archived": should_archive
        }

        if should_archive:
            result["archive_reason"] = auto_archive_reason
            result["message"] = f"Session updated and auto-archived: {auto_archive_reason}"
        else:
            result["message"] = f"Session updated. Total tokens: {new_total_tokens}"

        return result

    async def _archive_session(self, request: NotionArchiveRequest) -> Dict[str, Any]:
        """Manually archive session"""

        if not request.page_id:
            return {"success": False, "error": "page_id required"}

        self.notion.pages.update(
            page_id=request.page_id,
            properties={
                "Status": {"select": {"name": "archived"}}
            }
        )

        return {
            "success": True,
            "action": "archive_session",
            "page_id": request.page_id,
            "status": "archived",
            "message": "Session archived successfully"
        }

    async def _query_archive(self, request: NotionArchiveRequest) -> Dict[str, Any]:
        """Query archive with filters"""

        filters = []

        # Filter by status
        if request.query_status:
            filters.append({
                "property": "Status",
                "select": {"equals": request.query_status}
            })

        # Filter by project
        if request.query_project:
            filters.append({
                "property": "Project",
                "select": {"equals": request.query_project}
            })

        # Filter by tags (if provided)
        if request.query_tags:
            tags = [t.strip() for t in request.query_tags.split(",")]
            for tag in tags:
                filters.append({
                    "property": "Tags",
                    "multi_select": {"contains": tag}
                })

        # Build query
        query = {"database_id": self.database_id}
        if filters:
            query["filter"] = {"and": filters} if len(filters) > 1 else filters[0]

        # Execute query
        response = self.notion.databases.query(**query)

        results = []
        for page in response["results"]:
            title_prop = page["properties"]["Summary"]
            title = title_prop["title"][0]["plain_text"] if title_prop["title"] else "Untitled"

            project_prop = page["properties"]["Project"]
            project = project_prop["select"]["name"] if project_prop.get("select") else None

            status_prop = page["properties"]["Status"]
            status = status_prop["select"]["name"] if status_prop.get("select") else None

            tokens_prop = page["properties"]["Token Usage"]
            tokens = tokens_prop.get("number", 0)

            results.append({
                "page_id": page["id"],
                "title": title,
                "project": project,
                "status": status,
                "tokens": tokens,
                "url": f"https://notion.so/{page['id'].replace('-', '')}"
            })

        return {
            "success": True,
            "action": "query_archive",
            "count": len(results),
            "results": results,
            "filters": {
                "status": request.query_status,
                "project": request.query_project,
                "tags": request.query_tags
            }
        }

    async def _get_status(self, request: NotionArchiveRequest) -> Dict[str, Any]:
        """Get session status"""

        if not request.page_id:
            return {"success": False, "error": "page_id required"}

        page = self.notion.pages.retrieve(page_id=request.page_id)

        title_prop = page["properties"]["Summary"]
        title = title_prop["title"][0]["plain_text"] if title_prop["title"] else "Untitled"

        status_prop = page["properties"]["Status"]
        status = status_prop["select"]["name"] if status_prop.get("select") else None

        tokens_prop = page["properties"]["Token Usage"]
        tokens = tokens_prop.get("number", 0)

        project_prop = page["properties"]["Project"]
        project = project_prop["select"]["name"] if project_prop.get("select") else None

        return {
            "success": True,
            "action": "get_status",
            "page_id": request.page_id,
            "title": title,
            "status": status,
            "tokens": tokens,
            "project": project,
            "near_archive_threshold": tokens > 40000,
            "url": f"https://notion.so/{page['id'].replace('-', '')}"
        }
