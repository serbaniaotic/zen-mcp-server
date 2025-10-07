"""
Evidence Monitor - Real-time evidence file monitoring

Watches evidence files for updates and notifies thinking agents when
new entries are added, enabling thinking termination and hallucination prevention.

Philosophy: "Grace in wisdom" - know when to stop thinking
"""

import asyncio
import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class EvidenceState:
    """Captured state of an evidence file at a point in time"""
    ticket_id: str
    evidence_file: str
    entry_count: int
    last_entry_timestamp: str
    context_type: str
    file_hash: str  # MD5 hash for change detection
    captured_at: str  # ISO timestamp


@dataclass
class EvidenceEntry:
    """Represents a single evidence entry"""
    entry_number: int
    timestamp: str
    prompt_input: str
    raw_output: str
    context_type: str
    source: str = "user"  # "user", "agent", "system"
    metadata: Dict = field(default_factory=dict)


@dataclass
class EvidenceUpdate:
    """Notification of evidence changes"""
    ticket_id: str
    evidence_file: str
    new_entry_number: int
    entry: EvidenceEntry
    source: str
    context_changed: bool
    invalidates_thinking: bool
    reason: str = ""


class EvidenceMonitor:
    """
    Monitors evidence files for changes and notifies subscribers.
    
    Features:
    - Parse evidence files to extract entries
    - Detect new entries via file hash changes
    - Notify subscribed agents of updates
    - Track evidence state per ticket
    """
    
    def __init__(self):
        self.evidence_states: Dict[str, EvidenceState] = {}  # ticket_id -> state
        self.subscribers: Dict[str, Set[str]] = {}  # ticket_id -> set of agent_ids
        self.notification_callbacks: List[Callable] = []
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}  # ticket_id -> task
        self._lock = asyncio.Lock()
    
    async def capture_state(self, ticket_id: str, evidence_file: str) -> EvidenceState:
        """
        Capture current state of an evidence file.
        
        Args:
            ticket_id: Ticket ID
            evidence_file: Path to evidence file
            
        Returns:
            Current evidence state
        """
        try:
            # Read file
            file_path = Path(evidence_file)
            if not file_path.exists():
                return EvidenceState(
                    ticket_id=ticket_id,
                    evidence_file=evidence_file,
                    entry_count=0,
                    last_entry_timestamp="",
                    context_type="",
                    file_hash="",
                    captured_at=datetime.utcnow().isoformat() + "Z"
                )
            
            content = file_path.read_text()
            
            # Parse entries
            entries = self._parse_evidence_entries(content)
            
            # Get context type from filename
            context_type = self._extract_context_type(evidence_file)
            
            # Calculate file hash
            file_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Get last entry timestamp
            last_timestamp = entries[-1].timestamp if entries else ""
            
            state = EvidenceState(
                ticket_id=ticket_id,
                evidence_file=evidence_file,
                entry_count=len(entries),
                last_entry_timestamp=last_timestamp,
                context_type=context_type,
                file_hash=file_hash,
                captured_at=datetime.utcnow().isoformat() + "Z"
            )
            
            # Cache state
            async with self._lock:
                self.evidence_states[ticket_id] = state
            
            return state
            
        except Exception as e:
            logger.error(f"Failed to capture evidence state: {e}")
            raise
    
    def _parse_evidence_entries(self, content: str) -> List[EvidenceEntry]:
        """
        Parse evidence entries from markdown content.
        
        Expects format:
        ## Evidence Entry #N: YYYY-MM-DD HH:MM:SS TZ
        ### Prompt Input
        ...
        ### Raw Data Output
        ...
        """
        entries = []
        
        # Split by evidence entry headers
        entry_pattern = r"## Evidence Entry #(\d+):\s*([^\n]+)"
        matches = list(re.finditer(entry_pattern, content))
        
        for i, match in enumerate(matches):
            entry_num = int(match.group(1))
            timestamp = match.group(2).strip()
            
            # Get content between this entry and next (or end of file)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            entry_content = content[start:end]
            
            # Extract sections
            prompt = self._extract_section(entry_content, "### Prompt Input")
            output = self._extract_section(entry_content, "### Raw Data Output")
            
            # Extract metadata from HTML comments
            source = self._extract_html_comment(entry_content, "source") or "user"
            
            entries.append(EvidenceEntry(
                entry_number=entry_num,
                timestamp=timestamp,
                prompt_input=prompt,
                raw_output=output,
                context_type="",  # Will be set from filename
                source=source
            ))
        
        return entries
    
    def _extract_section(self, content: str, header: str) -> str:
        """Extract content under a markdown header"""
        pattern = f"{re.escape(header)}\n```[^\n]*\n(.*?)\n```"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else ""
    
    def _extract_html_comment(self, content: str, key: str) -> Optional[str]:
        """Extract value from HTML comment: <!-- key: value -->"""
        pattern = f"<!--\\s*{re.escape(key)}:\\s*([^-]+?)\\s*-->"
        match = re.search(pattern, content)
        return match.group(1).strip() if match else None
    
    def _extract_context_type(self, filepath: str) -> str:
        """Extract context type from filename"""
        # e.g., "evidence/database-performance.md" -> "database-performance"
        filename = Path(filepath).stem
        return filename
    
    async def check_for_updates(
        self,
        ticket_id: str,
        last_known_range: tuple[int, int]
    ) -> List[EvidenceUpdate]:
        """
        Check if evidence has been updated since last known state.
        
        Args:
            ticket_id: Ticket to check
            last_known_range: (start, end) entry numbers agent has seen
            
        Returns:
            List of new updates
        """
        try:
            # Get current state
            if ticket_id not in self.evidence_states:
                return []
            
            current_state = self.evidence_states[ticket_id]
            
            # Check if new entries exist
            last_seen = last_known_range[1]
            if current_state.entry_count <= last_seen:
                return []  # No new entries
            
            # Re-parse to get new entries
            file_path = Path(current_state.evidence_file)
            if not file_path.exists():
                return []
            
            content = file_path.read_text()
            all_entries = self._parse_evidence_entries(content)
            
            # Get only new entries
            new_entries = [e for e in all_entries if e.entry_number > last_seen]
            
            # Create update notifications
            updates = []
            for entry in new_entries:
                # Determine if this invalidates thinking
                invalidates = self._check_invalidation(entry)
                
                update = EvidenceUpdate(
                    ticket_id=ticket_id,
                    evidence_file=current_state.evidence_file,
                    new_entry_number=entry.entry_number,
                    entry=entry,
                    source=entry.source,
                    context_changed=False,  # Will be determined by invalidation checker
                    invalidates_thinking=invalidates,
                    reason=self._get_invalidation_reason(entry) if invalidates else ""
                )
                updates.append(update)
            
            return updates
            
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            return []
    
    def _check_invalidation(self, entry: EvidenceEntry) -> bool:
        """
        Quick check if entry might invalidate thinking.
        
        Detailed invalidation logic is in InvalidationChecker,
        this is just a fast pre-filter.
        """
        # Check for common invalidation patterns
        content = entry.prompt_input.lower() + entry.raw_output.lower()
        
        # User direction changes
        if any(word in content for word in ["failed", "not working", "try different", "change approach"]):
            return True
        
        # Solution found
        if entry.source == "agent" and any(word in content for word in ["solution found", "problem solved", "fix applied"]):
            return True
        
        return False
    
    def _get_invalidation_reason(self, entry: EvidenceEntry) -> str:
        """Get human-readable reason for potential invalidation"""
        content = entry.prompt_input.lower() + entry.raw_output.lower()
        
        if "failed" in content:
            return f"Entry #{entry.entry_number} indicates approach failed"
        if "solution found" in content:
            return f"Entry #{entry.entry_number} shows solution found by another agent"
        if "change approach" in content:
            return f"Entry #{entry.entry_number} indicates direction change"
        
        return f"Entry #{entry.entry_number} may invalidate current thinking"
    
    async def subscribe(self, agent_id: str, ticket_id: str) -> bool:
        """
        Subscribe an agent to evidence updates for a ticket.
        
        Args:
            agent_id: Agent to subscribe
            ticket_id: Ticket to monitor
            
        Returns:
            Success status
        """
        async with self._lock:
            if ticket_id not in self.subscribers:
                self.subscribers[ticket_id] = set()
            
            self.subscribers[ticket_id].add(agent_id)
            logger.info(f"Agent {agent_id} subscribed to ticket {ticket_id}")
            
            return True
    
    async def unsubscribe(self, agent_id: str, ticket_id: str) -> bool:
        """Unsubscribe agent from ticket updates"""
        async with self._lock:
            if ticket_id in self.subscribers:
                self.subscribers[ticket_id].discard(agent_id)
                return True
            return False
    
    async def notify_subscribers(self, update: EvidenceUpdate) -> None:
        """
        Notify all subscribed agents of an evidence update.
        
        Args:
            update: Evidence update to broadcast
        """
        ticket_id = update.ticket_id
        
        # Get subscribers
        if ticket_id not in self.subscribers:
            return
        
        subscribers = self.subscribers[ticket_id].copy()
        
        logger.info(
            f"Notifying {len(subscribers)} agents of update to ticket {ticket_id}, "
            f"entry #{update.new_entry_number}"
        )
        
        # Call notification callbacks
        for callback in self.notification_callbacks:
            try:
                await callback(update, subscribers)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")
    
    def register_notification_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called when evidence updates occur.
        
        Callback signature: async def callback(update: EvidenceUpdate, agent_ids: Set[str])
        """
        self.notification_callbacks.append(callback)
    
    async def start_monitoring(self, ticket_id: str, evidence_file: str, interval: int = 5) -> None:
        """
        Start monitoring an evidence file for changes.
        
        Args:
            ticket_id: Ticket ID
            evidence_file: Path to evidence file
            interval: Check interval in seconds (default: 5)
        """
        if ticket_id in self._monitoring_tasks:
            logger.warning(f"Already monitoring ticket {ticket_id}")
            return
        
        async def monitor_loop():
            """Periodic monitoring loop"""
            last_hash = ""
            
            while True:
                try:
                    # Capture current state
                    state = await self.capture_state(ticket_id, evidence_file)
                    
                    # Check if file changed
                    if state.file_hash != last_hash and last_hash:
                        # File changed, check for new entries
                        # We'll need to know agents' last known states
                        # This is handled by check_for_updates when agents poll
                        logger.info(f"Evidence file changed for ticket {ticket_id}")
                    
                    last_hash = state.file_hash
                    
                    await asyncio.sleep(interval)
                    
                except asyncio.CancelledError:
                    logger.info(f"Stopped monitoring ticket {ticket_id}")
                    break
                except Exception as e:
                    logger.error(f"Monitoring error for ticket {ticket_id}: {e}")
                    await asyncio.sleep(interval)
        
        # Start monitoring task
        task = asyncio.create_task(monitor_loop())
        self._monitoring_tasks[ticket_id] = task
        
        logger.info(f"Started monitoring ticket {ticket_id} every {interval}s")
    
    async def stop_monitoring(self, ticket_id: str) -> None:
        """Stop monitoring a ticket"""
        if ticket_id in self._monitoring_tasks:
            self._monitoring_tasks[ticket_id].cancel()
            try:
                await self._monitoring_tasks[ticket_id]
            except asyncio.CancelledError:
                pass
            del self._monitoring_tasks[ticket_id]
            logger.info(f"Stopped monitoring ticket {ticket_id}")
    
    async def get_monitoring_status(self) -> Dict:
        """Get status of all monitoring tasks"""
        return {
            "active_monitors": len(self._monitoring_tasks),
            "monitored_tickets": list(self._monitoring_tasks.keys()),
            "total_subscribers": sum(len(subs) for subs in self.subscribers.values()),
            "subscribers_by_ticket": {
                ticket_id: len(subs)
                for ticket_id, subs in self.subscribers.items()
            }
        }


# Global monitor instance
_monitor: Optional[EvidenceMonitor] = None


def get_monitor() -> EvidenceMonitor:
    """Get or create the global evidence monitor"""
    global _monitor
    if _monitor is None:
        _monitor = EvidenceMonitor()
    return _monitor

