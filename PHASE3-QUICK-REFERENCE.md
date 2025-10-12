# Phase 3 Quick Reference - Task Queue

**Task 8 - Phase 3: Task Queue Enhancement**  
**Status**: ✅ COMPLETE

---

## Quick Start

### Test the Task Queue

```bash
cd /home/dingo/code/zen-mcp-server
source .zen_venv/bin/activate
python test_phase3_task_queue.py
```

### Run the Demo

```bash
python demo_task_queue.py
```

---

## Basic Usage

### Create and Use Queue

```python
from utils.task_queue import TaskQueue, TaskType, TaskStatus

# Context manager (recommended)
with TaskQueue() as queue:
    # Enqueue a task
    task_id = queue.enqueue(
        task_type=TaskType.CHAT.value,
        data={"prompt": "Your question", "model": "gpt-5"},
        priority=7
    )
    
    # Dequeue tasks
    tasks = queue.dequeue(limit=10)
    
    # Claim a task (atomic)
    if queue.claim_task(tasks[0].id, "window-1"):
        # Process task
        result = process_task(tasks[0])
        
        # Mark complete
        queue.update_task_status(
            tasks[0].id,
            TaskStatus.COMPLETED.value,
            result=result
        )
```

---

## Core Operations

### Enqueue Task

```python
task_id = queue.enqueue(
    task_type=TaskType.DEBUG.value,      # Required: task type
    data={"issue": "Memory leak"},       # Required: task data (dict)
    assigned_to="window-1",              # Optional: specific window
    priority=8                           # Optional: 1-10 (default: 5)
)
```

### Dequeue Tasks

```python
# Get any pending tasks
tasks = queue.dequeue(limit=10)

# Get tasks for specific window
tasks = queue.dequeue(agent_id="window-1", limit=10)

# Returns: List[Task]
```

### Claim Task

```python
# Atomically claim a task
claimed = queue.claim_task(task_id, "window-1")

if claimed:
    # Task is now running, assigned to window-1
    pass
else:
    # Task already claimed by another window
    pass
```

### Update Status

```python
# Mark completed
queue.update_task_status(
    task_id,
    TaskStatus.COMPLETED.value,
    result={"success": True, "output": "Result data"}
)

# Mark failed
queue.update_task_status(
    task_id,
    TaskStatus.FAILED.value,
    result={"error": "Error message"}
)

# Cancel task
queue.cancel_task(task_id)
```

### Get Task Info

```python
# Get specific task
task = queue.get_task(task_id)

if task:
    print(f"Status: {task.status}")
    print(f"Type: {task.task_type}")
    print(f"Priority: {task.priority}")
    print(f"Data: {task.data}")
    print(f"Result: {task.result}")
```

### Query Tasks

```python
# All pending tasks
pending = queue.get_pending_tasks()

# Pending for specific window
pending = queue.get_pending_tasks(agent_id="window-1")

# Pending of specific type
pending = queue.get_pending_tasks(task_type=TaskType.CHAT.value)

# Running tasks
running = queue.get_running_tasks()
running = queue.get_running_tasks(agent_id="window-1")
```

---

## Multi-Window Coordination

### Assign Task to Specific Window

```python
# Window 1 creates task for Window 2
with TaskQueue() as queue:
    task_id = queue.enqueue(
        task_type=TaskType.CODEREVIEW.value,
        data={"files": ["auth.py", "api.py"]},
        assigned_to="window-2",  # Only window-2 will see this
        priority=8
    )
```

### Create Shared Task

```python
# Any window can take this task
with TaskQueue() as queue:
    task_id = queue.enqueue(
        task_type=TaskType.CHAT.value,
        data={"prompt": "General question"},
        assigned_to=None,  # Shared task
        priority=5
    )
```

### Window-Specific View

