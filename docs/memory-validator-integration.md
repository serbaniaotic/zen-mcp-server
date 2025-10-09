# Memory Validator Integration Guide

**Tool**: `mcp__zen__memory_validator`
**Purpose**: Prevent persistent memory contamination
**Status**: ✅ Production Ready

---

## Quick Start

### Check Memory Health
```python
result = await mcp__zen__memory_validator(
    action="health_check",
    model="gemini-2.5-flash"
)

print(f"Health Score: {result['health_score']}/100")
print(f"Conflicts: {result['conflicts_detected']}")
```

### Validate Before Use
```python
result = await mcp__zen__memory_validator(
    action="retrieve",
    identifier="TICKET-030",
    validate_filesystem=True,
    model="gemini-2.5-flash"
)

if result.get('is_stale'):
    print("⚠️ WARNING: Memory is stale - file has been modified")

if result.get('conflict'):
    print(f"🔴 CONFLICT: {result['conflict']['competing_count']} competing memories")
    # Use filesystem as source of truth
```

---

## Integration Points

### 1. Ticket Commands (`/ticket-work`)

Add validation before reading ticket content:

```python
def ticket_work_command(ticket_id: str):
    # Validate memory first
    memory_result = await mcp__zen__memory_validator(
        action="retrieve",
        identifier=ticket_id,
        validate_filesystem=True,
        model="gemini-2.5-flash"
    )

    # Check for issues
    if memory_result.get('conflict'):
        conflict = memory_result['conflict']
        print(f"⚠️ MEMORY CONFLICT DETECTED FOR {ticket_id}")
        print(f"   Severity: {conflict['severity']}")
        print(f"   Competing concepts:")
        for concept in conflict['concepts']:
            print(f"   - {concept}")
        print(f"\n   Recommended: {conflict['recommended_action']}")
        print(f"   Reading from filesystem (source of truth)...")

    if memory_result.get('is_stale'):
        print(f"⚠️ STALE MEMORY FOR {ticket_id}")
        print(f"   Memory: {memory_result['timestamp']}")
        print(f"   File:   {memory_result['file_mtime']}")
        print(f"   Reading from filesystem (source of truth)...")

    # Read from filesystem (source of truth)
    ticket_content = read_ticket_from_filesystem(ticket_id)

    # Update memory from filesystem
    await mcp__zen__memory_validator(
        action="store",
        identifier=ticket_id,
        concept_summary=extract_summary(ticket_content),
        content=ticket_content,
        file_path=get_ticket_path(ticket_id),
        session_id=get_current_session_id(),
        model="gemini-2.5-flash"
    )

    return ticket_content
```

### 2. File Write Hooks

Update memory when files are written:

```python
def on_ticket_file_write(ticket_id: str, content: str, file_path: str):
    # Write file
    write_file(file_path, content)

    # Update memory
    await mcp__zen__memory_validator(
        action="store",
        identifier=ticket_id,
        concept_summary=extract_ticket_summary(content),
        content=content,
        file_path=file_path,
        session_id=get_current_session_id(),
        model="gemini-2.5-flash"
    )
```

### 3. Session Start Hooks

Check for conflicts on session start:

```python
async def on_session_start():
    # Run health check
    health = await mcp__zen__memory_validator(
        action="health_check",
        model="gemini-2.5-flash"
    )

    if health['conflicts_detected'] > 0:
        print(f"⚠️ MEMORY HEALTH WARNING")
        print(f"   Health Score: {health['health_score']}/100")
        print(f"   Conflicts: {health['conflicts_detected']}")
        print(f"\n   Detected Conflicts:")
        for conflict in health['conflicts']:
            print(f"   - {conflict['identifier']}: {conflict['unique_concepts']} competing concepts")
        print(f"\n   Run /memory-health-check for details")

    if health['stale_memories'] > 0:
        print(f"⚠️ {health['stale_memories']} stale memories detected")
        print(f"   Consider running /memory-cleanup")
```

### 4. Context Limit Warnings

Validate before context window limit:

