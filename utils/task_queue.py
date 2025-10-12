"""
Task Queue implementation for Zen MCP Server.

Provides persistent task queue in Postgres for multi-window coordination,
task persistence across restarts, and priority-based task selection.
"""

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import DictCursor, Json

from utils.db_config import DatabaseConfig

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """Task type enumeration"""
    CHAT = "chat"
    THINKDEEP = "thinkdeep"
    DEBUG = "debug"
    CODEREVIEW = "codereview"
    CONSENSUS = "consensus"
    PLANNER = "planner"
    PRECOMMIT = "precommit"
    ANALYZE = "analyze"
    REFACTOR = "refactor"
    CUSTOM = "custom"


@dataclass
class Task:
    """Task data structure"""
    id: str
    task_type: str
    status: str
    assigned_to: Optional[str]
    priority: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    data: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "id": self.id,
            "task_type": self.task_type,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "data": self.data,
            "result": self.result,
        }
    
    @classmethod
    def from_db_row(cls, row) -> "Task":
        """Create Task from database row"""
        return cls(
            id=str(row["id"]),
            task_type=row["task_type"],
            status=row["status"],
            assigned_to=row["assigned_to"],
            priority=row["priority"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
            data=row["data"],
            result=row["result"],
        )


class TaskQueue:
    """
    Persistent task queue using Postgres.
    
    Provides:
    - Task persistence across restarts
    - Multi-window coordination
    - Priority-based task selection
    - Task status tracking
    - Async task execution support
    """
    
    def __init__(self, connection_params: Optional[Dict] = None):
        """
        Initialize task queue.
        
        Args:
            connection_params: Optional Postgres connection parameters.
                              If None, uses DatabaseConfig defaults.
        """
        self.connection_params = connection_params or DatabaseConfig.get_postgres_dsn()
        self.conn = None
        self._connect()
        self._ensure_schema()
    
    def _connect(self):
        """Connect to Postgres database"""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.conn.autocommit = False  # Use transactions
            logger.info("Task queue connected to Postgres")
        except Exception as e:
            logger.error(f"Failed to connect to Postgres: {e}")
            raise
    
    def _ensure_schema(self):
        """Ensure task_queue table exists"""
        try:
            with self.conn.cursor() as cursor:
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'task_queue'
                    )
                """)
                
                exists = cursor.fetchone()[0]
                
                if not exists:
                    logger.warning("task_queue table does not exist, creating...")
                    # Read schema from file
                    from pathlib import Path
                    schema_file = Path(__file__).parent.parent / "sql" / "task_queue.sql"
                    
                    if schema_file.exists():
                        with open(schema_file, 'r') as f:
                            schema_sql = f.read()
                        cursor.execute(schema_sql)
                        self.conn.commit()
                        logger.info("task_queue table created successfully")
                    else:
                        logger.error(f"Schema file not found: {schema_file}")
                        raise FileNotFoundError(f"Schema file not found: {schema_file}")
                else:
                    logger.debug("task_queue table exists")
        
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to ensure schema: {e}")
            raise
    
    def enqueue(
        self,
        task_type: str,
        data: Dict[str, Any],
        assigned_to: Optional[str] = None,
        priority: int = 5,
    ) -> str:
        """
        Add a task to the queue.
        
        Args:
            task_type: Type of task (e.g., 'consensus', 'thinkdeep')
            data: Task data as dictionary
            assigned_to: Optional agent/window ID to assign task to
            priority: Priority level (1-10, higher = more urgent)
            
        Returns:
            Task ID (UUID)
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO task_queue (task_type, status, assigned_to, priority, data)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    [task_type, TaskStatus.PENDING.value, assigned_to, priority, Json(data)]
                )
                
                task_id = cursor.fetchone()[0]
                self.conn.commit()
                
                logger.info(
                    f"Task enqueued: {task_id} (type={task_type}, priority={priority}, "
                    f"assigned_to={assigned_to})"
                )
                
                return str(task_id)
        
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to enqueue task: {e}")
            raise
    
    def dequeue(self, agent_id: Optional[str] = None, limit: int = 1) -> List[Task]:
        """
        Get pending tasks from queue.
        
        Args:
            agent_id: Optional agent/window ID to filter by assignment
            limit: Maximum number of tasks to return
            
        Returns:
            List of Task objects
        """
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cursor:
                if agent_id:
                    # Get tasks assigned to this agent or unassigned
                    cursor.execute(
                        """
                        SELECT * FROM task_queue
                        WHERE status = %s 
                        AND (assigned_to = %s OR assigned_to IS NULL)
                        ORDER BY priority DESC, created_at ASC
                        LIMIT %s
                        """,
                        [TaskStatus.PENDING.value, agent_id, limit]
                    )
                else:
                    # Get any pending tasks
                    cursor.execute(
                        """
                        SELECT * FROM task_queue
                        WHERE status = %s
                        ORDER BY priority DESC, created_at ASC
                        LIMIT %s
                        """,
                        [TaskStatus.PENDING.value, limit]
                    )
                
                rows = cursor.fetchall()
                tasks = [Task.from_db_row(row) for row in rows]
                
                logger.debug(f"Dequeued {len(tasks)} tasks (agent={agent_id}, limit={limit})")
                
                return tasks
        
        except Exception as e:
            logger.error(f"Failed to dequeue tasks: {e}")
            raise
    
    def claim_task(self, task_id: str, agent_id: str) -> bool:
        """
        Claim a task for execution (atomically set to RUNNING).
        
        Args:
            task_id: Task ID to claim
            agent_id: Agent/window ID claiming the task
            
        Returns:
            True if task was claimed successfully, False if already claimed
        """
        try:
            with self.conn.cursor() as cursor:
                # Atomically update task to RUNNING only if it's PENDING
                cursor.execute(
                    """
                    UPDATE task_queue
                    SET status = %s, assigned_to = %s
                    WHERE id = %s AND status = %s
                    RETURNING id
                    """,
                    [TaskStatus.RUNNING.value, agent_id, task_id, TaskStatus.PENDING.value]
                )
                
                result = cursor.fetchone()
                self.conn.commit()
                
                if result:
                    logger.info(f"Task {task_id} claimed by {agent_id}")
                    return True
                else:
                    logger.warning(f"Task {task_id} already claimed or not pending")
                    return False
        
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to claim task: {e}")
            raise
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
    ):
        """
        Update task status and optionally set result.
        
        Args:
            task_id: Task ID to update
            status: New status (pending, running, completed, failed, cancelled)
            result: Optional result data
        """
        try:
            with self.conn.cursor() as cursor:
                if status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                    # Set completed_at timestamp
                    cursor.execute(
                        """
                        UPDATE task_queue
                        SET status = %s, result = %s, completed_at = NOW()
                        WHERE id = %s
                        """,
                        [status, Json(result) if result else None, task_id]
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE task_queue
                        SET status = %s, result = %s
                        WHERE id = %s
                        """,
                        [status, Json(result) if result else None, task_id]
                    )
                
                self.conn.commit()
                logger.info(f"Task {task_id} status updated to {status}")
        
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to update task status: {e}")
            raise
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a specific task by ID.
        
        Args:
            task_id: Task ID to retrieve
            
        Returns:
            Task object or None if not found
        """
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM task_queue WHERE id = %s",
                    [task_id]
                )
                
                row = cursor.fetchone()
                
                if row:
                    return Task.from_db_row(row)
                else:
                    return None
        
        except Exception as e:
            logger.error(f"Failed to get task: {e}")
            raise
    
    def get_pending_tasks(
        self,
        agent_id: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> List[Task]:
        """
        Get all pending tasks, optionally filtered.
        
        Args:
            agent_id: Optional filter by assigned agent
            task_type: Optional filter by task type
            
        Returns:
            List of pending Task objects
        """
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cursor:
                query = "SELECT * FROM task_queue WHERE status = %s"
                params = [TaskStatus.PENDING.value]
                
                if agent_id:
                    query += " AND (assigned_to = %s OR assigned_to IS NULL)"
                    params.append(agent_id)
                
                if task_type:
                    query += " AND task_type = %s"
                    params.append(task_type)
                
                query += " ORDER BY priority DESC, created_at ASC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [Task.from_db_row(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to get pending tasks: {e}")
            raise
    
    def get_running_tasks(self, agent_id: Optional[str] = None) -> List[Task]:
        """
        Get all running tasks, optionally filtered by agent.
        
        Args:
            agent_id: Optional filter by assigned agent
            
        Returns:
            List of running Task objects
        """
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cursor:
                if agent_id:
                    cursor.execute(
                        """
                        SELECT * FROM task_queue
                        WHERE status = %s AND assigned_to = %s
                        ORDER BY created_at ASC
                        """,
                        [TaskStatus.RUNNING.value, agent_id]
                    )
                else:
                    cursor.execute(
                        """
                        SELECT * FROM task_queue
                        WHERE status = %s
                        ORDER BY created_at ASC
                        """,
                        [TaskStatus.RUNNING.value]
                    )
                
                rows = cursor.fetchall()
                return [Task.from_db_row(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to get running tasks: {e}")
            raise
    
    def cancel_task(self, task_id: str):
        """
        Cancel a task.
        
        Args:
            task_id: Task ID to cancel
        """
        self.update_task_status(task_id, TaskStatus.CANCELLED.value)
    
    def get_task_stats(self) -> Dict[str, Any]:
        """
        Get task queue statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cursor:
                # Count by status
                cursor.execute("""
                    SELECT status, COUNT(*) as count
                    FROM task_queue
                    GROUP BY status
                """)
                
                status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
                
                # Count by type
                cursor.execute("""
                    SELECT task_type, COUNT(*) as count
                    FROM task_queue
                    WHERE status = %s
                    GROUP BY task_type
                """, [TaskStatus.PENDING.value])
                
                type_counts = {row["task_type"]: row["count"] for row in cursor.fetchall()}
                
                # Average wait time for pending tasks
                cursor.execute("""
                    SELECT AVG(EXTRACT(EPOCH FROM (NOW() - created_at))) as avg_wait_seconds
                    FROM task_queue
                    WHERE status = %s
                """, [TaskStatus.PENDING.value])
                
                avg_wait = cursor.fetchone()["avg_wait_seconds"]
                
                return {
                    "status_counts": status_counts,
                    "type_counts": type_counts,
                    "avg_wait_seconds": float(avg_wait) if avg_wait else 0.0,
                    "total_pending": status_counts.get(TaskStatus.PENDING.value, 0),
                    "total_running": status_counts.get(TaskStatus.RUNNING.value, 0),
                    "total_completed": status_counts.get(TaskStatus.COMPLETED.value, 0),
                    "total_failed": status_counts.get(TaskStatus.FAILED.value, 0),
                }
        
        except Exception as e:
            logger.error(f"Failed to get task stats: {e}")
            raise
    
    def cleanup_old_tasks(self, days: int = 7):
        """
        Clean up completed/failed/cancelled tasks older than N days.
        
        Args:
            days: Number of days to keep
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM task_queue
                    WHERE status IN (%s, %s, %s)
                    AND completed_at < NOW() - INTERVAL '%s days'
                    RETURNING id
                    """,
                    [
                        TaskStatus.COMPLETED.value,
                        TaskStatus.FAILED.value,
                        TaskStatus.CANCELLED.value,
                        days
                    ]
                )
                
                deleted = cursor.rowcount
                self.conn.commit()
                
                logger.info(f"Cleaned up {deleted} old tasks (older than {days} days)")
                
                return deleted
        
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to cleanup old tasks: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Task queue connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

