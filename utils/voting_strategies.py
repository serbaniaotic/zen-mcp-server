"""
Voting strategies for consensus tool in Zen MCP Server.

Provides multiple voting strategies to determine the final decision from multiple model responses:
- Democratic voting: One model, one vote (simple majority)
- Quality-weighted voting: Votes weighted by reasoning quality
- Token-optimized voting: Balance quality vs. token cost

Voting results are logged to analytics for comparison and optimization.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class VotingStrategy(Enum):
    """Voting strategy enumeration"""
    DEMOCRATIC = "democratic"
    QUALITY_WEIGHTED = "quality_weighted"
    TOKEN_OPTIMIZED = "token_optimized"


@dataclass
class VotingResult:
    """Result of a voting process"""
    winning_decision: str
    strategy_used: str
    vote_breakdown: Dict[str, Any]
    confidence: float
    total_models: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert voting result to dictionary"""
        return {
            "winning_decision": self.winning_decision,
            "strategy_used": self.strategy_used,
            "vote_breakdown": self.vote_breakdown,
            "confidence": self.confidence,
            "total_models": self.total_models,
            "metadata": self.metadata,
        }


class BaseVotingStrategy(ABC):
    """Base class for voting strategies"""
    
    @abstractmethod
    def vote(self, model_responses: List[Dict[str, Any]]) -> VotingResult:
        """
        Determine the winning decision from model responses.
        
        Args:
            model_responses: List of model response dictionaries
            
        Returns:
            VotingResult with winning decision and metadata
        """
        pass
    
    def _extract_decision(self, response: Dict[str, Any]) -> str:
        """
        Extract the decision from a model response.
        
        Looks for explicit decision keywords or uses stance as fallback.
        """
        verdict = response.get("verdict", "")
        
        # Check for explicit decision keywords
        decision_patterns = {
            "approve": ["approve", "accept", "proceed", "go ahead", "recommend"],
            "reject": ["reject", "decline", "not recommend", "advise against", "oppose"],
            "conditional": ["conditional", "with caveats", "if and only if", "depends on"],
        }
        
        verdict_lower = verdict.lower()
        
        for decision, keywords in decision_patterns.items():
            if any(keyword in verdict_lower for keyword in keywords):
                return decision
        
        # Fallback to stance
        stance = response.get("stance", "neutral")
        stance_to_decision = {
            "for": "approve",
            "against": "reject",
            "neutral": "conditional"
        }
        
        return stance_to_decision.get(stance, "conditional")
    
    def _assess_reasoning_quality(self, verdict: str) -> float:
        """
        Assess the quality of reasoning in a verdict.
        
        Returns a score from 0.0 to 1.0 based on various quality indicators.
        """
        if not verdict:
            return 0.1
        
        quality_score = 0.0
        
        # 1. Length factor (but with diminishing returns)
        word_count = len(verdict.split())
        if word_count >= 200:
            quality_score += 0.15
        elif word_count >= 100:
            quality_score += 0.10
        elif word_count >= 50:
            quality_score += 0.05
        
        # 2. Structure indicators
        structure_indicators = [
            "first", "second", "third",  # Numbered points
            "however", "therefore", "consequently",  # Logical connectors
            "because", "since", "as a result",  # Causal reasoning
            "pros:", "cons:", "advantages:", "disadvantages:",  # Structured analysis
        ]
        structure_count = sum(1 for indicator in structure_indicators if indicator.lower() in verdict.lower())
        quality_score += min(0.15, structure_count * 0.03)
        
        # 3. Evidence indicators
        evidence_indicators = [
            "data shows", "research indicates", "studies suggest",
            "evidence", "according to", "measured", "tested",
            "example", "case study", "benchmark",
        ]
        evidence_count = sum(1 for indicator in evidence_indicators if indicator.lower() in verdict.lower())
        quality_score += min(0.20, evidence_count * 0.05)
        
        # 4. Risk analysis indicators
        risk_indicators = [
            "risk", "potential issue", "concern", "caveat",
            "trade-off", "downside", "limitation", "challenge",
        ]
        risk_count = sum(1 for indicator in risk_indicators if indicator.lower() in verdict.lower())
        quality_score += min(0.15, risk_count * 0.05)
        
        # 5. Actionable recommendations
        action_indicators = [
            "recommend", "suggest", "should", "propose",
            "next steps", "action items", "implementation",
        ]
        action_count = sum(1 for indicator in action_indicators if indicator.lower() in verdict.lower())
        quality_score += min(0.15, action_count * 0.05)
        
        # 6. Specificity indicators
        specificity_indicators = [
            "specifically", "precisely", "exactly",
            r"\d+%", r"\d+ (days|weeks|months)",  # Numeric specifics
            r"\$\d+",  # Cost specifics
        ]
        specificity_count = sum(
            1 for indicator in specificity_indicators
            if (indicator.startswith(r"\d") and re.search(indicator, verdict))
            or indicator.lower() in verdict.lower()
        )
        quality_score += min(0.10, specificity_count * 0.03)
        
        # 7. Balanced analysis indicator
        if ("pros" in verdict.lower() or "advantages" in verdict.lower()) and \
           ("cons" in verdict.lower() or "disadvantages" in verdict.lower()):
            quality_score += 0.10
        
        # Normalize to 0.0 - 1.0 range
        return min(1.0, max(0.1, quality_score))


