"""
Integration Tests - Complete Thinking Termination Workflow

Tests the full flow from agent registration to thinking termination.
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from tools.agent_registry import (
    AgentInstance,
    AgentStatus,
    AgentType,
    get_registry,
)
from tools.evidence_monitor import get_monitor
from tools.invalidation_checker import get_checker


class TestThinkingTerminationWorkflow:
    """Test complete thinking termination workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, tmp_path):
        """
        Test the complete workflow:
        1. Agent starts thinking
        2. Subscribes to evidence
        3. User adds invalidating evidence
        4. Agent checks and terminates
        """
        # Initialize systems
        registry = get_registry()
        monitor = get_monitor()
        checker = get_checker()
        
        # Create evidence file
        evidence_file = tmp_path / "database-performance.md"
        evidence_file.write_text("""# Database Performance Evidence

---

## Evidence Entry #1: 2025-10-06 14:30:00 MDT

### Prompt Input
```
Check ThinPrint configuration
```

### Raw Data Output
```
ThinPrint settings appear correct
```

---

## Evidence Entry #2: 2025-10-06 14:35:00 MDT

### Prompt Input
```
Apply ThinPrint fix
```

### Raw Data Output
```
ThinPrint fix applied
```

---

## Evidence Entry #3: 2025-10-06 14:40:00 MDT

### Prompt Input
```
Test ThinPrint solution
```

### Raw Data Output
```
Testing in progress...
```
""")
        
        # STEP 1: Register agent (starts thinking about ThinPrint)
        now = datetime.utcnow().isoformat() + "Z"
        agent = AgentInstance(
            agent_id="thinprint-analyzer-001",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file=str(evidence_file),
            evidence_entry_range=(1, 3),  # Has seen entries 1-3
            started_at=now,
            last_context_check=now,
            metadata={"hypothesis": "ThinPrint configuration needs adjustment"}
        )
        
        await registry.register(agent)
        
        # STEP 2: Subscribe to evidence updates
        await monitor.subscribe(agent.agent_id, "002")
        
        # STEP 3: Capture initial evidence state
        initial_state = await monitor.capture_state("002", str(evidence_file))
        assert initial_state.entry_count == 3
        
        # STEP 4: User adds invalidating evidence (ThinPrint failed)
        evidence_file.write_text(evidence_file.read_text() + """
---

## Evidence Entry #4: 2025-10-06 14:45:00 MDT

<!-- source: user -->

### Prompt Input
```
Check ThinPrint results after 3 days
```

### Raw Data Output
```
No improvement after 3 days. ThinPrint solution failed.
Need to try different approach.
```
""")
        
        # STEP 5: Agent checks for updates
        updates = await monitor.check_for_updates("002", agent.evidence_entry_range)
        
        assert len(updates) == 1
        assert updates[0].new_entry_number == 4
        
        # STEP 6: Check if update invalidates thinking
        decision = checker.check_entry(agent, updates[0].entry)
        
        assert decision.should_terminate is True
        assert "failed" in decision.reason.lower()
        
        # STEP 7: Terminate agent
        await registry.terminate(agent.agent_id, decision.reason)
        
        # STEP 8: Verify agent terminated
        terminated_agent = await registry.get(agent.agent_id)
        assert terminated_agent.status == AgentStatus.TERMINATED
        assert terminated_agent.termination_reason is not None
    
    @pytest.mark.asyncio
    async def test_multi_agent_coordination(self, tmp_path):
        """
        Test multiple agents coordinating:
        1. Agent A starts thinking (ThinPrint)
        2. Agent B forks (Database investigation)
        3. Agent B finds solution
        4. Agent A checks and terminates
        """
        registry = get_registry()
        monitor = get_monitor()
        checker = get_checker()
        
        # Create evidence file
        evidence_file = tmp_path / "investigation.md"
        evidence_file.write_text("""# Investigation Evidence

## Evidence Entry #1: 2025-10-06 14:30:00 MDT
### Prompt Input
```
Initial investigation
```
### Raw Data Output
```
Starting analysis
```
""")
        
        now = datetime.utcnow().isoformat() + "Z"
        
        # Agent A: Thinking about ThinPrint
        agent_a = AgentInstance(
            agent_id="agent-a-thinprint",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file=str(evidence_file),
            evidence_entry_range=(1, 1),
            started_at=now,
            last_context_check=now,
            metadata={"hypothesis": "ThinPrint issue"}
        )
        
        await registry.register(agent_a)
        await monitor.subscribe(agent_a.agent_id, "002")
        
        # Agent B: Forked to investigate database
        agent_b = AgentInstance(
            agent_id="agent-b-database",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file=str(evidence_file),
            evidence_entry_range=(1, 1),
            started_at=now,
            last_context_check=now,
            parent_agent_id=agent_a.agent_id,
            metadata={"hypothesis": "Database fragmentation"}
        )
        
        await registry.register(agent_b)
        await monitor.subscribe(agent_b.agent_id, "002")
        
        # Agent B finds solution and adds evidence
        evidence_file.write_text(evidence_file.read_text() + """
## Evidence Entry #2: 2025-10-06 14:40:00 MDT

<!-- source: agent -->

### Prompt Input
```
Database analysis complete
```

### Raw Data Output
```
Solution found! Database fragmentation was the issue.
Index rebuild achieved 86% performance improvement.
```
""")
        
        # Update monitor state
        await monitor.capture_state("002", str(evidence_file))
        
        # Agent A checks for updates
        updates = await monitor.check_for_updates("002", agent_a.evidence_entry_range)
        
        assert len(updates) == 1
        
        # Agent A checks if invalidated
        decision = checker.check_entry(agent_a, updates[0].entry)
        
        # Agent A should terminate (Agent B found solution)
        assert decision.should_terminate is True
        
        # Terminate Agent A
        await registry.terminate(agent_a.agent_id, decision.reason)
        
        # Verify
        final_agent_a = await registry.get(agent_a.agent_id)
        assert final_agent_a.status == AgentStatus.TERMINATED
        
        # Agent B can continue
        final_agent_b = await registry.get(agent_b.agent_id)
        assert final_agent_b.status == AgentStatus.THINKING
    
    @pytest.mark.asyncio
    async def test_validate_before_respond_prevents_hallucination(self, tmp_path):
        """
        Test the critical validate_before_respond check:
        1. Agent thinks solution is X
        2. User updates: X failed, try Y
        3. Agent calls validate_before_respond
        4. Agent terminated instead of responding with outdated X
        """
        registry = get_registry()
        monitor = get_monitor()
        checker = get_checker()
        
        # Create evidence file
        evidence_file = tmp_path / "solution-testing.md"
        evidence_file.write_text("""# Solution Testing

## Evidence Entry #1: 2025-10-06 14:30:00 MDT
### Prompt Input
```
Try solution X
```
### Raw Data Output
```
Testing...
```
""")
        
        now = datetime.utcnow().isoformat() + "Z"
        
        # Agent starts thinking "Solution X will work"
        agent = AgentInstance(
            agent_id="solution-thinker",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file=str(evidence_file),
            evidence_entry_range=(1, 1),
            started_at=now,
            last_context_check=now,
            metadata={"solution": "X"}
        )
        
        await registry.register(agent)
        await monitor.capture_state("002", str(evidence_file))
        
        # User adds: "Solution X failed"
        evidence_file.write_text(evidence_file.read_text() + """
## Evidence Entry #2: 2025-10-06 14:45:00 MDT
### Prompt Input
```
Solution X results
```
### Raw Data Output
```
Solution X failed. No improvement. Try solution Y instead.
```
""")
        
        # Update state
        await monitor.capture_state("002", str(evidence_file))
        
        # Agent is about to respond "Solution X will work!"
        # But FIRST calls validate_before_respond
        
        updates = await monitor.check_for_updates("002", agent.evidence_entry_range)
        assert len(updates) == 1
        
        decision = checker.check_entry(agent, updates[0].entry)
        
        # CRITICAL: Agent should be invalidated
        assert decision.should_terminate is True
        
        # Terminate before responding
        await registry.terminate(agent.agent_id, decision.reason)
        
        # Verify agent can't respond
        final_agent = await registry.get(agent.agent_id)
        assert final_agent.status == AgentStatus.TERMINATED
        
        # HALLUCINATION PREVENTED! 🎉
        # Agent did NOT respond with outdated "Solution X will work"


