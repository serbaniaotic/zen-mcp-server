"""
Usage Tracker for Centralized Prompts
Task-8: Phase 2.2 - Basic Usage Tracking
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class UsageTracker:
    """Tracks prompt usage to .motif/feedback/ for learning"""
    
    def __init__(self):
        home = Path.home()
        self.feedback_dir = home / ".mcp" / "prompts" / ".motif" / "feedback"
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
    
    def track_usage(
        self,
        prompt_id: str,
        context: dict[str, Any],
        outcome: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Track prompt usage to feedback logs
        
        Args:
            prompt_id: Prompt identifier (e.g., "qc-analysis")
            context: Context dict with mode, project, task, etc.
            outcome: Outcome dict with success, duration, etc.
        """
        try:
            # Generate unique session ID
            timestamp = datetime.now().isoformat()
            session_id = f"{prompt_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create feedback entry
            feedback = {
                "session_id": session_id,
                "prompt_id": prompt_id,
                "timestamp": timestamp,
                "context": context,
                "outcome": outcome or {},
            }
            
            # Write to daily log file
            date = datetime.now().strftime("%Y-%m-%d")
            feedback_file = self.feedback_dir / f"usage-{date}.json"
            
            # Append to file (one JSON object per line)
            with open(feedback_file, "a") as f:
                f.write(json.dumps(feedback) + "\n")
            
            logger.info(f"Tracked usage: {prompt_id} → {feedback_file}")
            
        except Exception as e:
            logger.error(f"Failed to track usage: {e}")
    
    def record_outcome(
        self,
        session_id: str,
        outcome: dict[str, Any]
    ) -> None:
        """
        Update outcome for an existing session
        
        Args:
            session_id: Session identifier
            outcome: Outcome dict with success, clarifications, etc.
        """
        try:
            # Find the session in today's log
            date = datetime.now().strftime("%Y-%m-%d")
            feedback_file = self.feedback_dir / f"usage-{date}.json"
            
            if not feedback_file.exists():
                logger.warning(f"Feedback file not found: {feedback_file}")
                return
            
            # Read all entries
            entries = []
            with open(feedback_file, "r") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
            
            # Update the matching entry
            updated = False
            for entry in entries:
                if entry.get("session_id") == session_id:
                    entry["outcome"] = outcome
                    entry["outcome_updated_at"] = datetime.now().isoformat()
                    updated = True
                    break
            
            if updated:
                # Rewrite file with updated entries
                with open(feedback_file, "w") as f:
                    for entry in entries:
                        f.write(json.dumps(entry) + "\n")
                logger.info(f"Updated outcome for session: {session_id}")
            else:
                logger.warning(f"Session not found: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to record outcome: {e}")
    
    def get_recent_usage(self, days: int = 7) -> list[dict[str, Any]]:
        """
        Get recent usage entries
        
        Args:
            days: Number of days to look back
        
        Returns:
            List of feedback entries
        """
        entries = []
        
        try:
            # Get feedback files from last N days
            from datetime import timedelta
            today = datetime.now()
            
            for i in range(days):
                date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                feedback_file = self.feedback_dir / f"usage-{date}.json"
                
                if feedback_file.exists():
                    with open(feedback_file, "r") as f:
                        for line in f:
                            if line.strip():
                                entries.append(json.loads(line))
        
        except Exception as e:
            logger.error(f"Failed to get recent usage: {e}")
        
        return entries
    
    def get_prompt_stats(self, prompt_id: str, days: int = 30) -> dict[str, Any]:
        """
        Get statistics for a specific prompt
        
        Args:
            prompt_id: Prompt identifier
            days: Number of days to analyze
        
        Returns:
            Statistics dict
        """
        entries = self.get_recent_usage(days)
        prompt_entries = [e for e in entries if e.get("prompt_id") == prompt_id]
        
        if not prompt_entries:
            return {
                "prompt_id": prompt_id,
                "usage_count": 0,
                "success_rate": 0.0,
                "avg_clarifications": 0.0,
            }
        
        # Calculate stats
        total = len(prompt_entries)
        successes = sum(1 for e in prompt_entries if e.get("outcome", {}).get("success", False))
        clarifications = [e.get("outcome", {}).get("clarifications", 0) for e in prompt_entries if "outcome" in e]
        
        return {
            "prompt_id": prompt_id,
            "usage_count": total,
            "success_rate": successes / total if total > 0 else 0.0,
            "avg_clarifications": sum(clarifications) / len(clarifications) if clarifications else 0.0,
            "last_used": prompt_entries[0].get("timestamp") if prompt_entries else None,
        }

