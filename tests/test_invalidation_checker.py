"""
Tests for Invalidation Checker system
"""

import pytest
from datetime import datetime

from tools.agent_registry import AgentInstance, AgentStatus, AgentType
from tools.evidence_monitor import EvidenceEntry
from tools.invalidation_checker import (
    InvalidationChecker,
    InvalidationRule,
    InvalidationSeverity,
    InvalidationType,
    get_checker,
)


class TestInvalidationChecker:
    """Test Invalidation Checker functionality"""
    
    @pytest.fixture
    def checker(self):
        """Create a fresh checker for each test"""
        return InvalidationChecker()
    
    @pytest.fixture
    def sample_agent(self):
        """Create a sample thinking agent"""
        now = datetime.utcnow().isoformat() + "Z"
        return AgentInstance(
            agent_id="test-agent-001",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file="evidence/database-performance.md",
            evidence_entry_range=(1, 3),
            started_at=now,
            last_context_check=now,
            metadata={"hypothesis": "ThinPrint configuration is the issue"}
        )
    
    def test_approach_failed_detection(self, checker, sample_agent):
        """Test detecting when user reports approach failed"""
        entry = EvidenceEntry(
            entry_number=4,
            timestamp="2025-10-06 15:00:00 MDT",
            prompt_input="Tried ThinPrint fix",
            raw_output="After 3 days, no improvement. Solution failed.",
            context_type="system",
            source="user"
        )
        
        decision = checker.check_entry(sample_agent, entry)
        
        assert decision.should_terminate is True
        assert decision.invalidation_type == InvalidationType.APPROACH_FAILED
        assert "failed" in decision.reason.lower()
        assert decision.conflicting_entry == 4
    
    def test_direction_change_detection(self, checker, sample_agent):
        """Test detecting user direction changes"""
        entry = EvidenceEntry(
            entry_number=4,
            timestamp="2025-10-06 15:00:00 MDT",
            prompt_input="Let's try a different approach - check database instead",
            raw_output="Switching focus to database performance",
            context_type="database",
            source="user"
        )
        
        decision = checker.check_entry(sample_agent, entry)
        
        assert decision.should_terminate is True
        assert decision.invalidation_type == InvalidationType.USER_DIRECTION_CHANGE
        assert "direction" in decision.reason.lower()
    
    def test_solution_found_detection(self, checker, sample_agent):
        """Test detecting when another agent found solution"""
        entry = EvidenceEntry(
            entry_number=5,
            timestamp="2025-10-06 15:05:00 MDT",
            prompt_input="Database optimization results",
            raw_output="Solution found! 86% performance improvement confirmed.",
            context_type="database",
            source="agent"
        )
        
        decision = checker.check_entry(sample_agent, entry)
        
        assert decision.should_terminate is True
        assert decision.invalidation_type == InvalidationType.AGENT_SOLUTION_FOUND
        assert "solution" in decision.reason.lower()
    
    def test_context_shift_detection(self, checker):
        """Test detecting context shifts"""
        # Agent working on database context
        agent = AgentInstance(
            agent_id="test-agent-002",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file="evidence/database-performance.md",
            evidence_entry_range=(1, 3),
            started_at=datetime.utcnow().isoformat() + "Z",
            last_context_check=datetime.utcnow().isoformat() + "Z",
            metadata={"context_type": "database-performance"}
        )
        
        # New entry in network context
        entry = EvidenceEntry(
            entry_number=4,
            timestamp="2025-10-06 15:00:00 MDT",
            prompt_input="Network analysis",
            raw_output="Checking network latency",
            context_type="network-analysis",
            source="user"
        )
        
        decision = checker.check_entry(agent, entry)
        
        assert decision.should_terminate is True
        assert decision.invalidation_type == InvalidationType.CONTEXT_SHIFT
    
    def test_no_invalidation(self, checker, sample_agent):
        """Test when entry doesn't invalidate thinking"""
        entry = EvidenceEntry(
            entry_number=4,
            timestamp="2025-10-06 15:00:00 MDT",
            prompt_input="Continue investigation",
            raw_output="Collecting more data",
            context_type="system",
            source="user"
        )
        
        decision = checker.check_entry(sample_agent, entry)
        
        assert decision.should_terminate is False
        assert decision.invalidation_type == InvalidationType.NONE
    
    def test_multiple_entries_first_invalidates(self, checker, sample_agent):
        """Test checking multiple entries where first one invalidates"""
        entries = [
            EvidenceEntry(
                entry_number=4,
                timestamp="2025-10-06 15:00:00 MDT",
                prompt_input="ThinPrint approach failed",
                raw_output="No improvement",
                context_type="system",
                source="user"
            ),
            EvidenceEntry(
                entry_number=5,
                timestamp="2025-10-06 15:05:00 MDT",
                prompt_input="More data",
                raw_output="Collecting info",
                context_type="system",
                source="user"
            )
        ]
        
        decision = checker.check_multiple_entries(sample_agent, entries)
        
        # Should terminate on first entry
        assert decision.should_terminate is True
        assert decision.conflicting_entry == 4
    
    def test_multiple_entries_none_invalidate(self, checker, sample_agent):
        """Test checking multiple entries where none invalidate"""
        entries = [
            EvidenceEntry(
                entry_number=4,
                timestamp="2025-10-06 15:00:00 MDT",
                prompt_input="Continue investigation",
                raw_output="More data",
                context_type="system",
                source="user"
            ),
            EvidenceEntry(
                entry_number=5,
                timestamp="2025-10-06 15:05:00 MDT",
                prompt_input="Another check",
                raw_output="Still collecting",
                context_type="system",
                source="user"
            )
        ]
        
        decision = checker.check_multiple_entries(sample_agent, entries)
        
        assert decision.should_terminate is False
    
    def test_confidence_calculation(self, checker):
        """Test confidence scoring"""
        # No matched rules
        confidence = checker._calculate_confidence([])
        assert confidence == 0.0
        
        # One matched rule
        confidence = checker._calculate_confidence(["rule1"])
        assert 0.7 <= confidence <= 1.0
        
        # Multiple matched rules
        confidence = checker._calculate_confidence(["rule1", "rule2", "rule3"])
        assert confidence == 1.0  # Capped at 1.0
    
    def test_custom_rule_addition(self, checker):
        """Test adding custom invalidation rules"""
        initial_count = len(checker.rules)
        
        def custom_check(agent, entry):
            return "custom_keyword" in entry.prompt_input.lower()
        
        rule = InvalidationRule(
            name="custom_rule",
            invalidation_type=InvalidationType.USER_DIRECTION_CHANGE,
            severity=InvalidationSeverity.TERMINATE,
            check=custom_check,
            description="Custom test rule"
        )
        
        checker.add_rule(rule)
        
        assert len(checker.rules) == initial_count + 1
        assert checker.rules[-1].name == "custom_rule"


