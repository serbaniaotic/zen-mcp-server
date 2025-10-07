"""
Tests for Evidence Monitor system
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from tools.evidence_monitor import (
    EvidenceEntry,
    EvidenceMonitor,
    EvidenceState,
    EvidenceUpdate,
    get_monitor,
)


class TestEvidenceMonitor:
    """Test Evidence Monitor functionality"""
    
    @pytest.fixture
    async def monitor(self):
        """Create a fresh monitor for each test"""
        return EvidenceMonitor()
    
    @pytest.fixture
    def sample_evidence_file(self, tmp_path):
        """Create a sample evidence file"""
        evidence_file = tmp_path / "database-performance.md"
        content = """# Database Performance Evidence

---

## Evidence Entry #1: 2025-10-06 14:30:00 MDT

<!-- source: user -->

### Prompt Input
```
Check Product table fragmentation
```

### Raw Data Output
```sql
Product  IX_description  100
```

---

## Evidence Entry #2: 2025-10-06 14:35:00 MDT

<!-- source: user -->

### Prompt Input
```
Rebuild index
```

### Raw Data Output
```
Rebuild completed
```

---

## Evidence Entry #3: 2025-10-06 14:40:00 MDT

<!-- source: agent -->

### Prompt Input
```
Solution found
```

### Raw Data Output
```
Fragmentation reduced to 21%
```
"""
        evidence_file.write_text(content)
        return str(evidence_file)
    
    @pytest.mark.asyncio
    async def test_capture_state(self, monitor, sample_evidence_file):
        """Test capturing evidence state"""
        state = await monitor.capture_state("002", sample_evidence_file)
        
        assert state.ticket_id == "002"
        assert state.entry_count == 3
        assert state.context_type == "database-performance"
        assert len(state.file_hash) == 32  # MD5 hash
    
    @pytest.mark.asyncio
    async def test_parse_entries(self, monitor, sample_evidence_file):
        """Test parsing evidence entries"""
        content = Path(sample_evidence_file).read_text()
        entries = monitor._parse_evidence_entries(content)
        
        assert len(entries) == 3
        assert entries[0].entry_number == 1
        assert entries[0].source == "user"
        assert "fragmentation" in entries[0].prompt_input.lower()
        
        assert entries[2].entry_number == 3
        assert entries[2].source == "agent"
        assert "solution" in entries[2].prompt_input.lower()
    
    @pytest.mark.asyncio
    async def test_check_for_updates_no_new(self, monitor, sample_evidence_file):
        """Test checking for updates when there are none"""
        # Capture initial state
        await monitor.capture_state("002", sample_evidence_file)
        
        # Check for updates (agent has seen all 3 entries)
        updates = await monitor.check_for_updates("002", (1, 3))
        
        assert len(updates) == 0
    
    @pytest.mark.asyncio
    async def test_check_for_updates_new_entries(self, monitor, sample_evidence_file):
        """Test checking for updates when there are new entries"""
        # Capture initial state
        await monitor.capture_state("002", sample_evidence_file)
        
        # Check for updates (agent has only seen entries 1-2)
        updates = await monitor.check_for_updates("002", (1, 2))
        
        assert len(updates) == 1
        assert updates[0].new_entry_number == 3
        assert updates[0].source == "agent"
    
    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, monitor):
        """Test agent subscription"""
        # Subscribe
        success = await monitor.subscribe("agent-1", "002")
        assert success
        
        assert "002" in monitor.subscribers
        assert "agent-1" in monitor.subscribers["002"]
        
        # Unsubscribe
        success = await monitor.unsubscribe("agent-1", "002")
        assert success
        assert "agent-1" not in monitor.subscribers.get("002", set())
    
    @pytest.mark.asyncio
    async def test_notification_callback(self, monitor, sample_evidence_file):
        """Test notification callback system"""
        notifications = []
        
        async def callback(update, agent_ids):
            notifications.append((update, agent_ids))
        
        # Register callback
        monitor.register_notification_callback(callback)
        
        # Subscribe agents
        await monitor.subscribe("agent-1", "002")
        await monitor.subscribe("agent-2", "002")
        
        # Create and notify update
        await monitor.capture_state("002", sample_evidence_file)
        updates = await monitor.check_for_updates("002", (1, 2))
        
        if updates:
            await monitor.notify_subscribers(updates[0])
        
        # Check callback was called
        assert len(notifications) == 1
        update, agent_ids = notifications[0]
        assert update.new_entry_number == 3
        assert len(agent_ids) == 2
    
    @pytest.mark.asyncio
    async def test_invalidation_detection(self, monitor):
        """Test detecting entries that may invalidate thinking"""
        # Entry with "failed" keyword
        entry1 = EvidenceEntry(
            entry_number=4,
            timestamp="2025-10-06 15:00:00 MDT",
            prompt_input="Previous approach failed",
            raw_output="Need to try different solution",
            context_type="test",
            source="user"
        )
        
        assert monitor._check_invalidation(entry1) is True
        
        # Entry with "solution found"
        entry2 = EvidenceEntry(
            entry_number=5,
            timestamp="2025-10-06 15:05:00 MDT",
            prompt_input="Testing solution",
            raw_output="Solution found! Problem solved.",
            context_type="test",
            source="agent"
        )
        
        assert monitor._check_invalidation(entry2) is True
        
        # Normal entry
        entry3 = EvidenceEntry(
            entry_number=6,
            timestamp="2025-10-06 15:10:00 MDT",
            prompt_input="Check status",
            raw_output="All good",
            context_type="test",
            source="user"
        )
        
        assert monitor._check_invalidation(entry3) is False
    
    @pytest.mark.asyncio
    async def test_monitoring_status(self, monitor):
        """Test getting monitoring status"""
        # Subscribe some agents
        await monitor.subscribe("agent-1", "002")
        await monitor.subscribe("agent-2", "002")
        await monitor.subscribe("agent-3", "003")
        
        status = await monitor.get_monitoring_status()
        
        assert status["total_subscribers"] == 3
        assert status["subscribers_by_ticket"]["002"] == 2
        assert status["subscribers_by_ticket"]["003"] == 1
    
    @pytest.mark.asyncio
    async def test_context_extraction(self, monitor):
        """Test extracting context type from filename"""
        assert monitor._extract_context_type("evidence/database-performance.md") == "database-performance"
        assert monitor._extract_context_type("evidence/system-diagnostics.md") == "system-diagnostics"
        assert monitor._extract_context_type("/full/path/to/network-analysis.md") == "network-analysis"
    
    @pytest.mark.asyncio
    async def test_multiple_tickets(self, monitor, tmp_path):
        """Test monitoring multiple tickets"""
        # Create evidence files for multiple tickets
        file1 = tmp_path / "ticket-002-evidence.md"
        file1.write_text("""