class DemocraticVoting(BaseVotingStrategy):
    """
    Democratic voting: One model, one vote.
    
    Simple majority wins. If tie, defaults to "conditional".
    """
    
    def vote(self, model_responses: List[Dict[str, Any]]) -> VotingResult:
        """Implement democratic voting"""
        if not model_responses:
            return VotingResult(
                winning_decision="conditional",
                strategy_used="democratic",
                vote_breakdown={},
                confidence=0.0,
                total_models=0,
                metadata={"reason": "No model responses provided"}
            )
        
        # Count votes
        votes: Dict[str, int] = {}
        decision_models: Dict[str, List[str]] = {}
        
        for response in model_responses:
            decision = self._extract_decision(response)
            model_name = response.get("model", "unknown")
            
            votes[decision] = votes.get(decision, 0) + 1
            
            if decision not in decision_models:
                decision_models[decision] = []
            decision_models[decision].append(model_name)
        
        # Find winner
        if not votes:
            return VotingResult(
                winning_decision="conditional",
                strategy_used="democratic",
                vote_breakdown={},
                confidence=0.0,
                total_models=len(model_responses),
                metadata={"reason": "No valid votes extracted"}
            )
        
        max_votes = max(votes.values())
        winners = [decision for decision, count in votes.items() if count == max_votes]
        
        # Handle tie
        if len(winners) > 1:
            winning_decision = "conditional"  # Tie defaults to conditional
            confidence = 0.5
            metadata = {
                "tie": True,
                "tied_decisions": winners,
                "reason": "Tie broken by defaulting to conditional"
            }
        else:
            winning_decision = winners[0]
            confidence = max_votes / len(model_responses)
            metadata = {"tie": False}
        
        vote_breakdown = {
            "votes_by_decision": votes,
            "models_by_decision": decision_models,
            "winner": winning_decision,
            "percentage": f"{confidence * 100:.1f}%"
        }
        
        logger.info(
            f"Democratic voting complete: {winning_decision} wins with {max_votes}/{len(model_responses)} votes"
        )
        
        return VotingResult(
            winning_decision=winning_decision,
            strategy_used="democratic",
            vote_breakdown=vote_breakdown,
            confidence=confidence,
            total_models=len(model_responses),
            metadata=metadata
        )


class QualityWeightedVoting(BaseVotingStrategy):
    """
    Quality-weighted voting: Votes weighted by reasoning quality.
    
    Each model's vote is weighted by the assessed quality of its reasoning.
    Quality is determined by factors like:
    - Structure and organization
    - Evidence and examples
    - Risk analysis
    - Actionable recommendations
    - Specificity
    """
    
    def vote(self, model_responses: List[Dict[str, Any]]) -> VotingResult:
        """Implement quality-weighted voting"""
        if not model_responses:
            return VotingResult(
                winning_decision="conditional",
                strategy_used="quality_weighted",
                vote_breakdown={},
                confidence=0.0,
                total_models=0,
                metadata={"reason": "No model responses provided"}
            )
        
        # Calculate weighted scores
        weighted_scores: Dict[str, float] = {}
        quality_by_model: Dict[str, float] = {}
        decision_details: Dict[str, List[Dict]] = {}
        
        total_quality = 0.0
        
        for response in model_responses:
            decision = self._extract_decision(response)
            model_name = response.get("model", "unknown")
            verdict = response.get("verdict", "")
            
            # Assess quality
            quality = self._assess_reasoning_quality(verdict)
            total_quality += quality
            
            # Weight vote by quality
            weighted_scores[decision] = weighted_scores.get(decision, 0.0) + quality
            quality_by_model[model_name] = quality
            
            if decision not in decision_details:
                decision_details[decision] = []
            
            decision_details[decision].append({
                "model": model_name,
                "quality": quality,
                "weight_contribution": quality
            })
        
        # Find winner
        if not weighted_scores:
            return VotingResult(
                winning_decision="conditional",
                strategy_used="quality_weighted",
                vote_breakdown={},
                confidence=0.0,
                total_models=len(model_responses),
                metadata={"reason": "No valid weighted scores"}
            )
        
        winning_decision = max(weighted_scores.items(), key=lambda x: x[1])[0]
        winning_score = weighted_scores[winning_decision]
        confidence = winning_score / total_quality if total_quality > 0 else 0.0
        
        vote_breakdown = {
            "weighted_scores_by_decision": {
                k: f"{v:.3f}" for k, v in weighted_scores.items()
            },
            "quality_by_model": {
                k: f"{v:.3f}" for k, v in quality_by_model.items()
            },
            "decision_details": decision_details,
            "winner": winning_decision,
            "winning_score": f"{winning_score:.3f}",
            "total_quality": f"{total_quality:.3f}",
            "confidence": f"{confidence * 100:.1f}%"
        }
        
        logger.info(
            f"Quality-weighted voting complete: {winning_decision} wins with score {winning_score:.3f}/{total_quality:.3f}"
        )
        
        return VotingResult(
            winning_decision=winning_decision,
            strategy_used="quality_weighted",
            vote_breakdown=vote_breakdown,
            confidence=confidence,
            total_models=len(model_responses),
            metadata={
                "avg_quality": total_quality / len(model_responses),
                "quality_range": [
                    min(quality_by_model.values()),
                    max(quality_by_model.values())
                ]
            }
        )


