# Database Usage Guide - Zen MCP Server

**Updated**: 2025-10-12  
**Phase 1**: Database Setup + DuckDB Installation  
**Status**: ✅ Operational

---

## Quick Access

### Python API

```python
# Import modules
from utils.analytics import ZenAnalytics
from utils.db_config import DatabaseConfig
import psycopg2

# Initialize analytics
analytics = ZenAnalytics()

# Get Postgres connection
conn = psycopg2.connect(**DatabaseConfig.get_postgres_dsn())
```

---

## Analytics (DuckDB)

### Basic Usage

```python
from utils.analytics import ZenAnalytics

# Use as context manager (recommended)
with ZenAnalytics() as analytics:
    # Your code here
    summary = analytics.get_summary_stats()
    print(summary)
    
# Or manual management
analytics = ZenAnalytics()
try:
    # Your code here
    pass
finally:
    analytics.close()
```

### Log Tool Execution

```python
analytics = ZenAnalytics()

# Simple logging
exec_id = analytics.log_tool_execution(
    tool_name="chat",
    model="gemini-2.5-pro",
    tokens_used=1500,
    execution_time_ms=2500,
    success=True
)

# With metadata
exec_id = analytics.log_tool_execution(
    tool_name="thinkdeep",
    model="gpt-5",
    tokens_used=3000,
    execution_time_ms=5000,
    success=True,
    status="completed",
    metadata={
        "complexity": 8,
        "steps": 5,
        "user_query": "Debug memory leak"
    }
)
```

### Log Routing Decision

```python
decision_id = analytics.log_routing_decision(
    user_intent="Review code for security issues",
    chosen_tool="codereview",
    chosen_strategy="SOLO",
    detected_complexity=6,
    detected_risk=8,
    outcome="success",
    metadata={
        "files_reviewed": 5,
        "issues_found": 3
    }
)
```

### Query Performance

```python
# Get tool performance (last 7 days)
performance = analytics.get_tool_performance(days=7)

for tool in performance:
    print(f"\n{tool['tool_name']} ({tool['model']})")
    print(f"  Executions: {tool['total_executions']}")
    print(f"  Success rate: {tool['success_rate']:.1%}")
    print(f"  Avg tokens: {tool['avg_tokens']:.0f}")
    print(f"  Avg time: {tool['avg_time_ms']:.0f}ms")
    print(f"  Total tokens: {tool['total_tokens']:.0f}")

# Get last 30 days
performance = analytics.get_tool_performance(days=30)
```

### Get Recommendations

```python
# Get best tool for a task
recommendation = analytics.get_best_tool_for(
    intent="debug",      # Optional: keyword in user intent
    complexity=7,        # Optional: complexity level 1-10
    risk=5,             # Optional: risk level 1-10
    days=30             # Look back 30 days
)

if recommendation:
    print(f"Recommended tool: {recommendation['tool']}")
    print(f"Strategy: {recommendation['strategy']}")
    print(f"Success rate: {recommendation['success_rate']:.1%}")
    print(f"Based on: {recommendation['usage_count']} past uses")
else:
    print("No recommendation available (need more data)")
```

### Get Summary Statistics

```python
# Dashboard stats
summary = analytics.get_summary_stats(days=7)

print(f"Period: {summary['period_days']} days")
print(f"Total executions: {summary['total_executions']}")
print(f"Success rate: {summary['success_rate']:.1%}")
print(f"Most used tool: {summary['most_used_tool']}")
print(f"Most used count: {summary['most_used_tool_count']}")
print(f"Avg tokens: {summary['avg_tokens_per_execution']:.0f}")
print(f"Avg time: {summary['avg_time_ms_per_execution']:.0f}ms")
print(f"Total tokens: {summary['total_tokens_used']:.0f}")
```

### Get Routing History

```python
# Get recent routing decisions
history = analytics.get_routing_history(limit=10)

for decision in history:
    print(f"\n{decision['created_at']}")
    print(f"  Intent: {decision['user_intent'][:50]}...")
    print(f"  Chosen: {decision['chosen_tool']} ({decision['chosen_strategy']})")
    print(f"  Complexity: {decision['detected_complexity']}/10")
    print(f"  Risk: {decision['detected_risk']}/10")
    print(f"  Outcome: {decision['outcome']}")
```

### Update Performance Aggregations

```python
# Update model performance metrics (run periodically)
analytics.update_model_performance()
```

---

## Task Queue (Postgres)

### Connect to Database