## Evidence Entry #1: 2025-10-06 14:30:00 MDT
### Prompt Input
```
Test 1
```
### Raw Data Output
```
Output 1
```
""")
        
        file2 = tmp_path / "ticket-003-evidence.md"
        file2.write_text("""
## Evidence Entry #1: 2025-10-06 14:35:00 MDT
### Prompt Input
```
Test 2
```
### Raw Data Output
```
Output 2
```
""")
        
        # Capture states for both
        state1 = await monitor.capture_state("002", str(file1))
        state2 = await monitor.capture_state("003", str(file2))
        
        assert state1.ticket_id == "002"
        assert state2.ticket_id == "003"
        assert len(monitor.evidence_states) == 2


class TestGlobalMonitor:
    """Test global monitor singleton"""
    
    def test_get_monitor(self):
        """Test getting global monitor"""
        monitor1 = get_monitor()
        monitor2 = get_monitor()
        
        # Should return same instance
        assert monitor1 is monitor2


class TestEvidenceUpdate:
    """Test evidence update data structure"""
    
    def test_evidence_update_creation(self):
        """Test creating evidence update"""
        entry = EvidenceEntry(
            entry_number=5,
            timestamp="2025-10-06 15:00:00 MDT",
            prompt_input="Test",
            raw_output="Output",
            context_type="test",
            source="user"
        )
        
        update = EvidenceUpdate(
            ticket_id="002",
            evidence_file="evidence/test.md",
            new_entry_number=5,
            entry=entry,
            source="user",
            context_changed=False,
            invalidates_thinking=True,
            reason="Test reason"
        )
        
        assert update.ticket_id == "002"
        assert update.new_entry_number == 5
        assert update.invalidates_thinking is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