class TokenOptimizedVoting(BaseVotingStrategy):
    """
    Token-optimized voting: Balance quality vs. token cost.
    
    Each model's vote is weighted by quality per token used.
    This favors concise, high-quality reasoning over verbose responses.
    
    Score = quality / (tokens / 1000)
    Higher score = better value (more quality per 1K tokens)
    """
    
    def vote(self, model_responses: List[Dict[str, Any]]) -> VotingResult:
        """Implement token-optimized voting"""
        if not model_responses:
            return VotingResult(
                winning_decision="conditional",
                strategy_used="token_optimized",
                vote_breakdown={},
                confidence=0.0,
                total_models=0,
                metadata={"reason": "No model responses provided"}
            )
        
        # Calculate efficiency scores
        efficiency_scores: Dict[str, float] = {}
        model_efficiency: Dict[str, Dict] = {}
        decision_details: Dict[str, List[Dict]] = {}
        
        total_efficiency = 0.0
        
        for response in model_responses:
            decision = self._extract_decision(response)
            model_name = response.get("model", "unknown")
            verdict = response.get("verdict", "")
            
            # Assess quality
            quality = self._assess_reasoning_quality(verdict)
            
            # Estimate tokens (rough approximation: 1 token ≈ 0.75 words)
            tokens = response.get("tokens_used")
            if tokens is None:
                # Estimate from verdict length
                word_count = len(verdict.split())
                tokens = int(word_count / 0.75)
            
            # Avoid division by zero
            tokens = max(tokens, 10)
            
            # Calculate efficiency: quality per 1K tokens
            efficiency = quality / (tokens / 1000)
            total_efficiency += efficiency
            
            # Weight vote by efficiency
            efficiency_scores[decision] = efficiency_scores.get(decision, 0.0) + efficiency
            
            model_efficiency[model_name] = {
                "quality": quality,
                "tokens": tokens,
                "efficiency": efficiency
            }
            
            if decision not in decision_details:
                decision_details[decision] = []
            
            decision_details[decision].append({
                "model": model_name,
                "quality": quality,
                "tokens": tokens,
                "efficiency": efficiency,
                "weight_contribution": efficiency
            })
        
        # Find winner
        if not efficiency_scores:
            return VotingResult(
                winning_decision="conditional",
                strategy_used="token_optimized",
                vote_breakdown={},
                confidence=0.0,
                total_models=len(model_responses),
                metadata={"reason": "No valid efficiency scores"}
            )
        
        winning_decision = max(efficiency_scores.items(), key=lambda x: x[1])[0]
        winning_score = efficiency_scores[winning_decision]
        confidence = winning_score / total_efficiency if total_efficiency > 0 else 0.0
        
        vote_breakdown = {
            "efficiency_scores_by_decision": {
                k: f"{v:.3f}" for k, v in efficiency_scores.items()
            },
            "model_efficiency": {
                k: {
                    "quality": f"{v['quality']:.3f}",
                    "tokens": v['tokens'],
                    "efficiency": f"{v['efficiency']:.3f}"
                }
                for k, v in model_efficiency.items()
            },
            "decision_details": decision_details,
            "winner": winning_decision,
            "winning_score": f"{winning_score:.3f}",
            "total_efficiency": f"{total_efficiency:.3f}",
            "confidence": f"{confidence * 100:.1f}%"
        }
        
        logger.info(
            f"Token-optimized voting complete: {winning_decision} wins with efficiency {winning_score:.3f}/{total_efficiency:.3f}"
        )
        
        return VotingResult(
            winning_decision=winning_decision,
            strategy_used="token_optimized",
            vote_breakdown=vote_breakdown,
            confidence=confidence,
            total_models=len(model_responses),
            metadata={
                "avg_efficiency": total_efficiency / len(model_responses),
                "total_tokens": sum(v['tokens'] for v in model_efficiency.values()),
                "avg_quality": sum(v['quality'] for v in model_efficiency.values()) / len(model_efficiency)
            }
        )