```python
def on_context_warning(remaining_tokens: int):
    if remaining_tokens < 5000:
        print("⚠️ Context window almost full - validating active memories...")

        # Get all active work
        active_tickets = get_active_tickets()

        for ticket_id in active_tickets:
            result = await mcp__zen__memory_validator(
                action="validate",
                identifier=ticket_id,
                model="gemini-2.5-flash"
            )

            if not result.get('is_valid'):
                print(f"⚠️ Memory validation failed for {ticket_id}")
                print(f"   Recommendation: {result.get('recommendation')}")
```

---

## Best Practices

### 1. Always Validate on Retrieval
```python
# ❌ Bad: Trust memory blindly
memory = get_memory_from_cache(ticket_id)

# ✅ Good: Validate against filesystem
result = await mcp__zen__memory_validator(
    action="retrieve",
    identifier=ticket_id,
    validate_filesystem=True,
    model="gemini-2.5-flash"
)
```

### 2. Update Memory on Write
```python
# ❌ Bad: Write file but don't update memory
write_file(path, content)

# ✅ Good: Write file and update memory
write_file(path, content)
await mcp__zen__memory_validator(
    action="store",
    identifier=ticket_id,
    concept_summary=summary,
    content=content,
    file_path=path,
    model="gemini-2.5-flash"
)
```

### 3. Health Checks
```python
# Run weekly or on session start
async def weekly_health_check():
    health = await mcp__zen__memory_validator(
        action="health_check",
        model="gemini-2.5-flash"
    )

    if health['health_score'] < 70:
        notify_admin(f"Memory health degraded: {health['health_score']}/100")
```

### 4. Conflict Resolution
```python
async def resolve_ticket_conflict(ticket_id: str):
    result = await mcp__zen__memory_validator(
        action="resolve_conflict",
        identifier=ticket_id,
        model="gemini-2.5-flash"
    )

    print(f"Competing memories: {result['competing_memories']}")
    print(f"Recommendation: {result['recommendation']}")

    if result['filesystem_state']['exists']:
        # Use filesystem as source of truth
        return read_from_filesystem(ticket_id)
    else:
        # Use most recent memory
        return result['concepts'][0]
```

---

## Error Handling

```python
try:
    result = await mcp__zen__memory_validator(
        action="retrieve",
        identifier=ticket_id,
        validate_filesystem=True,
        model="gemini-2.5-flash"
    )

    if not result.get('success'):
        # Handle error
        print(f"Memory validation failed: {result.get('error')}")
        # Fallback to filesystem read
        return read_from_filesystem(ticket_id)

except Exception as e:
    # Critical error - always use filesystem
    print(f"Memory validator error: {e}")
    print("Falling back to filesystem (source of truth)")
    return read_from_filesystem(ticket_id)
```

---

## Performance Optimization

### 1. Batch Validation
```python
# Validate multiple tickets in one session
async def validate_active_work(ticket_ids: List[str]):
    results = {}

    for ticket_id in ticket_ids:
        result = await mcp__zen__memory_validator(
            action="retrieve",
            identifier=ticket_id,
            validate_filesystem=True,
            model="gemini-2.5-flash"
        )
        results[ticket_id] = result

    return results
```

### 2. Selective Validation
```python
# Only validate if memory is old
async def smart_validation(ticket_id: str, max_age_hours: int = 24):
    result = await mcp__zen__memory_validator(
        action="retrieve",
        identifier=ticket_id,
        validate_filesystem=False,  # Fast retrieval
        model="gemini-2.5-flash"
    )

    if result.get('found'):
        memory_age = calculate_age_hours(result['timestamp'])

        if memory_age > max_age_hours:
            # Re-validate with filesystem check
            result = await mcp__zen__memory_validator(
                action="retrieve",
                identifier=ticket_id,
                validate_filesystem=True,
                model="gemini-2.5-flash"
            )

    return result
```

---

## Monitoring and Alerts

### Daily Health Report
```python
async def daily_health_report():
    health = await mcp__zen__memory_validator(
        action="health_check",
        model="gemini-2.5-flash"
    )

    report = f"""
Memory Health Report - {datetime.now().strftime('%Y-%m-%d')}
{'='*50}
Health Score: {health['health_score']}/100 {health['status']}
Total Memories: {health['total_memories']}
Stale Memories: {health['stale_memories']}
Conflicts: {health['conflicts_detected']}

Recommendations:
{chr(10).join('- ' + r for r in health['recommendations'])}
"""

    send_to_slack(report)
    return report
```

