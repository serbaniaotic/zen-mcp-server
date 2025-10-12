# Phase 1 Quick Reference Guide

**Task 8 - Phase 1: Database Setup + DuckDB Installation**  
**Status**: ✅ COMPLETE

---

## Quick Start

### 1. Test Everything

```bash
cd /home/dingo/code/zen-mcp-server
source .zen_venv/bin/activate
python test_phase1_databases.py
```

Expected output: All tests pass ✅

### 2. Check Configuration

```bash
source .zen_venv/bin/activate
python -m utils.db_config
```

---

## Database Access

### Postgres (Task Queue)

```python
from utils.db_config import DatabaseConfig
import psycopg2

conn = psycopg2.connect(**DatabaseConfig.get_postgres_dsn())
cursor = conn.cursor()
cursor.execute("SELECT * FROM task_queue")
```

**Manual Connection**:
```bash
docker exec -it zen-postgres psql -U zen -d zendb
```

### DuckDB (Analytics)

```python
from utils.analytics import ZenAnalytics

with ZenAnalytics() as analytics:
    # Log execution
    analytics.log_tool_execution(
        tool_name="chat",
        model="gemini-2.5-pro",
        tokens_used=1500,
        execution_time_ms=2500,
        success=True
    )
    
    # Get performance
    performance = analytics.get_tool_performance(days=7)
    print(performance)
    
    # Get summary
    summary = analytics.get_summary_stats(days=7)
    print(f"Total executions: {summary['total_executions']}")
    print(f"Success rate: {summary['success_rate']:.1%}")
```

---

## Common Tasks

### View Analytics

```bash
source .zen_venv/bin/activate
python -c "
from utils.analytics import ZenAnalytics
a = ZenAnalytics()
summary = a.get_summary_stats(days=7)
print('Total executions:', summary['total_executions'])
print('Success rate:', f\"{summary['success_rate']:.1%}\")
print('Most used tool:', summary['most_used_tool'])
a.close()
"
```

### Check Postgres Container

```bash
# Check status
docker ps | grep zen-postgres

# Check connection
docker exec zen-postgres pg_isready -U zen

# View logs
docker logs zen-postgres

# Connect to database
docker exec -it zen-postgres psql -U zen -d zendb
```

### Restart Postgres

```bash
docker restart zen-postgres
```

---

## File Locations

### Code Files
- Analytics module: `/home/dingo/code/zen-mcp-server/utils/analytics.py`
- Analytics schema: `/home/dingo/code/zen-mcp-server/utils/analytics_schema.sql`
- DB config: `/home/dingo/code/zen-mcp-server/utils/db_config.py`
- Task queue schema: `/home/dingo/code/zen-mcp-server/sql/task_queue.sql`
- Test suite: `/home/dingo/code/zen-mcp-server/test_phase1_databases.py`

### Database Files
- DuckDB: `~/.zen-mcp/analytics.duckdb`
- Postgres: Docker volume (managed by Docker)

### Documentation
- Phase 1 complete: `/home/dingo/code/workspaces/1-current-week/daily/day-6/task-8-agent-fusion-integration-intelligent-routing-duckd/evidence/PHASE1-COMPLETE.md`
- Task file: `/home/dingo/code/workspaces/1-current-week/daily/day-6/task-8-agent-fusion-integration-intelligent-routing-duckd/TASK.md`

---

## Connection Details

### Postgres
- **Host**: localhost
- **Port**: 5434
- **Database**: zendb
- **User**: zen
- **Password**: zenpass
- **Connection String**: `postgresql://zen:zenpass@localhost:5434/zendb`

### DuckDB
- **Path**: `~/.zen-mcp/analytics.duckdb`
- **Type**: File-based (no server)

---

## Troubleshooting

### Postgres not responding

```bash
# Restart
docker restart zen-postgres

# Check logs
docker logs zen-postgres --tail 50

# Recreate if needed
docker stop zen-postgres
docker rm zen-postgres
docker run -d --name zen-postgres -e POSTGRES_PASSWORD=zenpass -e POSTGRES_USER=zen -e POSTGRES_DB=zendb -p 5434:5432 --restart unless-stopped postgres:16-alpine
```

### DuckDB file issues

```bash
# Check file
ls -lh ~/.zen-mcp/analytics.duckdb

# Backup and recreate
mv ~/.zen-mcp/analytics.duckdb ~/.zen-mcp/analytics.duckdb.backup
python -c "from utils.analytics import ZenAnalytics; ZenAnalytics()"
```

### Import errors

```bash
# Reinstall dependencies
cd /home/dingo/code/zen-mcp-server
source .zen_venv/bin/activate
pip install -r requirements.txt
```

---

## What's Next?

**Phase 2: Intelligent Router** (4-6 hours)

Create intelligent routing layer that automatically selects optimal tools based on:
- Task complexity analysis
- Risk assessment  
- Historical performance patterns
- Natural language directives

Files to create:
- `routing/__init__.py`
- `routing/intelligent_router.py`

Integration points:
- `server.py` - Add router before tool execution
- All tools - Add analytics logging

---

## Quick Commands Cheatsheet

```bash
# Activate environment
cd /home/dingo/code/zen-mcp-server && source .zen_venv/bin/activate

# Run tests
python test_phase1_databases.py

# Check config
python -m utils.db_config

# View analytics summary
python -c "from utils.analytics import ZenAnalytics; a = ZenAnalytics(); print(a.get_summary_stats()); a.close()"

# Check Postgres
docker exec zen-postgres pg_isready -U zen

# Connect to Postgres
docker exec -it zen-postgres psql -U zen -d zendb

# View container logs
docker logs zen-postgres

# Restart Postgres
docker restart zen-postgres
```

---

## Success Metrics

✅ All Phase 1 objectives met:
- Postgres container running on port 5434
- DuckDB installed and functional
- Analytics schema created with 3 tables + 3 views
- Analytics module with 8+ methods
- Task queue schema in Postgres
- Comprehensive test suite (all passing)
- Database configuration module
- Documentation complete

**Ready for Phase 2!** 🚀