```python
from utils.db_config import DatabaseConfig
import psycopg2
import json

# Connect
conn = psycopg2.connect(**DatabaseConfig.get_postgres_dsn())
cursor = conn.cursor()
```

### Create Task

```python
# Insert a task
cursor.execute(
    """
    INSERT INTO task_queue (task_type, status, assigned_to, priority, data)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id
    """,
    [
        "consensus",
        "pending",
        "window-1",
        8,  # priority (1-10)
        json.dumps({
            "question": "Should we use approach A or B?",
            "models": ["gpt-5", "gemini-2.5-pro", "claude-4"],
            "voting_strategy": "best_reasoning"
        })
    ]
)

task_id = cursor.fetchone()[0]
conn.commit()
print(f"Created task: {task_id}")
```

### Get Pending Tasks

```python
# Get all pending tasks
cursor.execute("SELECT * FROM v_pending_tasks")
tasks = cursor.fetchall()

for task in tasks:
    print(f"Task ID: {task[0]}")
    print(f"Type: {task[1]}")
    print(f"Assigned to: {task[2]}")
    print(f"Priority: {task[3]}")
    print(f"Created: {task[4]}")
    print(f"Data: {task[5]}")
    print()
```

### Update Task Status

```python
# Update task status
cursor.execute(
    """
    UPDATE task_queue 
    SET status = %s, completed_at = NOW(), result = %s
    WHERE id = %s
    """,
    [
        "completed",
        json.dumps({
            "decision": "Approach A",
            "consensus": 0.8,
            "reasoning": "Better performance and maintainability"
        }),
        task_id
    ]
)
conn.commit()
```

### Query Task Statistics

```python
# Get task statistics
cursor.execute("SELECT * FROM v_task_stats")
stats = cursor.fetchall()

for stat in stats:
    task_type, status, count, avg_duration = stat
    print(f"{task_type} - {status}: {count} tasks, avg {avg_duration:.1f}s")
```

---

## Configuration Management

### View All Configuration

```python
from utils.db_config import DatabaseConfig

# Print summary
DatabaseConfig.print_config_summary()
```

### Get Connection Details

```python
# Postgres connection string
conn_str = DatabaseConfig.get_postgres_connection_string()
print(f"Connection: {conn_str}")

# Postgres DSN (for psycopg2)
dsn = DatabaseConfig.get_postgres_dsn()
print(f"Host: {dsn['host']}")
print(f"Port: {dsn['port']}")
print(f"Database: {dsn['database']}")

# DuckDB path
duckdb_path = DatabaseConfig.get_duckdb_path()
print(f"DuckDB: {duckdb_path}")

# Memgraph URI
memgraph_uri = DatabaseConfig.get_memgraph_uri()
print(f"Memgraph: {memgraph_uri}")
```

### Validate Connections

```python
# Validate Postgres
if DatabaseConfig.validate_postgres():
    print("✅ Postgres is accessible")
else:
    print("❌ Postgres connection failed")

# Validate DuckDB
if DatabaseConfig.validate_duckdb():
    print("✅ DuckDB is accessible")
else:
    print("❌ DuckDB connection failed")
```

---

## Command Line Usage

### View Analytics from CLI

```bash
# Summary stats
python -c "
from utils.analytics import ZenAnalytics
with ZenAnalytics() as a:
    summary = a.get_summary_stats(days=7)
    print(f'Executions: {summary[\"total_executions\"]}')
    print(f'Success rate: {summary[\"success_rate\"]:.1%}')
    print(f'Most used: {summary[\"most_used_tool\"]}')
"

# Tool performance
python -c "
from utils.analytics import ZenAnalytics
with ZenAnalytics() as a:
    for tool in a.get_tool_performance(days=7):
        print(f'{tool[\"tool_name\"]}: {tool[\"success_rate\"]:.1%}')
"
```

### Check Configuration

```bash
python -m utils.db_config
```

### Connect to Postgres

```bash
# Via Docker
docker exec -it zen-postgres psql -U zen -d zendb

# Then in psql:
\dt                              # List tables
SELECT * FROM v_pending_tasks;   # View pending tasks
SELECT * FROM v_task_stats;      # View statistics
\q                               # Exit
```

---

## Integration Examples

### Example: Log Tool Execution with Analytics

