"""
Agent Registry - Multi-Agent Coordination System

Tracks active agents, their status, and coordinates thinking termination
to prevent hallucination from outdated responses.

Philosophy: "Grace in wisdom" - intelligent coordination without waste
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set


class AgentStatus(Enum):
    """Agent execution status"""
    FOREGROUND = "foreground"      # User-facing agent
    THINKING = "thinking"          # Background processing
    APPENDING = "appending"        # Writing evidence
    VALIDATING = "validating"      # Checking context
    TERMINATED = "terminated"      # Stopped due to invalidation
    COMPLETED = "completed"        # Finished successfully


class AgentType(Enum):
    """Type of agent"""
    CURATOR = "curator"
    GUARDIAN = "guardian"
    EVIDENCE_ORGANIZER = "evidence-organizer"
    FOLDER_PARSER = "folder-parser"
    THINKING = "thinking"
    ORCHESTRATOR = "orchestrator"


@dataclass
class AgentInstance:
    """Represents an active agent in the system"""
    agent_id: str
    agent_type: AgentType
    status: AgentStatus
    ticket_id: str
    evidence_file: str
    evidence_entry_range: tuple[int, int]  # (start, end) entry numbers agent has seen
    started_at: str  # ISO timestamp
    last_context_check: str  # ISO timestamp
    context_check_interval: int = 5000  # milliseconds
    parent_agent_id: Optional[str] = None  # if forked from another agent
    termination_reason: Optional[str] = None
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "status": self.status.value,
            "ticket_id": self.ticket_id,
            "evidence_file": self.evidence_file,
            "evidence_entry_range": list(self.evidence_entry_range),
            "started_at": self.started_at,
            "last_context_check": self.last_context_check,
            "context_check_interval": self.context_check_interval,
            "parent_agent_id": self.parent_agent_id,
            "termination_reason": self.termination_reason,
            "metadata": self.metadata
        }


class AgentRegistry:
    """
    Registry for tracking active agents and coordinating multi-agent workflows.
    
    Features:
    - Track agent status and lifecycle
    - Query agents by ticket, status, or type
    - Coordinate thinking termination
    - Manage agent hierarchy (parent/child relationships)
    """
    
    def __init__(self):
        self.agents: Dict[str, AgentInstance] = {}
        self.ticket_index: Dict[str, Set[str]] = {}  # ticket_id -> set of agent_ids
        self._lock = asyncio.Lock()
    
    async def register(self, agent: AgentInstance) -> str:
        """
        Register a new agent in the registry.
        
        Args:
            agent: Agent instance to register
            
        Returns:
            agent_id: The registered agent's ID
        """
        async with self._lock:
            if agent.agent_id in self.agents:
                raise ValueError(f"Agent {agent.agent_id} already registered")
            
            self.agents[agent.agent_id] = agent
            
            # Index by ticket
            if agent.ticket_id not in self.ticket_index:
                self.ticket_index[agent.ticket_id] = set()
            self.ticket_index[agent.ticket_id].add(agent.agent_id)
            
            return agent.agent_id
    
    async def get(self, agent_id: str) -> Optional[AgentInstance]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    async def get_by_ticket(self, ticket_id: str) -> List[AgentInstance]:
        """Get all agents working on a specific ticket"""
        agent_ids = self.ticket_index.get(ticket_id, set())
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]
    
    async def get_thinking_agents(self, ticket_id: str) -> List[AgentInstance]:
        """Get all agents currently in thinking status for a ticket"""
        agents = await self.get_by_ticket(ticket_id)
        return [a for a in agents if a.status == AgentStatus.THINKING]
    
    async def get_by_status(self, status: AgentStatus) -> List[AgentInstance]:
        """Get all agents with specific status"""
        return [a for a in self.agents.values() if a.status == status]
    
    async def get_by_type(self, agent_type: AgentType) -> List[AgentInstance]:
        """Get all agents of specific type"""
        return [a for a in self.agents.values() if a.agent_type == agent_type]
    
    async def update_status(self, agent_id: str, new_status: AgentStatus) -> bool:
        """Update agent status"""
        async with self._lock:
            if agent_id not in self.agents:
                return False
            
            self.agents[agent_id].status = new_status
            return True
    
    async def update_context_check(self, agent_id: str) -> bool:
        """Update last context check timestamp"""
        async with self._lock:
            if agent_id not in self.agents:
                return False
            
            self.agents[agent_id].last_context_check = datetime.utcnow().isoformat() + "Z"
            return True
    
    async def update_evidence_range(self, agent_id: str, new_range: tuple[int, int]) -> bool:
        """Update the evidence entry range an agent has seen"""
        async with self._lock:
            if agent_id not in self.agents:
                return False
            
            self.agents[agent_id].evidence_entry_range = new_range
            return True
    
    async def terminate(self, agent_id: str, reason: str) -> bool:
        """
        Terminate an agent with a reason.
        
        This is used when an agent's thinking has been invalidated by
        new evidence or other agents' work.
        
        Args:
            agent_id: ID of agent to terminate
            reason: Human-readable reason for termination
            
        Returns:
            True if agent was terminated, False if not found
        """
        async with self._lock:
            if agent_id not in self.agents:
                return False
            
            agent = self.agents[agent_id]
            agent.status = AgentStatus.TERMINATED
            agent.termination_reason = reason
            
            return True
    
    async def complete(self, agent_id: str) -> bool:
        """Mark agent as completed successfully"""
        return await self.update_status(agent_id, AgentStatus.COMPLETED)
    
    async def cleanup(self, agent_id: str) -> bool:
        """
        Remove agent from registry.
        
        Should only be called after agent is terminated or completed.
        """
        async with self._lock:
            if agent_id not in self.agents:
                return False
            
            agent = self.agents[agent_id]
            
            # Remove from ticket index
            if agent.ticket_id in self.ticket_index:
                self.ticket_index[agent.ticket_id].discard(agent_id)
                if not self.ticket_index[agent.ticket_id]:
                    del self.ticket_index[agent.ticket_id]
            
            # Remove from main registry
            del self.agents[agent_id]
            
            return True
    
    async def get_children(self, parent_agent_id: str) -> List[AgentInstance]:
        """Get all agents forked from a parent agent"""
        return [
            a for a in self.agents.values()
            if a.parent_agent_id == parent_agent_id
        ]
    
    async def get_stats(self) -> Dict:
        """Get registry statistics"""
        return {
            "total_agents": len(self.agents),
            "by_status": {
                status.value: len([a for a in self.agents.values() if a.status == status])
                for status in AgentStatus
            },
            "by_type": {
                atype.value: len([a for a in self.agents.values() if a.agent_type == atype])
                for atype in AgentType
            },
            "active_tickets": len(self.ticket_index),
        }
    
    async def get_ticket_status(self, ticket_id: str) -> Dict:
        """Get status of all agents for a specific ticket"""
        agents = await self.get_by_ticket(ticket_id)
        
        return {
            "ticket_id": ticket_id,
            "total_agents": len(agents),
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "type": a.agent_type.value,
                    "status": a.status.value,
                    "started_at": a.started_at,
                    "termination_reason": a.termination_reason
                }
                for a in agents
            ]
        }


# Global registry instance
_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """Get or create the global agent registry"""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


async def create_agent_id(agent_type: AgentType, ticket_id: str) -> str:
    """
    Generate unique agent ID.
    
    Format: {agent_type}-{ticket_id}-{timestamp_ms}
    """
    timestamp_ms = int(time.time() * 1000)
    return f"{agent_type.value}-{ticket_id}-{timestamp_ms}"