class ConsensusVoter:
    """
    Main interface for consensus voting.
    
    Provides a unified interface to apply different voting strategies
    and compare their results.
    """
    
    def __init__(self, analytics=None):
        """
        Initialize consensus voter.
        
        Args:
            analytics: Optional ZenAnalytics instance for logging voting results
        """
        self.analytics = analytics
        self.strategies = {
            VotingStrategy.DEMOCRATIC: DemocraticVoting(),
            VotingStrategy.QUALITY_WEIGHTED: QualityWeightedVoting(),
            VotingStrategy.TOKEN_OPTIMIZED: TokenOptimizedVoting(),
        }
    
    def vote(
        self,
        model_responses: List[Dict[str, Any]],
        strategy: VotingStrategy = VotingStrategy.DEMOCRATIC
    ) -> VotingResult:
        """
        Apply a voting strategy to determine the consensus decision.
        
        Args:
            model_responses: List of model response dictionaries
            strategy: Voting strategy to use
            
        Returns:
            VotingResult with winning decision and metadata
        """
        if strategy not in self.strategies:
            logger.warning(f"Unknown strategy {strategy}, defaulting to democratic")
            strategy = VotingStrategy.DEMOCRATIC
        
        result = self.strategies[strategy].vote(model_responses)
        
        # Log to analytics if available
        if self.analytics:
            try:
                self._log_to_analytics(result, model_responses)
            except Exception as e:
                logger.warning(f"Failed to log voting result to analytics: {e}")
        
        return result
    
    def compare_strategies(
        self,
        model_responses: List[Dict[str, Any]]
    ) -> Dict[str, VotingResult]:
        """
        Compare all voting strategies on the same model responses.
        
        Args:
            model_responses: List of model response dictionaries
            
        Returns:
            Dictionary mapping strategy names to their VotingResults
        """
        results = {}
        
        for strategy in VotingStrategy:
            results[strategy.value] = self.vote(model_responses, strategy)
        
        # Log comparison if analytics available
        if self.analytics:
            try:
                self._log_strategy_comparison(results, model_responses)
            except Exception as e:
                logger.warning(f"Failed to log strategy comparison: {e}")
        
        return results
    
    def _log_to_analytics(self, result: VotingResult, model_responses: List[Dict[str, Any]]):
        """Log voting result to analytics"""
        if not self.analytics:
            return
        
        try:
            # Log as a routing decision (voting is a type of routing)
            self.analytics.log_routing_decision(
                user_intent="consensus_voting",
                chosen_tool=result.winning_decision,
                chosen_strategy=result.strategy_used,
                detected_complexity=len(model_responses),
                detected_risk=int((1 - result.confidence) * 10),
                outcome="success",
                metadata={
                    "vote_breakdown": result.vote_breakdown,
                    "confidence": result.confidence,
                    "total_models": result.total_models,
                    **result.metadata
                }
            )
        except Exception as e:
            logger.error(f"Error logging to analytics: {e}")
    
    def _log_strategy_comparison(self, results: Dict[str, VotingResult], model_responses: List[Dict[str, Any]]):
        """Log strategy comparison to analytics"""
        if not self.analytics:
            return
        
        try:
            comparison_data = {
                "strategies_compared": list(results.keys()),
                "model_count": len(model_responses),
                "decisions": {k: v.winning_decision for k, v in results.items()},
                "confidences": {k: v.confidence for k, v in results.items()},
                "agreement": len(set(v.winning_decision for v in results.values())) == 1
            }
            
            self.analytics.log_routing_decision(
                user_intent="voting_strategy_comparison",
                chosen_tool="consensus",
                chosen_strategy="comparison",
                detected_complexity=len(model_responses),
                detected_risk=5,
                outcome="success",
                metadata=comparison_data
            )
        except Exception as e:
            logger.error(f"Error logging comparison: {e}")

