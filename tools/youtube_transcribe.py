"""
YouTube Transcribe tool - Extract transcripts from YouTube videos

This tool extracts transcripts/captions from YouTube videos for analysis by AI models.
Supports multiple languages and automatic caption detection.
"""

import logging
import re
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from pydantic import Field
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from tools.shared.base_models import COMMON_FIELD_DESCRIPTIONS, ToolRequest

from .simple.base import SimpleTool

logger = logging.getLogger(__name__)

YOUTUBE_FIELD_DESCRIPTIONS = {
    "url": "YouTube video URL (supports youtube.com/watch?v=ID or youtu.be/ID formats)",
    "prompt": "What you want to learn or extract from the video transcript",
    "language": "Preferred language code (e.g., 'en' for English, 'es' for Spanish). Auto-detected if not specified.",
}


class YouTubeTranscribeRequest(ToolRequest):
    """Request model for YouTube Transcribe tool"""

    url: str = Field(..., description=YOUTUBE_FIELD_DESCRIPTIONS["url"])
    prompt: str = Field(..., description=YOUTUBE_FIELD_DESCRIPTIONS["prompt"])
    language: Optional[str] = Field(None, description=YOUTUBE_FIELD_DESCRIPTIONS["language"])


class YouTubeTranscribeTool(SimpleTool):
    """
    Extract and analyze YouTube video transcripts.

    Features:
    - Automatic video ID extraction from URLs
    - Multi-language support
    - Auto-generated and manual captions
    - Clean transcript formatting
    """

    def get_name(self) -> str:
        return "youtube_transcribe"

    def get_description(self) -> str:
        return (
            "Extracts transcripts from YouTube videos for analysis. "
            "Supports both youtube.com and youtu.be URLs, handles multiple languages, "
            "and works with both auto-generated and manual captions. "
            "Use this tool to analyze video content, extract key points, or answer questions about video topics."
        )

    def get_system_prompt(self) -> str:
        return """You are a YouTube video transcript analyzer that helps users understand and extract information from video content.

Your role is to:
1. Receive video transcripts with timestamps
2. Answer the user's specific question about the video
3. Extract key points, quotes, or information
4. Summarize content when requested
5. Cite specific timestamps when relevant (e.g., "At 2:15...")

Be clear and direct. Focus on answering the user's question based on the transcript.
If the transcript doesn't contain requested information, say so clearly."""

    def get_model_category(self):
        """YouTube transcribe uses balanced models for comprehension"""
        from tools.models import ToolModelCategory

        return ToolModelCategory.BALANCED

    def get_default_temperature(self) -> float:
        return 0.4  # Slightly creative for summarization

    def get_request_model(self):
        return YouTubeTranscribeRequest

    def get_tool_fields(self) -> dict[str, dict[str, Any]]:
        """Define tool-specific fields for YouTube Transcribe"""
        return {
            "url": {
                "type": "string",
                "description": YOUTUBE_FIELD_DESCRIPTIONS["url"],
            },
            "prompt": {
                "type": "string",
                "description": YOUTUBE_FIELD_DESCRIPTIONS["prompt"],
            },
            "language": {
                "type": "string",
                "description": YOUTUBE_FIELD_DESCRIPTIONS["language"],
            },
        }

    def get_required_fields(self) -> list[str]:
        """Required fields for YouTube Transcribe"""
        return ["url", "prompt"]

    def get_input_schema(self) -> dict[str, Any]:
        """Generate input schema for YouTube Transcribe tool"""
        required_fields = ["url", "prompt"]
        if self.is_effective_auto_mode():
            required_fields.append("model")

        schema = {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": YOUTUBE_FIELD_DESCRIPTIONS["url"],
                },
                "prompt": {
                    "type": "string",
                    "description": YOUTUBE_FIELD_DESCRIPTIONS["prompt"],
                },
                "language": {
                    "type": "string",
                    "description": YOUTUBE_FIELD_DESCRIPTIONS["language"],
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

    def _extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract YouTube video ID from various URL formats.

        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://youtube.com/watch?v=VIDEO_ID&other=params
        """
        parsed = urlparse(url)

        # youtu.be format
        if parsed.netloc in ["youtu.be", "www.youtu.be"]:
            return parsed.path.lstrip("/")

        # youtube.com format
        if "youtube.com" in parsed.netloc:
            query_params = parse_qs(parsed.query)
            if "v" in query_params:
                return query_params["v"][0]

        # Try regex as fallback
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
            r"(?:embed\/)([0-9A-Za-z_-]{11})",
            r"^([0-9A-Za-z_-]{11})$",  # Just the ID
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _format_time(self, seconds: float) -> str:
        """Convert seconds to MM:SS or HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _fetch_transcript(
        self, video_id: str, language: Optional[str]
    ) -> tuple[list[dict], Optional[str]]:
        """
        Fetch transcript for video.

        Returns:
            tuple: (transcript_entries, error_message)
        """
        try:
            if language:
                # Try specific language first
                try:
                    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
                    logger.info(f"Fetched {language} transcript for {video_id}")
                    return transcript, None
                except NoTranscriptFound:
                    logger.warning(f"No {language} transcript found, trying auto-detect")

            # Auto-detect language
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try manual transcripts first (higher quality)
            try:
                transcript = transcript_list.find_manually_created_transcript()
                logger.info(f"Using manual transcript in {transcript.language}")
                return transcript.fetch(), None
            except NoTranscriptFound:
                pass

            # Fall back to auto-generated
            try:
                transcript = transcript_list.find_generated_transcript(["en"])
                logger.info(f"Using auto-generated transcript in {transcript.language}")
                return transcript.fetch(), None
            except NoTranscriptFound:
                # Try any available transcript
                for transcript in transcript_list:
                    logger.info(f"Using available transcript in {transcript.language}")
                    return transcript.fetch(), None

            return [], "No transcripts available for this video"

        except TranscriptsDisabled:
            return [], "Transcripts are disabled for this video"
        except VideoUnavailable:
            return [], "Video is unavailable or does not exist"
        except Exception as e:
            return [], f"Error fetching transcript: {str(e)}"

    def _format_transcript(self, transcript: list[dict]) -> str:
        """
        Format transcript entries into readable text with timestamps.
        """
        lines = []
        for entry in transcript:
            timestamp = self._format_time(entry["start"])
            text = entry["text"].strip()
            lines.append(f"[{timestamp}] {text}")

        return "\n".join(lines)

    async def prepare_prompt(self, request: YouTubeTranscribeRequest) -> str:
        """
        Extract YouTube transcript and prepare prompt.
        """
        # Extract video ID
        video_id = self._extract_video_id(request.url)
        if not video_id:
            return f"Error: Could not extract video ID from URL: {request.url}\n\nPlease provide a valid YouTube URL (e.g., https://www.youtube.com/watch?v=VIDEO_ID or https://youtu.be/VIDEO_ID)"

        # Fetch transcript
        transcript, error = self._fetch_transcript(video_id, request.language)

        if error:
            return f"Error fetching transcript for video {video_id}: {error}"

        if not transcript:
            return f"No transcript available for video {video_id}"

        # Format transcript
        formatted = self._format_transcript(transcript)

        # Limit size (roughly 100K tokens = ~400K chars)
        max_chars = 400_000
        if len(formatted) > max_chars:
            formatted = formatted[:max_chars] + f"\n\n[Transcript truncated - original was {len(formatted):,} characters]"
            logger.warning(f"Transcript truncated from {len(formatted):,} to {max_chars:,} chars")

        # Build prompt
        prompt_parts = [
            f"YouTube Video Transcript",
            f"Video ID: {video_id}",
            f"URL: https://www.youtube.com/watch?v={video_id}",
            "",
            "---",
            "",
            formatted,
            "",
            "---",
            "",
            f"User question: {request.prompt}",
        ]

        return "\n".join(prompt_parts)
