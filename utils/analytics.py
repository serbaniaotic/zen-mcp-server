"""
Analytics module for Zen MCP Server using DuckDB.
Tracks tool executions, routing decisions, and model performance.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import duckdb

logger = logging.getLogger(__name__)


class ZenAnalytics:
    """Analytics engine for Zen MCP Server using DuckDB"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize analytics engine with DuckDB.
        
        Args:
            db_path: Path to DuckDB database file. If None, uses ~/.zen-mcp/analytics.duckdb
        """
        if db_path is None:
            db_path = Path.home() / ".zen-mcp" / "analytics.duckdb"
        else:
            db_path = Path(db_path)
        
        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = str(db_path)
        self.conn = duckdb.connect(self.db_path)
        
        logger.info(f"Analytics database initialized at {self.db_path}")
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema from SQL file"""
        schema_path = Path(__file__).parent / "analytics_schema.sql"
        
        if not schema_path.exists():
            logger.error(f"Schema file not found: {schema_path}")
            raise FileNotFoundError(f"Analytics schema file not found: {schema_path}")
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Execute schema creation
        self.conn.execute(schema_sql)
        logger.info("Analytics schema initialized successfully")

    def log_tool_execution(
        self,
        tool_name: str,
        model: Optional[str] = None,
        tokens_used: Optional[int] = None,
        execution_time_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        status: str = "completed",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Log a tool execution event.
        
        Args:
            tool_name: Name of the tool executed
            model: Model used (if applicable)
            tokens_used: Number of tokens used
            execution_time_ms: Execution time in milliseconds
            success: Whether execution succeeded
            error_message: Error message if failed
            status: Execution status (pending, running, completed, failed)
            metadata: Additional metadata as dictionary
            
        Returns:
            Execution ID
        """
        execution_id = str(uuid4())
        
        self.conn.execute(
            """
            INSERT INTO tool_executions (
                id, tool_name, model, status, tokens_used, 
                execution_time_ms, success, error_message, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                execution_id,
                tool_name,
                model,
                status,
                tokens_used,
                execution_time_ms,
                success,
                error_message,
                json.dumps(metadata) if metadata else None,
            ],
        )
        
        logger.debug(
            f"Logged execution: {tool_name} (model={model}, success={success}, "
            f"tokens={tokens_used}, time={execution_time_ms}ms)"
        )
        
        return execution_id

    def log_routing_decision(
        self,
        user_intent: str,
        chosen_tool: str,
        chosen_strategy: str,
        detected_complexity: int,
        detected_risk: int,
        outcome: str = "pending",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Log a routing decision.
        
        Args:
            user_intent: User's original query/intent
            chosen_tool: Tool selected by router
            chosen_strategy: Strategy used (SOLO, CONSENSUS, SEQUENTIAL, PARALLEL)
            detected_complexity: Complexity score (1-10)
            detected_risk: Risk score (1-10)
            outcome: Outcome of the routing (pending, success, failure)
            metadata: Additional metadata
            
        Returns:
            Routing decision ID
        """
        decision_id = str(uuid4())
        
        self.conn.execute(
            """
            INSERT INTO routing_decisions (
                id, user_intent, detected_complexity, detected_risk,
                chosen_tool, chosen_strategy, outcome, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                decision_id,
                user_intent,
                detected_complexity,
                detected_risk,
                chosen_tool,
                chosen_strategy,
                outcome,
                json.dumps(metadata) if metadata else None,
            ],
        )
        
        logger.debug(
            f"Logged routing: {chosen_tool} ({chosen_strategy}) - "
            f"complexity={detected_complexity}, risk={detected_risk}"
        )
        
        return decision_id

    def update_model_performance(self):
        """
        Update model performance aggregations based on recent executions.
        This should be called periodically to refresh performance metrics.
        """
        self.conn.execute(
            """
            INSERT OR REPLACE INTO model_performance (
                id, tool_name, model, success_rate, avg_tokens, 
                avg_time_ms, sample_size, last_updated
            )
            SELECT 
                tool_name || '-' || COALESCE(model, 'unknown') as id,
                tool_name,
                model,
                CAST(SUM(CASE WHEN success THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as success_rate,
                CAST(AVG(tokens_used) AS INTEGER) as avg_tokens,
                CAST(AVG(execution_time_ms) AS INTEGER) as avg_time_ms,
                COUNT(*) as sample_size,
                CURRENT_TIMESTAMP as last_updated
            FROM tool_executions
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            GROUP BY tool_name, model
            """
        )
        
        logger.info("Model performance metrics updated")

    def get_tool_performance(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get tool performance metrics for the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of performance metrics dictionaries
        """
        result = self.conn.execute(
            f"""
            SELECT 
                tool_name,
                model,
                COUNT(*) as total_executions,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_executions,
                CAST(SUM(CASE WHEN success THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as success_rate,
                AVG(tokens_used) as avg_tokens,
                AVG(execution_time_ms) as avg_time_ms,
                SUM(tokens_used) as total_tokens
            FROM tool_executions
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
            GROUP BY tool_name, model
            ORDER BY total_executions DESC
            """
        ).fetchall()
        
        return [
            {
                "tool_name": row[0],
                "model": row[1],
                "total_executions": row[2],
                "successful_executions": row[3],
                "success_rate": row[4],
                "avg_tokens": row[5],
                "avg_time_ms": row[6],
                "total_tokens": row[7],
            }
            for row in result
        ]

    def get_best_tool_for(
        self,
        intent: Optional[str] = None,
        complexity: Optional[int] = None,
        risk: Optional[int] = None,
        days: int = 30,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the best tool for a given intent/complexity/risk based on historical performance.
        
        Args:
            intent: User intent keyword (optional)
            complexity: Complexity level 1-10 (optional)
            risk: Risk level 1-10 (optional)
            days: Number of days of history to consider
            
        Returns:
            Best tool recommendation or None if no data
        """
        # Build query based on provided filters
        conditions = [f"r.created_at >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS"]
        
        if intent:
            intent_filter = intent.lower().replace("'", "''")  # SQL escape
            conditions.append(f"LOWER(r.user_intent) LIKE '%{intent_filter}%'")
        
        if complexity is not None:
            conditions.append(f"ABS(r.detected_complexity - {complexity}) <= 2")
        
        if risk is not None:
            conditions.append(f"ABS(r.detected_risk - {risk}) <= 2")
        
        where_clause = " AND ".join(conditions)
        
        result = self.conn.execute(
            f"""
            SELECT 
                r.chosen_tool,
                r.chosen_strategy,
                COUNT(*) as usage_count,
                SUM(CASE WHEN r.outcome = 'success' THEN 1 ELSE 0 END) as success_count,
                CAST(SUM(CASE WHEN r.outcome = 'success' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as success_rate
            FROM routing_decisions r
            WHERE {where_clause}
            GROUP BY r.chosen_tool, r.chosen_strategy
            HAVING success_rate >= 0.5
            ORDER BY success_rate DESC, usage_count DESC
            LIMIT 1
            """
        ).fetchone()
        
        if result:
            return {
                "tool": result[0],
                "strategy": result[1],
                "usage_count": result[2],
                "success_count": result[3],
                "success_rate": result[4],
            }
        
        return None

    def get_routing_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent routing decisions.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of routing decision dictionaries
        """
        result = self.conn.execute(
            f"""
            SELECT 
                id, user_intent, detected_complexity, detected_risk,
                chosen_tool, chosen_strategy, outcome, created_at
            FROM routing_decisions
            ORDER BY created_at DESC
            LIMIT {limit}
            """
        ).fetchall()
        
        return [
            {
                "id": row[0],
                "user_intent": row[1],
                "detected_complexity": row[2],
                "detected_risk": row[3],
                "chosen_tool": row[4],
                "chosen_strategy": row[5],
                "outcome": row[6],
                "created_at": row[7],
            }
            for row in result
        ]

    def get_summary_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get summary statistics for the analytics dashboard.
        
        Args:
            days: Number of days to include
            
        Returns:
            Dictionary with summary statistics
        """
        # Total executions
        total_executions = self.conn.execute(
            f"""
            SELECT COUNT(*) FROM tool_executions
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
            """
        ).fetchone()[0]
        
        # Success rate
        success_rate = self.conn.execute(
            f"""
            SELECT 
                CAST(SUM(CASE WHEN success THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*)
            FROM tool_executions
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
            """
        ).fetchone()[0] or 0.0
        
        # Most used tool
        most_used = self.conn.execute(
            f"""
            SELECT tool_name, COUNT(*) as count
            FROM tool_executions
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
            GROUP BY tool_name
            ORDER BY count DESC
            LIMIT 1
            """
        ).fetchone()
        
        # Average tokens and time
        avg_stats = self.conn.execute(
            f"""
            SELECT 
                AVG(tokens_used) as avg_tokens,
                AVG(execution_time_ms) as avg_time_ms,
                SUM(tokens_used) as total_tokens
            FROM tool_executions
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL {days} DAYS
            """
        ).fetchone()
        
        return {
            "period_days": days,
            "total_executions": total_executions,
            "success_rate": success_rate,
            "most_used_tool": most_used[0] if most_used else None,
            "most_used_tool_count": most_used[1] if most_used else 0,
            "avg_tokens_per_execution": avg_stats[0] or 0,
            "avg_time_ms_per_execution": avg_stats[1] or 0,
            "total_tokens_used": avg_stats[2] or 0,
        }

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Analytics database connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