class TestGlobalChecker:
    """Test global checker singleton"""
    
    def test_get_checker(self):
        """Test getting global checker"""
        checker1 = get_checker()
        checker2 = get_checker()
        
        # Should return same instance
        assert checker1 is checker2
    
    def test_default_rules_initialized(self):
        """Test that default rules are initialized"""
        checker = get_checker()
        
        # Should have default rules
        assert len(checker.rules) >= 5
        
        rule_names = [rule.name for rule in checker.rules]
        assert "user_approach_failed" in rule_names
        assert "user_direction_change" in rule_names
        assert "agent_solution_found" in rule_names
        assert "context_shift" in rule_names


class TestRealScenarios:
    """Test real-world scenarios from ticket-002"""
    
    @pytest.fixture
    def sample_agent(self):
        """Create a sample thinking agent"""
        now = datetime.utcnow().isoformat() + "Z"
        return AgentInstance(
            agent_id="test-agent-001",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file="evidence/database-performance.md",
            evidence_entry_range=(1, 3),
            started_at=now,
            last_context_check=now,
            metadata={"hypothesis": "ThinPrint configuration is the issue"}
        )
    
    def test_ticket_002_thinprint_failure(self, sample_agent):
        """Test ticket-002 scenario: ThinPrint solution failed"""
        checker = InvalidationChecker()
        
        # User reports ThinPrint failed after 3 days
        entry = EvidenceEntry(
            entry_number=10,
            timestamp="2025-01-27 15:00:00 MDT",
            prompt_input="Check ThinPrint solution status",
            raw_output="Wrapper deployed for 3+ days. No improvement. Solution failed.",
            context_type="system",
            source="user"
        )
        
        decision = checker.check_entry(sample_agent, entry)
        
        # Should terminate agent thinking about ThinPrint
        assert decision.should_terminate is True
        assert decision.invalidation_type == InvalidationType.APPROACH_FAILED
    
    def test_ticket_002_database_discovery(self):
        """Test ticket-002 scenario: Database fragmentation discovered"""
        checker = InvalidationChecker()
        
        # Agent was thinking about ThinPrint
        agent = AgentInstance(
            agent_id="thinprint-analyzer",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file="evidence/system-diagnostics.md",
            evidence_entry_range=(1, 10),
            started_at=datetime.utcnow().isoformat() + "Z",
            last_context_check=datetime.utcnow().isoformat() + "Z",
            metadata={"hypothesis": "ThinPrint configuration is causing delays"}
        )
        
        # User pivots to database investigation
        entry = EvidenceEntry(
            entry_number=11,
            timestamp="2025-10-06 14:30:00 MDT",
            prompt_input="Let's check database fragmentation instead",
            raw_output="Product.IX_description shows 100% fragmentation",
            context_type="database-performance",
            source="user"
        )
        
        decision = checker.check_entry(agent, entry)
        
        # Should terminate ThinPrint agent
        assert decision.should_terminate is True
        # Could be direction change or context shift
        assert decision.invalidation_type in [
            InvalidationType.USER_DIRECTION_CHANGE,
            InvalidationType.CONTEXT_SHIFT
        ]
    
    def test_ticket_002_solution_validated(self, sample_agent):
        """Test ticket-002 scenario: Database solution validated"""
        checker = InvalidationChecker()
        
        # Another agent validates solution
        entry = EvidenceEntry(
            entry_number=15,
            timestamp="2025-10-06 14:45:00 MDT",
            prompt_input="Performance validation",
            raw_output="Print time: 2.27s (down from 16s). 86% improvement. Solution confirmed!",
            context_type="database-performance",
            source="agent"
        )
        
        decision = checker.check_entry(sample_agent, entry)
        
        # Should terminate agent still thinking
        assert decision.should_terminate is True
        assert decision.invalidation_type == InvalidationType.AGENT_SOLUTION_FOUND
        assert "solution" in decision.reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