class TestTicket002RealScenario:
    """Test actual ticket-002 scenario"""
    
    @pytest.mark.asyncio
    async def test_ticket_002_complete_journey(self, tmp_path):
        """
        Simulate ticket-002 complete investigation:
        1. Start with ThinPrint hypothesis
        2. ThinPrint solution fails
        3. Pivot to database investigation
        4. Database solution succeeds
        """
        registry = get_registry()
        monitor = get_monitor()
        checker = get_checker()
        
        # Create evidence file
        evidence_file = tmp_path / "readqueen-investigation.md"
        evidence_file.write_text("""# ReadQueen Investigation

## Evidence Entry #1: 2025-01-27 10:00:00 MDT
### Prompt Input
```
Check printer enumeration
```
### Raw Data Output
```
513 printers enumerated
```
""")
        
        now = datetime.utcnow().isoformat() + "Z"
        
        # Agent 1: ThinPrint analyzer
        agent_thinprint = AgentInstance(
            agent_id="thinprint-analyzer",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file=str(evidence_file),
            evidence_entry_range=(1, 1),
            started_at=now,
            last_context_check=now,
            metadata={"hypothesis": "Too many printers causing delays"}
        )
        
        await registry.register(agent_thinprint)
        await monitor.subscribe(agent_thinprint.agent_id, "002")
        
        # Add ThinPrint solution attempt
        evidence_file.write_text(evidence_file.read_text() + """
## Evidence Entry #2: 2025-01-27 10:30:00 MDT
### Prompt Input
```
Apply ThinPrint registry fix
```
### Raw Data Output
```
OnlyDefaultPrinter=1 applied
```

## Evidence Entry #3: 2025-01-27 10:35:00 MDT
### Prompt Input
```
Test after 3 days
```
### Raw Data Output
```
After 3 days: No improvement. Print delays persist.
ThinPrint solution failed.
```
""")
        
        await monitor.capture_state("002", str(evidence_file))
        
        # Agent checks - should see ThinPrint failed
        updates = await monitor.check_for_updates("002", (1, 1))
        assert len(updates) == 2
        
        # Check last update (ThinPrint failed)
        decision = checker.check_entry(agent_thinprint, updates[-1].entry)
        assert decision.should_terminate is True
        
        # Terminate ThinPrint agent
        await registry.terminate(agent_thinprint.agent_id, decision.reason)
        
        # Fork database agent
        agent_database = AgentInstance(
            agent_id="database-analyzer",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file=str(evidence_file),
            evidence_entry_range=(1, 3),
            started_at=now,
            last_context_check=now,
            parent_agent_id=agent_thinprint.agent_id,
            metadata={"hypothesis": "Database fragmentation"}
        )
        
        await registry.register(agent_database)
        await monitor.subscribe(agent_database.agent_id, "002")
        
        # Add database investigation
        evidence_file.write_text(evidence_file.read_text() + """
## Evidence Entry #4: 2025-10-06 14:30:00 MDT
### Prompt Input
```
Check database fragmentation
```
### Raw Data Output
```
Product.IX_description: 100% fragmentation
```

## Evidence Entry #5: 2025-10-06 14:35:00 MDT
### Prompt Input
```
Rebuild index
```
### Raw Data Output
```
Index rebuild completed
```

## Evidence Entry #6: 2025-10-06 14:40:00 MDT

<!-- source: agent -->

### Prompt Input
```
Validate solution
```

### Raw Data Output
```
Fragmentation: 21% (down from 100%)
Print time: 2.27s (down from 16s)
86% performance improvement confirmed!
Solution found and validated.
```
""")
        
        await monitor.capture_state("002", str(evidence_file))
        
        # Database agent validates before responding
        updates = await monitor.check_for_updates("002", (1, 3))
        assert len(updates) == 3
        
        # Check if any invalidate (solution found by another agent)
        final_decision = checker.check_multiple_entries(agent_database, [u.entry for u in updates])
        
        # In this case, it's the same agent, so should be safe to respond
        # (In real implementation, would check agent_id in HTML comments)
        
        # Verify ticket status
        ticket_status = await registry.get_ticket_status("002")
        assert ticket_status["total_agents"] == 2
        
        # Verify ThinPrint agent terminated
        thinprint_agent = await registry.get("thinprint-analyzer")
        assert thinprint_agent.status == AgentStatus.TERMINATED
        
        # Verify database agent still active
        database_agent = await registry.get("database-analyzer")
        assert database_agent.status == AgentStatus.THINKING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