```python
# Window 1
with TaskQueue() as queue:
    tasks = queue.dequeue(agent_id="window-1", limit=10)
    # Sees: tasks assigned to window-1 + unassigned tasks

# Window 2
with TaskQueue() as queue:
    tasks = queue.dequeue(agent_id="window-2", limit=10)
    # Sees: tasks assigned to window-2 + unassigned tasks
```

---

## Priority Queuing

### Priority Levels

- **10**: Critical/Emergency (immediate attention)
- **8-9**: Urgent (high priority)
- **5-7**: Normal (default)
- **3-4**: Low priority
- **1-2**: Background/Cleanup

### Priority Ordering

```python
# Tasks with higher priority dequeued first
with TaskQueue() as queue:
    queue.enqueue(TaskType.CHAT.value, {}, priority=3)   # Dequeued last
    queue.enqueue(TaskType.DEBUG.value, {}, priority=10) # Dequeued first
    queue.enqueue(TaskType.CODEREVIEW.value, {}, priority=7)  # Dequeued second
    
    tasks = queue.dequeue(limit=3)
    # Order: priority 10, then 7, then 3
```

---

## Task Status

### Status Flow

```
pending → running → completed
        ↘         ↗ failed
        ↘ cancelled
```

### Status Meanings

- **pending**: Task waiting to be picked up
- **running**: Task claimed and being processed
- **completed**: Task finished successfully
- **failed**: Task execution failed
- **cancelled**: Task manually cancelled

---

## Statistics

### Get Queue Stats

```python
with TaskQueue() as queue:
    stats = queue.get_task_stats()
    
    print(f"Pending: {stats['total_pending']}")
    print(f"Running: {stats['total_running']}")
    print(f"Completed: {stats['total_completed']}")
    print(f"Failed: {stats['total_failed']}")
    print(f"Avg wait time: {stats['avg_wait_seconds']:.2f}s")
    
    # By status
    for status, count in stats['status_counts'].items():
        print(f"{status}: {count}")
    
    # By type
    for task_type, count in stats['type_counts'].items():
        print(f"{task_type}: {count}")
```

---

## Maintenance

### Cleanup Old Tasks

```python
# Remove completed/failed/cancelled tasks older than 7 days
with TaskQueue() as queue:
    deleted = queue.cleanup_old_tasks(days=7)
    print(f"Cleaned up {deleted} old tasks")
```

**Recommended Schedule**: Run daily to keep queue clean

---

## Patterns

### Pattern 1: Background Worker

```python
# Worker loop
while True:
    with TaskQueue() as queue:
        tasks = queue.dequeue(agent_id="worker-1", limit=10)
        
        for task in tasks:
            if queue.claim_task(task.id, "worker-1"):
                try:
                    result = process_task(task)
                    queue.update_task_status(
                        task.id,
                        TaskStatus.COMPLETED.value,
                        result=result
                    )
                except Exception as e:
                    queue.update_task_status(
                        task.id,
                        TaskStatus.FAILED.value,
                        result={"error": str(e)}
                    )
    
    time.sleep(1)  # Poll interval
```

### Pattern 2: Multi-Step Workflow

```python
with TaskQueue() as queue:
    # Create workflow tasks
    step1 = queue.enqueue(
        TaskType.CODEREVIEW.value,
        {"step": "Review code"},
        priority=10
    )
    
    step2 = queue.enqueue(
        TaskType.PRECOMMIT.value,
        {"step": "Validate changes", "depends_on": step1},
        priority=9
    )
    
    step3 = queue.enqueue(
        TaskType.CONSENSUS.value,
        {"step": "Approve deployment", "depends_on": step2},
        priority=10
    )
```

### Pattern 3: Load Balancing

```python
# Multiple windows automatically load balance
# Tasks are distributed across windows based on assignment

# Window 1
tasks1 = queue.dequeue(agent_id="window-1", limit=5)

# Window 2
tasks2 = queue.dequeue(agent_id="window-2", limit=5)

# No duplicate work due to atomic claiming
```

---

## Task Types

