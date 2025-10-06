#!/usr/bin/env python3
"""
Persistent Memory System for Todo Execution Monitoring
Survives server crashes and restarts with automatic recovery
"""

import json
import sqlite3
import time
import threading
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import os
import atexit
import logging

@dataclass
class PersistentExecution:
    """Persistent execution data that survives crashes"""
    todo_id: str
    todo_text: str
    status: str
    platform: str
    agent: str
    provider: str
    started_at: str
    last_activity: str
    progress_percent: int
    current_action: str
    context: str
    session_id: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    crash_recovery_count: int = 0
    last_checkpoint: str = ""

@dataclass
class CrashRecoveryInfo:
    """Information about crash recovery"""
    crash_time: str
    recovery_time: str
    active_executions: int
    recovered_executions: int
    lost_executions: int
    recovery_duration_seconds: float

class PersistentMemoryManager:
    """Manages persistent memory that survives crashes and restarts"""
    
    def __init__(self, db_path: str = "persistent_todo_execution.db"):
        self.db_path = db_path
        self.active_sessions: Dict[str, PersistentExecution] = {}
        self.crash_recovery_info: Optional[CrashRecoveryInfo] = None
        self.checkpoint_interval = 30  # seconds
        self.last_checkpoint = time.time()
        self.is_running = True
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self._cleanup)
        
        # Initialize database
        self.init_database()
        
        # Start checkpoint thread
        self.checkpoint_thread = threading.Thread(target=self._checkpoint_loop, daemon=True)
        self.checkpoint_thread.start()
        
        # Attempt crash recovery
        self._attempt_crash_recovery()
    
    def init_database(self):
        """Initialize SQLite database for persistent storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS persistent_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                todo_id TEXT NOT NULL,
                todo_text TEXT NOT NULL,
                status TEXT NOT NULL,
                platform TEXT NOT NULL,
                agent TEXT NOT NULL,
                provider TEXT NOT NULL,
                started_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                progress_percent INTEGER DEFAULT 0,
                current_action TEXT,
                context TEXT,
                session_id TEXT NOT NULL UNIQUE,
                completed_at TEXT,
                duration_seconds INTEGER,
                crash_recovery_count INTEGER DEFAULT 0,
                last_checkpoint TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Crash recovery log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crash_recovery_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crash_time TEXT NOT NULL,
                recovery_time TEXT NOT NULL,
                active_executions INTEGER NOT NULL,
                recovered_executions INTEGER NOT NULL,
                lost_executions INTEGER NOT NULL,
                recovery_duration_seconds REAL NOT NULL,
                recovery_details TEXT
            )
        """)
        
        # Checkpoints table for incremental saves
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                checkpoint_time TEXT NOT NULL,
                progress_percent INTEGER NOT NULL,
                current_action TEXT,
                context TEXT,
                last_activity TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES persistent_executions (session_id)
            )
        """)
        
        # Indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON persistent_executions(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON persistent_executions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_todo_id ON persistent_executions(todo_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_checkpoint_session ON execution_checkpoints(session_id)")
        
        conn.commit()
        conn.close()
    
    def _attempt_crash_recovery(self):
        """Attempt to recover from a previous crash"""
        start_time = time.time()
        crash_time = None
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if there are any active executions from before crash
            cursor.execute("""
                SELECT COUNT(*) FROM persistent_executions 
                WHERE status IN ('executing', 'paused') 
                AND last_checkpoint < datetime('now', '-5 minutes')
            """)
            stale_executions = cursor.fetchone()[0]
            
            if stale_executions > 0:
                # Get the last checkpoint time to estimate crash time
                cursor.execute("""
                    SELECT MAX(last_checkpoint) FROM persistent_executions 
                    WHERE status IN ('executing', 'paused')
                """)
                last_checkpoint = cursor.fetchone()[0]
                crash_time = last_checkpoint
                
                # Mark stale executions as paused for recovery
                cursor.execute("""
                    UPDATE persistent_executions 
                    SET status = 'paused', 
                        context = context || ' [CRASH RECOVERY - Auto-paused due to server restart]',
                        crash_recovery_count = crash_recovery_count + 1,
                        last_checkpoint = datetime('now')
                    WHERE status IN ('executing', 'paused') 
                    AND last_checkpoint < datetime('now', '-5 minutes')
                """)
                
                recovered_count = cursor.rowcount
                
                # Load recovered executions into memory
                cursor.execute("""
                    SELECT * FROM persistent_executions 
                    WHERE status = 'paused' 
                    AND crash_recovery_count > 0
                """)
                
                recovered_executions = []
                for row in cursor.fetchall():
                    execution = PersistentExecution(
                        todo_id=row[1],
                        todo_text=row[2],
                        status=row[3],
                        platform=row[4],
                        agent=row[5],
                        provider=row[6],
                        started_at=row[7],
                        last_activity=row[8],
                        progress_percent=row[9],
                        current_action=row[10],
                        context=row[11],
                        session_id=row[12],
                        completed_at=row[13],
                        duration_seconds=row[14],
                        crash_recovery_count=row[15],
                        last_checkpoint=row[16]
                    )
                    self.active_sessions[execution.session_id] = execution
                    recovered_executions.append(execution)
                
                # Log recovery information
                recovery_time = time.time()
                recovery_duration = recovery_time - start_time
                
                self.crash_recovery_info = CrashRecoveryInfo(
                    crash_time=crash_time or "unknown",
                    recovery_time=datetime.now().isoformat(),
                    active_executions=stale_executions,
                    recovered_executions=recovered_count,
                    lost_executions=stale_executions - recovered_count,
                    recovery_duration_seconds=recovery_duration
                )
                
                # Log to database
                cursor.execute("""
                    INSERT INTO crash_recovery_log 
                    (crash_time, recovery_time, active_executions, recovered_executions, 
                     lost_executions, recovery_duration_seconds, recovery_details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    crash_time or "unknown",
                    datetime.now().isoformat(),
                    stale_executions,
                    recovered_count,
                    stale_executions - recovered_count,
                    recovery_duration,
                    f"Recovered {len(recovered_executions)} executions from crash"
                ))
                
                conn.commit()
                
                self.logger.info(f"🔄 Crash recovery completed: {recovered_count} executions recovered")
                self.logger.info(f"⏱️ Recovery duration: {recovery_duration:.2f} seconds")
                
            else:
                self.logger.info("✅ No crash recovery needed - clean startup")
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"❌ Crash recovery failed: {e}")
    
    def start_execution(self, todo_id: str, todo_text: str, platform: str, 
                       agent: str, provider: str, context: str = "") -> str:
        """Start tracking a todo execution with persistent storage"""
        session_id = f"{todo_id}_{int(time.time())}"
        current_time = datetime.now().isoformat()
        
        execution = PersistentExecution(
            todo_id=todo_id,
            todo_text=todo_text,
            status="executing",
            platform=platform,
            agent=agent,
            provider=provider,
            started_at=current_time,
            last_activity=current_time,
            progress_percent=0,
            current_action="Starting execution",
            context=context,
            session_id=session_id,
            last_checkpoint=current_time
        )
        
        # Store in memory
        self.active_sessions[session_id] = execution
        
        # Store in database
        self._save_execution(execution)
        
        return session_id
    
    def update_execution(self, session_id: str, progress_percent: int = None, 
                        current_action: str = None, context: str = None):
        """Update execution progress with persistent storage"""
        if session_id not in self.active_sessions:
            return False
        
        execution = self.active_sessions[session_id]
        
        if progress_percent is not None:
            execution.progress_percent = progress_percent
        if current_action is not None:
            execution.current_action = current_action
        if context is not None:
            execution.context = context
        
        execution.last_activity = datetime.now().isoformat()
        
        # Update database
        self._save_execution(execution)
        
        return True
    
    def pause_execution(self, session_id: str, context: str = ""):
        """Pause a todo execution with persistent storage"""
        if session_id not in self.active_sessions:
            return False
        
        execution = self.active_sessions[session_id]
        execution.status = "paused"
        execution.last_activity = datetime.now().isoformat()
        if context:
            execution.context = context
        
        # Update database
        self._save_execution(execution)
        
        return True
    
    def complete_execution(self, session_id: str, context: str = ""):
        """Complete a todo execution with persistent storage"""
        if session_id not in self.active_sessions:
            return False
        
        execution = self.active_sessions[session_id]
        execution.status = "completed"
        execution.progress_percent = 100
        execution.last_activity = datetime.now().isoformat()
        execution.completed_at = datetime.now().isoformat()
        if context:
            execution.context = context
        
        # Calculate duration
        started_at = datetime.fromisoformat(execution.started_at)
        completed_at = datetime.now()
        execution.duration_seconds = int((completed_at - started_at).total_seconds())
        
        # Update database
        self._save_execution(execution)
        
        # Remove from active sessions
        del self.active_sessions[session_id]
        
        return True
    
    def _save_execution(self, execution: PersistentExecution):
        """Save execution to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if execution exists
            cursor.execute("SELECT id FROM persistent_executions WHERE session_id = ?", (execution.session_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing execution
                cursor.execute("""
                    UPDATE persistent_executions 
                    SET todo_id = ?, todo_text = ?, status = ?, platform = ?, agent = ?, provider = ?,
                        started_at = ?, last_activity = ?, progress_percent = ?, current_action = ?,
                        context = ?, completed_at = ?, duration_seconds = ?, 
                        crash_recovery_count = ?, last_checkpoint = ?, updated_at = ?
                    WHERE session_id = ?
                """, (
                    execution.todo_id, execution.todo_text, execution.status, execution.platform,
                    execution.agent, execution.provider, execution.started_at, execution.last_activity,
                    execution.progress_percent, execution.current_action, execution.context,
                    execution.completed_at, execution.duration_seconds, execution.crash_recovery_count,
                    execution.last_checkpoint, datetime.now().isoformat(), execution.session_id
                ))
            else:
                # Insert new execution
                cursor.execute("""
                    INSERT INTO persistent_executions 
                    (todo_id, todo_text, status, platform, agent, provider, started_at, 
                     last_activity, progress_percent, current_action, context, session_id,
                     completed_at, duration_seconds, crash_recovery_count, last_checkpoint,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution.todo_id, execution.todo_text, execution.status, execution.platform,
                    execution.agent, execution.provider, execution.started_at, execution.last_activity,
                    execution.progress_percent, execution.current_action, execution.context,
                    execution.session_id, execution.completed_at, execution.duration_seconds,
                    execution.crash_recovery_count, execution.last_checkpoint,
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to save execution {execution.session_id}: {e}")
    
    def _checkpoint_loop(self):
        """Background thread for periodic checkpoints"""
        while self.is_running:
            try:
                current_time = time.time()
                if current_time - self.last_checkpoint >= self.checkpoint_interval:
                    self._create_checkpoint()
                    self.last_checkpoint = current_time
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                self.logger.error(f"Checkpoint loop error: {e}")
                time.sleep(10)
    
    def _create_checkpoint(self):
        """Create a checkpoint of current execution state"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            checkpoint_time = datetime.now().isoformat()
            
            for session_id, execution in self.active_sessions.items():
                # Update last checkpoint
                execution.last_checkpoint = checkpoint_time
                
                # Create checkpoint record
                cursor.execute("""
                    INSERT INTO execution_checkpoints 
                    (session_id, checkpoint_time, progress_percent, current_action, 
                     context, last_activity)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session_id, checkpoint_time, execution.progress_percent,
                    execution.current_action, execution.context, execution.last_activity
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Checkpoint creation failed: {e}")
    
    def get_crash_recovery_info(self) -> Optional[CrashRecoveryInfo]:
        """Get information about the last crash recovery"""
        return self.crash_recovery_info
    
    def get_persistent_executions(self) -> List[PersistentExecution]:
        """Get all persistent executions"""
        return list(self.active_sessions.values())
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
        self.is_running = False
        self._cleanup()
        sys.exit(0)
    
    def _cleanup(self):
        """Cleanup on shutdown"""
        try:
            self.logger.info("🧹 Performing cleanup...")
            
            # Create final checkpoint
            self._create_checkpoint()
            
            # Mark all active executions as paused
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for session_id in self.active_sessions:
                cursor.execute("""
                    UPDATE persistent_executions 
                    SET status = 'paused', 
                        context = context || ' [SHUTDOWN - Auto-paused due to server shutdown]',
                        last_checkpoint = datetime('now')
                    WHERE session_id = ?
                """, (session_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info("✅ Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"❌ Cleanup failed: {e}")

def test_persistent_memory():
    """Test the persistent memory system"""
    print("🧪 Testing Persistent Memory System")
    print("=" * 50)
    
    # Create manager
    manager = PersistentMemoryManager("test_persistent_execution.db")
    
    # Start some executions
    session1 = manager.start_execution(
        "todo_001", 
        "Implement persistent memory system", 
        "cursor", 
        "dev", 
        "gpt-5-codex",
        "Starting implementation"
    )
    
    session2 = manager.start_execution(
        "todo_002", 
        "Test crash recovery", 
        "claude_code", 
        "pm", 
        "gemini-2.5-flash",
        "Testing persistence"
    )
    
    print(f"Started execution: {session1}")
    print(f"Started execution: {session2}")
    
    # Update progress
    manager.update_execution(session1, 50, "Implementing database layer", "Added SQLite persistence")
    manager.update_execution(session2, 25, "Testing crash scenarios", "Simulating crashes")
    
    # Check crash recovery info
    recovery_info = manager.get_crash_recovery_info()
    if recovery_info:
        print(f"\n🔄 Crash Recovery Info:")
        print(f"   Crash Time: {recovery_info.crash_time}")
        print(f"   Recovery Time: {recovery_info.recovery_time}")
        print(f"   Recovered Executions: {recovery_info.recovered_executions}")
        print(f"   Recovery Duration: {recovery_info.recovery_duration_seconds:.2f}s")
    else:
        print("\n✅ No crash recovery needed")
    
    # Get persistent executions
    executions = manager.get_persistent_executions()
    print(f"\n📋 Active Executions: {len(executions)}")
    for execution in executions:
        print(f"   {execution.todo_id}: {execution.status} ({execution.progress_percent}%)")
    
    print("\n✅ Persistent memory system test complete!")
    print("💡 To test crash recovery, restart the script and check recovery info")

if __name__ == "__main__":
    test_persistent_memory()
