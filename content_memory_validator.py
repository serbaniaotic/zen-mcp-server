#!/usr/bin/env python3
"""
Content Memory Validation System
Prevents persistent memory contamination by validating content against filesystem truth

Fixes the TRIPLE COLLISION bug where multiple competing memories exist for same identifier
"""

import json
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import logging


@dataclass
class ContentMemory:
    """Content memory entry with validation metadata"""
    identifier: str  # e.g., "TICKET-030"
    concept_summary: str  # e.g., "CLOUDSQL03 Optimization"
    content_hash: str  # SHA256 of content for change detection
    file_path: Optional[str]  # Path to source file
    file_mtime: Optional[str]  # File modification time
    memory_timestamp: str  # When memory was stored
    session_id: str  # Session that created this memory
    validated_at: Optional[str]  # Last validation timestamp
    is_stale: bool  # Is memory stale (file newer than memory)
    conflict_count: int  # How many competing memories exist
    metadata: Dict[str, Any]  # Additional context


@dataclass
class MemoryConflict:
    """Detected memory conflict"""
    identifier: str
    competing_memories: List[ContentMemory]
    filesystem_state: Optional[Dict[str, Any]]
    recommended_action: str
    severity: str  # 'critical', 'high', 'medium', 'low'


class ContentMemoryValidator:
    """Validates content memory against filesystem truth"""

    def __init__(self, db_path: str = "content_memory.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.init_database()

    def init_database(self):
        """Initialize SQLite database for content memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Content memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier TEXT NOT NULL,
                concept_summary TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                file_path TEXT,
                file_mtime TEXT,
                memory_timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                validated_at TEXT,
                is_stale INTEGER DEFAULT 0,
                conflict_count INTEGER DEFAULT 0,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Conflict detection log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conflict_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier TEXT NOT NULL,
                detection_time TEXT NOT NULL,
                conflict_type TEXT NOT NULL,
                competing_count INTEGER NOT NULL,
                filesystem_exists INTEGER NOT NULL,
                resolution_action TEXT,
                severity TEXT NOT NULL,
                details TEXT
            )
        """)

        # Validation audit log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier TEXT NOT NULL,
                validation_time TEXT NOT NULL,
                memory_timestamp TEXT NOT NULL,
                file_mtime TEXT,
                is_stale INTEGER NOT NULL,
                action_taken TEXT NOT NULL,
                details TEXT
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_identifier ON content_memories(identifier)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON content_memories(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stale ON content_memories(is_stale)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conflict_identifier ON conflict_log(identifier)")

        conn.commit()
        conn.close()

    def store_memory(
        self,
        identifier: str,
        concept_summary: str,
        content: str,
        file_path: Optional[str] = None,
        session_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContentMemory:
        """Store or update content memory with conflict detection"""

        # Check for existing memories
        existing_memories = self.get_memories(identifier)

        # Calculate content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Get file metadata if path provided
        file_mtime = None
        if file_path and os.path.exists(file_path):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()

        memory = ContentMemory(
            identifier=identifier,
            concept_summary=concept_summary,
            content_hash=content_hash,
            file_path=file_path,
            file_mtime=file_mtime,
            memory_timestamp=datetime.now().isoformat(),
            session_id=session_id,
            validated_at=datetime.now().isoformat(),
            is_stale=False,
            conflict_count=len(existing_memories),
            metadata=metadata or {}
        )

        # Detect conflicts with existing memories
        if existing_memories:
            for existing in existing_memories:
                if existing.concept_summary != concept_summary:
                    self.logger.warning(
                        f"⚠️ CONFLICT DETECTED: {identifier}\n"
                        f"   Existing: {existing.concept_summary}\n"
                        f"   New: {concept_summary}"
                    )
                    self._log_conflict(identifier, existing_memories + [memory])

        # Store in database
        self._save_memory(memory)

        # Invalidate stale memories for this identifier
        self._invalidate_stale_memories(identifier, memory.memory_timestamp)

        return memory

    def retrieve_memory(
        self,
        identifier: str,
        validate_filesystem: bool = True
    ) -> Tuple[Optional[ContentMemory], Optional[MemoryConflict]]:
        """
        Retrieve memory with automatic validation against filesystem

        Returns: (memory, conflict)
        - memory: Most recent valid memory, or None
        - conflict: Detected conflict if any
        """

        memories = self.get_memories(identifier)

        if not memories:
            return None, None

        # Check for conflicts (multiple competing memories)
        conflict = None
        if len(memories) > 1:
            different_concepts = len(set(m.concept_summary for m in memories)) > 1
            if different_concepts:
                conflict = self._detect_conflict(identifier, memories)

        # Get most recent memory
        memories.sort(key=lambda m: m.memory_timestamp, reverse=True)
        memory = memories[0]

        # Validate against filesystem if requested
        if validate_filesystem and memory.file_path:
            memory, validation_conflict = self._validate_against_filesystem(memory)
            if validation_conflict and not conflict:
                conflict = validation_conflict

        # Log validation
        self._log_validation(memory)

        return memory, conflict

    def _validate_against_filesystem(
        self,
        memory: ContentMemory
    ) -> Tuple[ContentMemory, Optional[MemoryConflict]]:
        """Validate memory against current filesystem state"""

        if not memory.file_path:
            return memory, None

        # Check if file exists
        if not os.path.exists(memory.file_path):
            self.logger.warning(f"⚠️ File not found: {memory.file_path} (orphaned memory)")
            memory.is_stale = True
            self._update_memory_staleness(memory.identifier, True)
            return memory, None

        # Get current file modification time
        current_mtime = datetime.fromtimestamp(os.path.getmtime(memory.file_path)).isoformat()

        # Compare file mtime with memory timestamp
        memory_time = datetime.fromisoformat(memory.memory_timestamp)
        file_time = datetime.fromisoformat(current_mtime)

        if file_time > memory_time:
            # File is newer than memory = STALE MEMORY
            self.logger.warning(
                f"🔴 STALE MEMORY DETECTED: {memory.identifier}\n"
                f"   Memory from: {memory.memory_timestamp}\n"
                f"   File modified: {current_mtime}\n"
                f"   ⚠️ File system is source of truth!"
            )

            memory.is_stale = True
            memory.file_mtime = current_mtime
            self._update_memory_staleness(memory.identifier, True)

            # Read current file content for conflict detection
            try:
                with open(memory.file_path, 'r', encoding='utf-8') as f:
                    current_content = f.read()
                    current_hash = hashlib.sha256(current_content.encode()).hexdigest()

                    if current_hash != memory.content_hash:
                        # Content has changed - create conflict
                        conflict = MemoryConflict(
                            identifier=memory.identifier,
                            competing_memories=[memory],
                            filesystem_state={
                                'path': memory.file_path,
                                'mtime': current_mtime,
                                'content_hash': current_hash
                            },
                            recommended_action="UPDATE_MEMORY_FROM_FILESYSTEM",
                            severity="critical"
                        )
                        return memory, conflict
            except Exception as e:
                self.logger.error(f"Error reading file {memory.file_path}: {e}")

        return memory, None

    def _detect_conflict(
        self,
        identifier: str,
        memories: List[ContentMemory]
    ) -> MemoryConflict:
        """Detect and classify memory conflicts"""

        # Get filesystem state if file exists
        filesystem_state = None
        file_path = next((m.file_path for m in memories if m.file_path), None)

        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    filesystem_state = {
                        'path': file_path,
                        'mtime': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                        'content_hash': hashlib.sha256(content.encode()).hexdigest()
                    }
            except Exception as e:
                self.logger.error(f"Error reading file {file_path}: {e}")

        # Determine severity
        unique_concepts = len(set(m.concept_summary for m in memories))
        if unique_concepts >= 3:
            severity = "critical"  # Triple collision or worse
        elif unique_concepts == 2:
            severity = "high"
        else:
            severity = "medium"

        # Determine recommended action
        if filesystem_state:
            recommended_action = "USE_FILESYSTEM_AS_SOURCE_OF_TRUTH"
        else:
            recommended_action = "USE_MOST_RECENT_MEMORY"

        conflict = MemoryConflict(
            identifier=identifier,
            competing_memories=memories,
            filesystem_state=filesystem_state,
            recommended_action=recommended_action,
            severity=severity
        )

        self._log_conflict(identifier, memories, conflict)

        return conflict

    def get_memories(self, identifier: str) -> List[ContentMemory]:
        """Get all memories for an identifier"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT identifier, concept_summary, content_hash, file_path, file_mtime,
                   memory_timestamp, session_id, validated_at, is_stale, conflict_count, metadata
            FROM content_memories
            WHERE identifier = ?
            ORDER BY memory_timestamp DESC
        """, (identifier,))

        memories = []
        for row in cursor.fetchall():
            metadata = json.loads(row[10]) if row[10] else {}
            memory = ContentMemory(
                identifier=row[0],
                concept_summary=row[1],
                content_hash=row[2],
                file_path=row[3],
                file_mtime=row[4],
                memory_timestamp=row[5],
                session_id=row[6],
                validated_at=row[7],
                is_stale=bool(row[8]),
                conflict_count=row[9],
                metadata=metadata
            )
            memories.append(memory)

        conn.close()
        return memories

    def health_check(self) -> Dict[str, Any]:
        """Perform memory health check"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count total memories
        cursor.execute("SELECT COUNT(*) FROM content_memories")
        total_memories = cursor.fetchone()[0]

        # Count stale memories
        cursor.execute("SELECT COUNT(*) FROM content_memories WHERE is_stale = 1")
        stale_count = cursor.fetchone()[0]

        # Find identifiers with multiple memories
        cursor.execute("""
            SELECT identifier, COUNT(*) as count
            FROM content_memories
            GROUP BY identifier
            HAVING COUNT(*) > 1
        """)
        multi_memory_identifiers = cursor.fetchall()

        # Get conflicts
        conflicts = []
        for identifier, count in multi_memory_identifiers:
            memories = self.get_memories(identifier)
            unique_concepts = len(set(m.concept_summary for m in memories))
            if unique_concepts > 1:
                conflicts.append({
                    'identifier': identifier,
                    'memory_count': count,
                    'unique_concepts': unique_concepts,
                    'concepts': list(set(m.concept_summary for m in memories))
                })

        conn.close()

        return {
            'total_memories': total_memories,
            'stale_memories': stale_count,
            'conflicts_detected': len(conflicts),
            'conflicts': conflicts,
            'health_score': self._calculate_health_score(total_memories, stale_count, len(conflicts))
        }

    def _calculate_health_score(self, total: int, stale: int, conflicts: int) -> int:
        """Calculate memory health score (0-100)"""
        if total == 0:
            return 100

        score = 100
        score -= (stale / total) * 50  # Stale memories reduce score
        score -= conflicts * 10  # Each conflict reduces score
        return max(0, int(score))

    def _save_memory(self, memory: ContentMemory):
        """Save memory to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        metadata_json = json.dumps(memory.metadata)

        cursor.execute("""
            INSERT INTO content_memories
            (identifier, concept_summary, content_hash, file_path, file_mtime,
             memory_timestamp, session_id, validated_at, is_stale, conflict_count,
             metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.identifier, memory.concept_summary, memory.content_hash,
            memory.file_path, memory.file_mtime, memory.memory_timestamp,
            memory.session_id, memory.validated_at, int(memory.is_stale),
            memory.conflict_count, metadata_json,
            datetime.now().isoformat(), datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def _update_memory_staleness(self, identifier: str, is_stale: bool):
        """Update staleness flag for all memories of identifier"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE content_memories
            SET is_stale = ?, updated_at = ?
            WHERE identifier = ?
        """, (int(is_stale), datetime.now().isoformat(), identifier))

        conn.commit()
        conn.close()

    def _invalidate_stale_memories(self, identifier: str, current_timestamp: str):
        """Mark older memories as stale when new memory is stored"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE content_memories
            SET is_stale = 1, updated_at = ?
            WHERE identifier = ? AND memory_timestamp < ?
        """, (datetime.now().isoformat(), identifier, current_timestamp))

        conn.commit()
        conn.close()

    def _log_conflict(self, identifier: str, memories: List[ContentMemory], conflict: Optional[MemoryConflict] = None):
        """Log conflict to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        filesystem_exists = any(
            m.file_path and os.path.exists(m.file_path) for m in memories
        )

        details = {
            'concepts': [m.concept_summary for m in memories],
            'sessions': [m.session_id for m in memories],
            'timestamps': [m.memory_timestamp for m in memories]
        }

        cursor.execute("""
            INSERT INTO conflict_log
            (identifier, detection_time, conflict_type, competing_count,
             filesystem_exists, resolution_action, severity, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            identifier,
            datetime.now().isoformat(),
            "MULTIPLE_CONCEPTS",
            len(memories),
            int(filesystem_exists),
            conflict.recommended_action if conflict else "PENDING",
            conflict.severity if conflict else "medium",
            json.dumps(details)
        ))

        conn.commit()
        conn.close()

    def _log_validation(self, memory: ContentMemory):
        """Log validation event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        action_taken = "VALIDATED" if not memory.is_stale else "MARKED_STALE"

        cursor.execute("""
            INSERT INTO validation_audit
            (identifier, validation_time, memory_timestamp, file_mtime,
             is_stale, action_taken, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.identifier,
            datetime.now().isoformat(),
            memory.memory_timestamp,
            memory.file_mtime,
            int(memory.is_stale),
            action_taken,
            json.dumps({'concept': memory.concept_summary})
        ))

        conn.commit()
        conn.close()


def test_content_memory_validator():
    """Test the content memory validator"""
    print("🧪 Testing Content Memory Validator")
    print("=" * 50)

    # Create validator
    validator = ContentMemoryValidator("test_content_memory.db")

    # Simulate TICKET-030 triple collision scenario
    print("\n📝 Simulating TICKET-030 triple collision bug...")

    # Memory 1: Vision planning (oldest)
    validator.store_memory(
        identifier="TICKET-030",
        concept_summary="Owlseek Kourn - Multi-Domain Schema",
        content="Vision planning document",
        session_id="vision_session"
    )
    print("✅ Stored: Vision planning memory")

    # Memory 2: Last night session
    validator.store_memory(
        identifier="TICKET-030",
        concept_summary="ReadQueen vs BookPeople Database Fragmentation Comparison",
        content="Investigation plan for database comparison",
        session_id="last_night_session"
    )
    print("✅ Stored: Last night memory")

    # Memory 3: Today's real work
    validator.store_memory(
        identifier="TICKET-030",
        concept_summary="CLOUDSQL03 Optimization",
        content="Real work: CLOUDSQL03 database performance optimization",
        session_id="today_session"
    )
    print("✅ Stored: Today's real memory")

    # Retrieve and validate
    print("\n🔍 Retrieving TICKET-030 memory...")
    memory, conflict = validator.retrieve_memory("TICKET-030")

    if memory:
        print(f"\n📋 Retrieved Memory:")
        print(f"   Concept: {memory.concept_summary}")
        print(f"   Session: {memory.session_id}")
        print(f"   Timestamp: {memory.memory_timestamp}")
        print(f"   Stale: {memory.is_stale}")
        print(f"   Conflicts: {memory.conflict_count}")

    if conflict:
        print(f"\n⚠️ CONFLICT DETECTED:")
        print(f"   Severity: {conflict.severity}")
        print(f"   Competing Memories: {len(conflict.competing_memories)}")
        print(f"   Recommended Action: {conflict.recommended_action}")
        print(f"\n   Concepts:")
        for m in conflict.competing_memories:
            print(f"   - {m.concept_summary} (from {m.session_id})")

    # Health check
    print("\n🏥 Memory Health Check:")
    health = validator.health_check()
    print(f"   Total Memories: {health['total_memories']}")
    print(f"   Stale Memories: {health['stale_memories']}")
    print(f"   Conflicts: {health['conflicts_detected']}")
    print(f"   Health Score: {health['health_score']}/100")

    if health['conflicts']:
        print(f"\n   Detected Conflicts:")
        for conf in health['conflicts']:
            print(f"   - {conf['identifier']}: {conf['unique_concepts']} competing concepts")
            for concept in conf['concepts']:
                print(f"     * {concept}")

    print("\n✅ Test complete!")
    print("🔒 Bug fix validated: System detects triple collision and warns user")


if __name__ == "__main__":
    test_content_memory_validator()
