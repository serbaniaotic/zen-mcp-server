"""
Tests for Agent Registry system
"""

import asyncio
import pytest
from datetime import datetime

from tools.agent_registry import (
    AgentInstance,
    AgentRegistry,
    AgentStatus,
    AgentType,
    create_agent_id,
    get_registry,
)


class TestAgentRegistry:
    """Test Agent Registry functionality"""
    
    @pytest.fixture
    async def registry(self):
        """Create a fresh registry for each test"""
        return AgentRegistry()
    
    @pytest.fixture
    async def sample_agent(self):
        """Create a sample agent instance"""
        now = datetime.utcnow().isoformat() + "Z"
        return AgentInstance(
            agent_id="test-agent-001",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file="evidence/database-performance.md",
            evidence_entry_range=(1, 3),
            started_at=now,
            last_context_check=now
        )
    
    @pytest.mark.asyncio
    async def test_register_agent(self, registry, sample_agent):
        """Test registering an agent"""
        agent_id = await registry.register(sample_agent)
        assert agent_id == sample_agent.agent_id
        
        # Verify agent is in registry
        retrieved = await registry.get(agent_id)
        assert retrieved is not None
        assert retrieved.agent_id == agent_id
    
    @pytest.mark.asyncio
    async def test_register_duplicate_agent(self, registry, sample_agent):
        """Test registering same agent twice raises error"""
        await registry.register(sample_agent)
        
        with pytest.raises(ValueError):
            await registry.register(sample_agent)
    
    @pytest.mark.asyncio
    async def test_get_by_ticket(self, registry):
        """Test querying agents by ticket"""
        # Create multiple agents for same ticket
        now = datetime.utcnow().isoformat() + "Z"
        agents = [
            AgentInstance(
                agent_id=f"agent-{i}",
                agent_type=AgentType.THINKING,
                status=AgentStatus.THINKING,
                ticket_id="002",
                evidence_file="evidence/test.md",
                evidence_entry_range=(1, 3),
                started_at=now,
                last_context_check=now
            )
            for i in range(3)
        ]
        
        for agent in agents:
            await registry.register(agent)
        
        # Query by ticket
        ticket_agents = await registry.get_by_ticket("002")
        assert len(ticket_agents) == 3
    
    @pytest.mark.asyncio
    async def test_get_thinking_agents(self, registry):
        """Test getting only thinking agents"""
        now = datetime.utcnow().isoformat() + "Z"
        
        # Create mixed status agents
        agent1 = AgentInstance(
            agent_id="agent-1",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file="evidence/test.md",
            evidence_entry_range=(1, 3),
            started_at=now,
            last_context_check=now
        )
        
        agent2 = AgentInstance(
            agent_id="agent-2",
            agent_type=AgentType.GUARDIAN,
            status=AgentStatus.APPENDING,
            ticket_id="002",
            evidence_file="evidence/test.md",
            evidence_entry_range=(1, 4),
            started_at=now,
            last_context_check=now
        )
        
        await registry.register(agent1)
        await registry.register(agent2)
        
        # Get thinking agents only
        thinking = await registry.get_thinking_agents("002")
        assert len(thinking) == 1
        assert thinking[0].agent_id == "agent-1"
    
    @pytest.mark.asyncio
    async def test_terminate_agent(self, registry, sample_agent):
        """Test terminating an agent"""
        await registry.register(sample_agent)
        
        # Terminate
        reason = "User changed direction"
        success = await registry.terminate(sample_agent.agent_id, reason)
        assert success
        
        # Verify termination
        agent = await registry.get(sample_agent.agent_id)
        assert agent.status == AgentStatus.TERMINATED
        assert agent.termination_reason == reason
    
    @pytest.mark.asyncio
    async def test_update_status(self, registry, sample_agent):
        """Test updating agent status"""
        await registry.register(sample_agent)
        
        # Update status
        success = await registry.update_status(
            sample_agent.agent_id,
            AgentStatus.COMPLETED
        )
        assert success
        
        # Verify
        agent = await registry.get(sample_agent.agent_id)
        assert agent.status == AgentStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_update_evidence_range(self, registry, sample_agent):
        """Test updating evidence range"""
        await registry.register(sample_agent)
        
        # Update range
        new_range = (1, 5)
        success = await registry.update_evidence_range(
            sample_agent.agent_id,
            new_range
        )
        assert success
        
        # Verify
        agent = await registry.get(sample_agent.agent_id)
        assert agent.evidence_entry_range == new_range
    
    @pytest.mark.asyncio
    async def test_cleanup(self, registry, sample_agent):
        """Test cleaning up agent"""
        await registry.register(sample_agent)
        
        # Cleanup
        success = await registry.cleanup(sample_agent.agent_id)
        assert success
        
        # Verify removed
        agent = await registry.get(sample_agent.agent_id)
        assert agent is None
    
    @pytest.mark.asyncio
    async def test_get_children(self, registry):
        """Test getting forked agents"""
        now = datetime.utcnow().isoformat() + "Z"
        
        # Create parent agent
        parent = AgentInstance(
            agent_id="parent-agent",
            agent_type=AgentType.THINKING,
            status=AgentStatus.THINKING,
            ticket_id="002",
            evidence_file="evidence/test.md",
            evidence_entry_range=(1, 3),
            started_at=now,
            last_context_check=now
        )
        
        # Create child agents
        children = [
            AgentInstance(
                agent_id=f"child-{i}",
                agent_type=AgentType.EVIDENCE_ORGANIZER,
                status=AgentStatus.THINKING,
                ticket_id="002",
                evidence_file="evidence/test.md",
                evidence_entry_range=(1, 3),
                started_at=now,
                last_context_check=now,
                parent_agent_id="parent-agent"
            )
            for i in range(2)
        ]
        
        await registry.register(parent)
        for child in children:
            await registry.register(child)
        
        # Get children
        found_children = await registry.get_children("parent-agent")
        assert len(found_children) == 2
    
    @pytest.mark.asyncio
    async def test_get_stats(self, registry):
        """Test getting registry statistics"""
        now = datetime.utcnow().isoformat() + "Z"
        
        # Create diverse agents
        agents = [
            AgentInstance(
                agent_id=f"agent-{i}",
                agent_type=AgentType.THINKING if i % 2 == 0 else AgentType.CURATOR,
                status=AgentStatus.THINKING if i < 2 else AgentStatus.COMPLETED,
                ticket_id=f"00{i % 2}",
                evidence_file="evidence/test.md",
                evidence_entry_range=(1, 3),
                started_at=now,
                last_context_check=now
            )
            for i in range(4)
        ]
        
        for agent in agents:
            await registry.register(agent)
        
        # Get stats
        stats = await registry.get_stats()
        assert stats["total_agents"] == 4
        assert stats["active_tickets"] == 2


class TestAgentIdGeneration:
    """Test agent ID generation"""
    
    @pytest.mark.asyncio
    async def test_create_agent_id(self):
        """Test creating unique agent IDs"""
        id1 = await create_agent_id(AgentType.THINKING, "002")
        await asyncio.sleep(0.001)  # Ensure different timestamp
        id2 = await create_agent_id(AgentType.THINKING, "002")
        
        # IDs should be unique (different timestamps)
        assert id1 != id2
        
        # IDs should have correct format
        assert "thinking-002-" in id1
        assert "thinking-002-" in id2


class TestGlobalRegistry:
    """Test global registry singleton"""
    
    def test_get_registry(self):
        """Test getting global registry"""
        registry1 = get_registry()
        registry2 = get_registry()
        
        # Should return same instance
        assert registry1 is registry2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