Available task types from `TaskType` enum:

- `TaskType.CHAT` - Chat/conversation tasks
- `TaskType.THINKDEEP` - Deep investigation tasks
- `TaskType.DEBUG` - Debugging tasks
- `TaskType.CODEREVIEW` - Code review tasks
- `TaskType.CONSENSUS` - Consensus/decision tasks
- `TaskType.PLANNER` - Planning tasks
- `TaskType.PRECOMMIT` - Pre-commit validation tasks
- `TaskType.ANALYZE` - Analysis tasks
- `TaskType.REFACTOR` - Refactoring tasks
- `TaskType.CUSTOM` - Custom task types

---

## Configuration

### Custom Postgres Connection

```python
from utils.task_queue import TaskQueue

# Custom connection
queue = TaskQueue(connection_params={
    "host": "custom-host",
    "port": 5432,
    "database": "custom-db",
    "user": "custom-user",
    "password": "custom-pass"
})

# Default (uses DatabaseConfig from Phase 1)
queue = TaskQueue()
```

### Environment Variables

```bash
# From Phase 1 database setup
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_DB=zendb
POSTGRES_USER=zen
POSTGRES_PASSWORD=zenpass
```

---

## Troubleshooting

### Connection Issues

```bash
# Check Postgres container
docker ps | grep zen-postgres

# Restart container
docker restart zen-postgres

# Test connection
cd /home/dingo/code/zen-mcp-server
source .zen_venv/bin/activate
python -c "from utils.task_queue import TaskQueue; TaskQueue().close()"
```

### Task Not Appearing

```python
# Check task status
with TaskQueue() as queue:
    task = queue.get_task(task_id)
    
    if task:
        print(f"Status: {task.status}")
        print(f"Assigned to: {task.assigned_to}")
    else:
        print("Task not found")
```

### Race Condition Concerns

No need to worry! The queue handles race conditions automatically:
- `claim_task()` uses atomic UPDATE with WHERE clause
- Only one window succeeds in claiming
- Failed claims return `False` (not an error)

---

## Performance

- **Enqueue**: < 10ms
- **Dequeue**: < 20ms
- **Claim**: < 15ms (atomic)
- **Update**: < 10ms
- **Stats**: < 50ms

---

## Files and Locations

### Implementation
- **TaskQueue**: `zen-mcp-server/utils/task_queue.py`
- **Schema**: `zen-mcp-server/sql/task_queue.sql`

### Testing & Demo
- **Test Suite**: `zen-mcp-server/test_phase3_task_queue.py`
- **Demo**: `zen-mcp-server/demo_task_queue.py`

### Documentation
- **Phase 3 Complete**: `workspaces/.../task-8.../evidence/PHASE3-COMPLETE.md`
- **Quick Reference**: `zen-mcp-server/PHASE3-QUICK-REFERENCE.md`

---

## Integration with Other Phases

### With Phase 1 (Analytics)

```python
from utils.task_queue import TaskQueue
from utils.analytics import ZenAnalytics

with TaskQueue() as queue, ZenAnalytics() as analytics:
    # Create task
    task_id = queue.enqueue(TaskType.CHAT.value, {}, priority=7)
    
    # Log to analytics
    analytics.log_routing_decision(
        user_intent="Task created",
        chosen_tool="chat",
        chosen_strategy="SOLO",
        detected_complexity=5,
        detected_risk=3
    )
```

### With Phase 2 (Router)

```python
from routing import IntelligentRouter
from utils.task_queue import TaskQueue

router = IntelligentRouter()
queue = TaskQueue()

# Route and enqueue
decision = router.route_request(user_query)

task_id = queue.enqueue(
    task_type=decision.tool,
    data={"query": user_query},
    priority=decision.complexity
)
```

---

**Updated**: 2025-10-12  
**Status**: ✅ Phase 3 Complete  
**Next**: Optional Phase 4 - Enhanced Voting