```python
import time
from utils.analytics import ZenAnalytics

def execute_tool_with_logging(tool_name, model, user_query):
    """Execute a tool and log to analytics"""
    analytics = ZenAnalytics()
    
    start_time = time.time()
    
    try:
        # Execute tool (your code here)
        result = execute_tool(tool_name, model, user_query)
        
        # Calculate metrics
        execution_time_ms = int((time.time() - start_time) * 1000)
        tokens_used = result.get('tokens', 0)
        
        # Log success
        analytics.log_tool_execution(
            tool_name=tool_name,
            model=model,
            tokens_used=tokens_used,
            execution_time_ms=execution_time_ms,
            success=True,
            status="completed",
            metadata={"user_query": user_query[:100]}
        )
        
        return result
        
    except Exception as e:
        # Log failure
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        analytics.log_tool_execution(
            tool_name=tool_name,
            model=model,
            execution_time_ms=execution_time_ms,
            success=False,
            status="failed",
            error_message=str(e)
        )
        
        raise
    
    finally:
        analytics.close()
```

### Example: Intelligent Tool Selection

```python
from utils.analytics import ZenAnalytics

def select_best_tool(user_query, complexity, risk):
    """Select best tool based on historical data"""
    
    # Extract intent
    intent = extract_intent(user_query)  # Your implementation
    
    # Get recommendation from analytics
    analytics = ZenAnalytics()
    recommendation = analytics.get_best_tool_for(
        intent=intent,
        complexity=complexity,
        risk=risk,
        days=30
    )
    analytics.close()
    
    if recommendation:
        return recommendation['tool'], recommendation['strategy']
    else:
        # Fallback to default logic
        return select_default_tool(complexity, risk)
```

---

## Best Practices

### 1. Always Use Context Managers

```python
# Good ✅
with ZenAnalytics() as analytics:
    summary = analytics.get_summary_stats()
    
# Avoid ❌
analytics = ZenAnalytics()
summary = analytics.get_summary_stats()
# Forgot to call analytics.close()
```

### 2. Log All Tool Executions

Every tool execution should be logged for analytics:

```python
# Log both successes and failures
analytics.log_tool_execution(
    tool_name=tool_name,
    model=model,
    tokens_used=tokens,
    execution_time_ms=time_ms,
    success=success,
    error_message=error if not success else None
)
```

### 3. Include Useful Metadata

```python
# Add context for future analysis
analytics.log_tool_execution(
    tool_name="consensus",
    model="multi",
    tokens_used=5000,
    execution_time_ms=10000,
    success=True,
    metadata={
        "models_used": ["gpt-5", "gemini-2.5-pro", "claude-4"],
        "voting_strategy": "best_reasoning",
        "agreement_score": 0.85,
        "task_category": "architecture_decision"
    }
)
```

### 4. Periodically Update Performance Metrics

```python
# Run this periodically (e.g., daily)
with ZenAnalytics() as analytics:
    analytics.update_model_performance()
```

### 5. Handle Errors Gracefully

```python
try:
    with ZenAnalytics() as analytics:
        analytics.log_tool_execution(...)
except Exception as e:
    # Log error but don't fail the main operation
    logger.error(f"Failed to log to analytics: {e}")
```

---

## Troubleshooting

### Analytics Not Recording Data

```python
# Check database file exists
from pathlib import Path
db_path = Path.home() / ".zen-mcp" / "analytics.duckdb"
print(f"Exists: {db_path.exists()}")
print(f"Size: {db_path.stat().st_size if db_path.exists() else 0} bytes")

# Verify schema
with ZenAnalytics() as analytics:
    result = analytics.conn.execute("SHOW TABLES").fetchall()
    print("Tables:", [r[0] for r in result])
```

### Postgres Connection Issues

```python
# Test connection
from utils.db_config import DatabaseConfig
import psycopg2

try:
    conn = psycopg2.connect(**DatabaseConfig.get_postgres_dsn())
    print("✅ Connection successful")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
    
# Check container
# docker ps | grep zen-postgres
# docker logs zen-postgres
```

### Performance Issues

```python
# Check database sizes
from pathlib import Path

# DuckDB
db_path = Path.home() / ".zen-mcp" / "analytics.duckdb"
if db_path.exists():
    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"DuckDB size: {size_mb:.2f} MB")

# If too large, consider archiving old data
```

---

## Reference

- **Analytics Module**: `zen-mcp-server/utils/analytics.py`
- **Configuration**: `zen-mcp-server/utils/db_config.py`
- **Schemas**: `zen-mcp-server/utils/analytics_schema.sql`, `zen-mcp-server/sql/task_queue.sql`
- **Tests**: `zen-mcp-server/test_phase1_databases.py`
- **Quick Reference**: `zen-mcp-server/PHASE1-QUICK-REFERENCE.md`

---

**Updated**: 2025-10-12  
**Phase**: 1 Complete  
**Next**: Phase 2 - Intelligent Router

