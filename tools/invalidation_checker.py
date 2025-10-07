"""
Invalidation Checker - Intelligent thinking termination

Analyzes evidence entries to determine if an agent's thinking has been
invalidated by new information, enabling hallucination prevention.

Philosophy: "Grace in wisdom" - know when to stop and defer
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional

from .agent_registry import AgentInstance, AgentType
from .evidence_monitor import EvidenceEntry

logger = logging.getLogger(__name__)


class InvalidationType(Enum):
    """Types of invalidation that can occur"""
    USER_DIRECTION_CHANGE = "user_direction_change"
    AGENT_SOLUTION_FOUND = "agent_solution_found"
    CONTEXT_SHIFT = "context_shift"
    CONTRADICTION = "contradiction"
    APPROACH_FAILED = "approach_failed"
    NONE = "none"


class InvalidationSeverity(Enum):
    """Severity of invalidation"""
    TERMINATE = "terminate"  # Immediately stop thinking
    WARN = "warn"           # Continue but be aware
    INFO = "info"           # FYI only


@dataclass
class InvalidationRule:
    """
    Rule for detecting invalidation.
    
    A rule consists of:
    - Pattern to match (regex or keywords)
    - Check function (custom logic)
    - Severity (terminate/warn/info)
    - Type classification
    """
    name: str
    invalidation_type: InvalidationType
    severity: InvalidationSeverity
    check: Callable[[AgentInstance, EvidenceEntry], bool]
    description: str


@dataclass
class InvalidationDecision:
    """
    Decision about whether to terminate an agent.
    
    Contains:
    - Should terminate (yes/no)
    - Reason (human-readable)
    - Conflicting entry number
    - Recommendation for next steps
    - Confidence (0-1)
    """
    should_terminate: bool
    reason: str
    invalidation_type: InvalidationType
    conflicting_entry: int
    recommendation: str
    confidence: float = 1.0
    matched_rules: List[str] = None
    
    def __post_init__(self):
        if self.matched_rules is None:
            self.matched_rules = []


class InvalidationChecker:
    """
    Checks if new evidence invalidates an agent's thinking.
    
    Features:
    - Rule-based invalidation detection
    - Context shift analysis
    - Contradiction detection
    - Confidence scoring
    - Detailed reasoning
    """
    
    def __init__(self):
        self.rules: List[InvalidationRule] = []
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default invalidation rules"""
        
        # Rule 1: User says approach failed
        self.add_rule(InvalidationRule(
            name="user_approach_failed",
            invalidation_type=InvalidationType.APPROACH_FAILED,
            severity=InvalidationSeverity.TERMINATE,
            check=self._check_approach_failed,
            description="User reported that current approach failed"
        ))
        
        # Rule 2: User changes direction
        self.add_rule(InvalidationRule(
            name="user_direction_change",
            invalidation_type=InvalidationType.USER_DIRECTION_CHANGE,
            severity=InvalidationSeverity.TERMINATE,
            check=self._check_direction_change,
            description="User explicitly changed investigation direction"
        ))
        
        # Rule 3: Another agent found solution
        self.add_rule(InvalidationRule(
            name="agent_solution_found",
            invalidation_type=InvalidationType.AGENT_SOLUTION_FOUND,
            severity=InvalidationSeverity.TERMINATE,
            check=self._check_solution_found,
            description="Another agent already found and validated solution"
        ))
        
        # Rule 4: Context shifted significantly
        self.add_rule(InvalidationRule(
            name="context_shift",
            invalidation_type=InvalidationType.CONTEXT_SHIFT,
            severity=InvalidationSeverity.TERMINATE,
            check=self._check_context_shift,
            description="Investigation context shifted to different area"
        ))
        
        # Rule 5: Direct contradiction
        self.add_rule(InvalidationRule(
            name="contradiction",
            invalidation_type=InvalidationType.CONTRADICTION,
            severity=InvalidationSeverity.WARN,
            check=self._check_contradiction,
            description="New evidence contradicts agent's current hypothesis"
        ))
    
    def add_rule(self, rule: InvalidationRule) -> None:
        """Add a new invalidation rule"""
        self.rules.append(rule)
        logger.info(f"Added invalidation rule: {rule.name}")
    
    def check_entry(
        self,
        agent: AgentInstance,
        entry: EvidenceEntry
    ) -> InvalidationDecision:
        """
        Check if a single evidence entry invalidates agent's thinking.
        
        Args:
            agent: Agent instance to check
            entry: New evidence entry
            
        Returns:
            InvalidationDecision with reasoning
        """
        matched_rules = []
        highest_severity = InvalidationSeverity.INFO
        primary_type = InvalidationType.NONE
        
        # Check all rules
        for rule in self.rules:
            try:
                if rule.check(agent, entry):
                    matched_rules.append(rule.name)
                    
                    # Track highest severity
                    if rule.severity == InvalidationSeverity.TERMINATE:
                        highest_severity = InvalidationSeverity.TERMINATE
                        primary_type = rule.invalidation_type
                    elif rule.severity == InvalidationSeverity.WARN and highest_severity != InvalidationSeverity.TERMINATE:
                        highest_severity = InvalidationSeverity.WARN
                        if primary_type == InvalidationType.NONE:
                            primary_type = rule.invalidation_type
                            
            except Exception as e:
                logger.error(f"Rule {rule.name} failed: {e}")
        
        # Build decision
        should_terminate = highest_severity == InvalidationSeverity.TERMINATE
        
        if should_terminate:
            reason = self._build_termination_reason(agent, entry, matched_rules, primary_type)
            recommendation = self._build_recommendation(primary_type, entry)
            confidence = self._calculate_confidence(matched_rules)
        else:
            reason = "No invalidation detected"
            recommendation = "Continue thinking"
            confidence = 1.0
        
        return InvalidationDecision(
            should_terminate=should_terminate,
            reason=reason,
            invalidation_type=primary_type,
            conflicting_entry=entry.entry_number,
            recommendation=recommendation,
            confidence=confidence,
            matched_rules=matched_rules
        )
    
    def check_multiple_entries(
        self,
        agent: AgentInstance,
        entries: List[EvidenceEntry]
    ) -> InvalidationDecision:
        """
        Check multiple entries and return aggregate decision.
        
        If any entry causes termination, the agent should terminate.
        
        Args:
            agent: Agent instance
            entries: List of new entries
            
        Returns:
            Aggregate invalidation decision
        """
        if not entries:
            return InvalidationDecision(
                should_terminate=False,
                reason="No new entries",
                invalidation_type=InvalidationType.NONE,
                conflicting_entry=0,
                recommendation="Continue thinking",
                confidence=1.0
            )
        
        # Check each entry
        decisions = [self.check_entry(agent, entry) for entry in entries]
        
        # Find first terminating decision
        for decision in decisions:
            if decision.should_terminate:
                return decision
        
        # No termination, return info about all entries
        return InvalidationDecision(
            should_terminate=False,
            reason=f"Checked {len(entries)} new entries, none invalidate thinking",
            invalidation_type=InvalidationType.NONE,
            conflicting_entry=entries[-1].entry_number,
            recommendation="Continue thinking",
            confidence=1.0
        )
    
    # ============================================
    # Rule Implementation Functions
    # ============================================
    
    def _check_approach_failed(self, agent: AgentInstance, entry: EvidenceEntry) -> bool:
        """Check if user reported approach failed"""
        content = (entry.prompt_input + " " + entry.raw_output).lower()
        
        # Failure keywords
        failure_patterns = [
            r'\b(failed|failure|didn\'t work|not working|no improvement)\b',
            r'\b(after \d+ days?.*no|tried for.*failed)\b',
            r'\b(solution (failed|didn\'t work)|approach (failed|unsuccessful))\b'
        ]
        
        # Only from user
        if entry.source != "user":
            return False
        
        for pattern in failure_patterns:
            if re.search(pattern, content):
                logger.info(f"Detected approach failure in entry #{entry.entry_number}")
                return True
        
        return False
    
    def _check_direction_change(self, agent: AgentInstance, entry: EvidenceEntry) -> bool:
        """Check if user changed investigation direction"""
        content = (entry.prompt_input + " " + entry.raw_output).lower()
        
        # Direction change keywords
        change_patterns = [
            r'\b(try (different|alternative)|change approach|new (hypothesis|direction))\b',
            r'\b(instead|rather than|not.*but)\b',
            r'\b(pivot to|switch to|focus on .* instead)\b',
            r'\b(forget.*try|abandon.*approach)\b'
        ]
        
        # Only from user
        if entry.source != "user":
            return False
        
        for pattern in change_patterns:
            if re.search(pattern, content):
                logger.info(f"Detected direction change in entry #{entry.entry_number}")
                return True
        
        return False
    
    def _check_solution_found(self, agent: AgentInstance, entry: EvidenceEntry) -> bool:
        """Check if another agent found solution"""
        content = (entry.prompt_input + " " + entry.raw_output).lower()
        
        # Solution keywords
        solution_patterns = [
            r'\b(solution found|problem solved|fix (applied|working))\b',
            r'\b(successfully (fixed|resolved)|issue (resolved|closed))\b',
            r'\b(validation (successful|passed)|confirmed (working|fixed))\b',
            r'\b(\d+%\s*(improvement|reduction|better))\b'  # Performance improvement
        ]
        
        # From another agent or user confirming
        if entry.source not in ["agent", "user"]:
            return False
        
        for pattern in solution_patterns:
            if re.search(pattern, content):
                # Check it's not this agent's own work
                if entry.source == "agent":
                    # Would need to check if it's the same agent
                    # For now, assume different agent
                    logger.info(f"Detected solution found by other agent in entry #{entry.entry_number}")
                    return True
                elif entry.source == "user":
                    # User confirming solution works
                    logger.info(f"Detected user-confirmed solution in entry #{entry.entry_number}")
                    return True
        
        return False
    
    def _check_context_shift(self, agent: AgentInstance, entry: EvidenceEntry) -> bool:
        """Check if investigation context shifted"""
        # Get agent's context type
        agent_context = agent.metadata.get("context_type", "")
        entry_context = entry.context_type
        
        if not agent_context or not entry_context:
            return False
        
        # Significant context shifts
        context_shifts = {
            "database": ["network", "system", "hardware"],
            "network": ["database", "application", "security"],
            "system": ["database", "network", "application"],
            "performance": ["security", "configuration", "deployment"]
        }
        
        # Check if contexts are incompatible
        for base_context, incompatible_contexts in context_shifts.items():
            if base_context in agent_context.lower():
                for incompatible in incompatible_contexts:
                    if incompatible in entry_context.lower():
                        logger.info(
                            f"Detected context shift from {agent_context} to {entry_context} "
                            f"in entry #{entry.entry_number}"
                        )
                        return True
        
        return False
    
    def _check_contradiction(self, agent: AgentInstance, entry: EvidenceEntry) -> bool:
        """Check if entry contradicts agent's hypothesis"""
        content = (entry.prompt_input + " " + entry.raw_output).lower()
        
        # Get agent's hypothesis if available
        agent_hypothesis = agent.metadata.get("hypothesis", "").lower()
        
        if not agent_hypothesis:
            return False
        
        # Contradiction patterns
        contradiction_patterns = [
            r'\b(actually|in fact|turns out|however)\b',
            r'\b(not .* but|instead of|contrary to)\b',
            r'\b(disproved|incorrect|wrong assumption)\b'
        ]
        
        # Check if hypothesis mentioned and contradicted
        hypothesis_mentioned = any(word in content for word in agent_hypothesis.split()[:3])
        
        if hypothesis_mentioned:
            for pattern in contradiction_patterns:
                if re.search(pattern, content):
                    logger.info(f"Detected contradiction to hypothesis in entry #{entry.entry_number}")
                    return True
        
        return False
    
    # ============================================
    # Helper Functions
    # ============================================
    
    def _build_termination_reason(
        self,
        agent: AgentInstance,
        entry: EvidenceEntry,
        matched_rules: List[str],
        invalidation_type: InvalidationType
    ) -> str:
        """Build human-readable termination reason"""
        reasons = {
            InvalidationType.APPROACH_FAILED: (
                f"Entry #{entry.entry_number} indicates the current approach failed. "
                f"User reported no improvement or unsuccessful results."
            ),
            InvalidationType.USER_DIRECTION_CHANGE: (
                f"Entry #{entry.entry_number} shows user changed investigation direction. "
                f"New approach requested."
            ),
            InvalidationType.AGENT_SOLUTION_FOUND: (
                f"Entry #{entry.entry_number} shows another agent found and validated solution. "
                f"Your thinking is no longer needed."
            ),
            InvalidationType.CONTEXT_SHIFT: (
                f"Entry #{entry.entry_number} shifted investigation context. "
                f"Focus moved to different area."
            ),
            InvalidationType.CONTRADICTION: (
                f"Entry #{entry.entry_number} contradicts your current hypothesis."
            )
        }
        
        base_reason = reasons.get(invalidation_type, "Unknown invalidation")
        matched_info = f" (Matched rules: {', '.join(matched_rules)})" if matched_rules else ""
        
        return base_reason + matched_info
    
    def _build_recommendation(
        self,
        invalidation_type: InvalidationType,
        entry: EvidenceEntry
    ) -> str:
        """Build recommendation for agent"""
        recommendations = {
            InvalidationType.APPROACH_FAILED: (
                "Terminate thinking. If user asks, acknowledge the failed approach "
                "and defer to current investigation direction."
            ),
            InvalidationType.USER_DIRECTION_CHANGE: (
                "Terminate thinking. User has new direction. "
                "If needed, new agent should be spawned for new context."
            ),
            InvalidationType.AGENT_SOLUTION_FOUND: (
                "Terminate thinking. Solution already validated. "
                "Defer to completed solution if user asks."
            ),
            InvalidationType.CONTEXT_SHIFT: (
                "Terminate thinking. Investigation moved to different context. "
                "Your expertise may not apply to new focus area."
            ),
            InvalidationType.CONTRADICTION: (
                "Review entry and re-evaluate hypothesis. "
                "May need to terminate if contradiction is strong."
            )
        }
        
        return recommendations.get(invalidation_type, "Continue with caution")
    
    def _calculate_confidence(self, matched_rules: List[str]) -> float:
        """Calculate confidence in invalidation decision"""
        if not matched_rules:
            return 0.0
        
        # More matched rules = higher confidence
        # But cap at 1.0
        base_confidence = 0.7
        bonus = min(len(matched_rules) * 0.15, 0.3)
        
        return min(base_confidence + bonus, 1.0)


# Global checker instance
_checker: Optional[InvalidationChecker] = None


def get_checker() -> InvalidationChecker:
    """Get or create the global invalidation checker"""
    global _checker
    if _checker is None:
        _checker = InvalidationChecker()
    return _checker