### Critical Alerts
```python
async def check_critical_memory_issues():
    health = await mcp__zen__memory_validator(
        action="health_check",
        model="gemini-2.5-flash"
    )

    if health['health_score'] < 50:
        send_pagerduty_alert(
            title="Critical Memory Health Issue",
            description=f"Health score: {health['health_score']}/100",
            severity="critical"
        )

    if health['conflicts_detected'] > 0:
        for conflict in health['conflicts']:
            if conflict['unique_concepts'] >= 3:
                send_pagerduty_alert(
                    title=f"Triple Collision: {conflict['identifier']}",
                    description=f"{conflict['unique_concepts']} competing memories",
                    severity="high"
                )
```

---

## Testing

### Unit Test Example
```python
import pytest
from content_memory_validator import ContentMemoryValidator

@pytest.fixture
def validator():
    return ContentMemoryValidator(":memory:")  # In-memory DB

def test_triple_collision_detection(validator):
    # Store three competing memories
    validator.store_memory("TICKET-030", "Concept A", "content A")
    validator.store_memory("TICKET-030", "Concept B", "content B")
    validator.store_memory("TICKET-030", "Concept C", "content C")

    # Retrieve and check conflict
    memory, conflict = validator.retrieve_memory("TICKET-030")

    assert conflict is not None
    assert conflict.severity == "critical"
    assert len(conflict.competing_memories) == 3

def test_staleness_detection(validator, tmp_path):
    # Create file
    file_path = tmp_path / "test.txt"
    file_path.write_text("original content")

    # Store memory
    validator.store_memory(
        "TEST-001",
        "Original",
        "original content",
        file_path=str(file_path)
    )

    # Modify file (make it newer)
    time.sleep(0.1)
    file_path.write_text("modified content")

    # Retrieve should detect staleness
    memory, conflict = validator.retrieve_memory("TEST-001", validate_filesystem=True)

    assert memory.is_stale is True
```

---

## Migration Guide

### From Old System
```python
# Old: No validation
def get_ticket(ticket_id):
    return memory_cache[ticket_id]

# New: With validation
async def get_ticket(ticket_id):
    result = await mcp__zen__memory_validator(
        action="retrieve",
        identifier=ticket_id,
        validate_filesystem=True,
        model="gemini-2.5-flash"
    )

    if result.get('conflict') or result.get('is_stale'):
        # Use filesystem as source of truth
        return read_from_filesystem(ticket_id)

    return result['concept']
```

---

## Troubleshooting

### Issue: High stale memory count
**Solution**: Run batch update from filesystem
```python
async def refresh_all_memories():
    health = await mcp__zen__memory_validator(
        action="health_check",
        model="gemini-2.5-flash"
    )

    for conflict in health['conflicts']:
        ticket_id = conflict['identifier']

        # Read current state from filesystem
        content = read_from_filesystem(ticket_id)

        # Update memory
        await mcp__zen__memory_validator(
            action="store",
            identifier=ticket_id,
            concept_summary=extract_summary(content),
            content=content,
            file_path=get_path(ticket_id),
            model="gemini-2.5-flash"
        )
```

### Issue: Conflicts not resolving
**Solution**: Use manual conflict resolution
```python
async def manual_resolve(ticket_id: str, use_filesystem: bool = True):
    if use_filesystem:
        # Read from filesystem (source of truth)
        content = read_from_filesystem(ticket_id)
        summary = extract_summary(content)
    else:
        # Ask user to choose
        result = await mcp__zen__memory_validator(
            action="resolve_conflict",
            identifier=ticket_id,
            model="gemini-2.5-flash"
        )
        # Present options to user
        summary = user_choose_concept(result['concepts'])

    # Update memory with chosen concept
    await mcp__zen__memory_validator(
        action="store",
        identifier=ticket_id,
        concept_summary=summary,
        content=content,
        file_path=get_path(ticket_id),
        force_update=True,
        model="gemini-2.5-flash"
    )
```

---

## Support

For issues or questions:

1. Check health: `/memory-health-check`
2. Review logs: `~/.zen-mcp/content_memory.db`
3. Run validation: `/memory-validate <identifier>`
4. Resolve conflicts: `/memory-resolve-conflict <identifier>`

**Remember**: **Filesystem is ALWAYS source of truth!**
