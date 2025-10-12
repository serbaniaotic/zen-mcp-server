"""
Intelligent Router for Zen MCP Server.

Automatically selects optimal tools based on:
- Task complexity analysis
- Risk assessment
- Historical performance patterns
- Natural language intent detection
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Routing strategies inspired by Agent-Fusion"""
    SOLO = "SOLO"              # Single tool execution
    CONSENSUS = "CONSENSUS"    # Multi-model consensus
    SEQUENTIAL = "SEQUENTIAL"  # Step-by-step investigation
    PARALLEL = "PARALLEL"      # Multiple tools in parallel


@dataclass
class RoutingDecision:
    """Result of intelligent routing"""
    tool: str
    strategy: RoutingStrategy
    complexity: int  # 1-10
    risk: int        # 1-10
    confidence: float  # 0.0-1.0
    intent: str
    reasoning: str
    alternative_tools: List[str]
    metadata: Dict


class IntelligentRouter:
    """
    Intelligent routing engine that automatically selects optimal tools
    based on task characteristics and historical performance.
    """
    
    # Tool definitions with capabilities
    TOOL_CAPABILITIES = {
        "chat": {
            "strategies": [RoutingStrategy.SOLO],
            "max_complexity": 6,
            "best_for": ["general", "simple", "quick"],
            "description": "General-purpose conversational AI"
        },
        "thinkdeep": {
            "strategies": [RoutingStrategy.SEQUENTIAL],
            "max_complexity": 10,
            "best_for": ["investigation", "analysis", "complex", "research"],
            "description": "Multi-stage investigation and reasoning"
        },
        "debug": {
            "strategies": [RoutingStrategy.SEQUENTIAL],
            "max_complexity": 9,
            "best_for": ["bug", "error", "issue", "problem", "troubleshoot"],
            "description": "Systematic debugging and root cause analysis"
        },
        "codereview": {
            "strategies": [RoutingStrategy.SOLO, RoutingStrategy.SEQUENTIAL],
            "max_complexity": 8,
            "best_for": ["review", "audit", "check", "validate", "quality"],
            "description": "Code review with quality and security checks"
        },
        "consensus": {
            "strategies": [RoutingStrategy.CONSENSUS],
            "max_complexity": 10,
            "best_for": ["decision", "critical", "important", "choose", "evaluate"],
            "description": "Multi-model consensus for critical decisions"
        },
        "planner": {
            "strategies": [RoutingStrategy.SEQUENTIAL],
            "max_complexity": 9,
            "best_for": ["plan", "design", "architecture", "strategy"],
            "description": "Interactive planning and design"
        },
        "precommit": {
            "strategies": [RoutingStrategy.SEQUENTIAL],
            "max_complexity": 8,
            "best_for": ["commit", "validate", "changes", "git"],
            "description": "Git changes validation before commit"
        },
    }
    
    # Complexity indicators (each adds to complexity score)
    COMPLEXITY_INDICATORS = {
        "multiple_files": 1,        # Multiple files involved
        "cross_domain": 2,          # Spans multiple domains (frontend, backend, etc.)
        "architecture": 2,          # Architectural decisions
        "performance": 1,           # Performance optimization
        "security": 2,              # Security considerations
        "refactoring": 1,           # Code refactoring
        "legacy_code": 1,           # Working with legacy code
        "integration": 2,           # System integration
        "distributed": 2,           # Distributed systems
        "concurrency": 2,           # Concurrency/threading
        "database": 1,              # Database operations
        "api_design": 1,            # API design
        "microservices": 2,         # Microservices architecture
        "synchronization": 2,       # Data synchronization
    }
    
    # Risk indicators (each adds to risk score)
    RISK_INDICATORS = {
        "production": 3,            # Production environment
        "critical": 4,              # Critical system
        "security": 4,              # Security implications
        "data_loss": 5,             # Potential data loss
        "breaking": 3,              # Breaking changes
        "irreversible": 4,          # Irreversible operations
        "payment": 4,               # Payment processing
        "auth": 3,                  # Authentication/authorization
        "privacy": 4,               # Privacy concerns
        "compliance": 3,            # Compliance requirements
        "migration": 3,             # Data migration
        "deployment": 2,            # Deployment changes
    }
    
    # Intent categories with keywords
    INTENT_PATTERNS = {
        "review": [
            r"\b(review|check|audit|validate|inspect|examine)\b",
            r"\b(code review|pull request|pr review)\b",
        ],
        "debug": [
            r"\b(bug|error|issue|problem|fix|broken|crash|fail|leak)\b",
            r"\b(not working|doesn't work|won't work)\b",
            r"\b(debug|troubleshoot)\b",
        ],
        "investigate": [
            r"\b(investigate|research|explore|analyze)\b",
            r"\b(find out|figure out|understand why)\b",
        ],
        "design": [
            r"\b(design|architect|plan|structure|organize)\b",
            r"\b(how should|what's the best way)\b",
        ],
        "implement": [
            r"\b(implement|build|create|develop|code|write)\b",
            r"\b(add feature|new feature)\b",
        ],
        "optimize": [
            r"\b(optimize|improve|enhance|speed up|faster)\b",
        ],
        "decide": [
            r"\b(decide|choose|select|pick|should I|should we)\b",
            r"\b(versus|vs\.| or )\b",
        ],
        "understand": [
            r"\b(understand|explain|how does|what is|why|difference between)\b",
            r"\b(tell me about|learn)\b",
        ],
    }

    def __init__(self, analytics=None):
        """
        Initialize intelligent router.
        
        Args:
            analytics: Optional ZenAnalytics instance for historical patterns
        """
        self.analytics = analytics
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for router"""
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
    
    def route_request(
        self,
        user_query: str,
        context: Optional[Dict] = None,
        files: Optional[List[str]] = None,
        override_tool: Optional[str] = None,
        override_strategy: Optional[str] = None,
    ) -> RoutingDecision:
        """
        Route a user request to the optimal tool and strategy.
        
        Args:
            user_query: User's natural language query
            context: Optional context dictionary
            files: Optional list of files involved
            override_tool: Optional manual tool override
            override_strategy: Optional manual strategy override
            
        Returns:
            RoutingDecision with tool, strategy, and metadata
        """
        context = context or {}
        files = files or []
        
        # Analyze request characteristics
        complexity = self._analyze_complexity(user_query, context, files)
        risk = self._assess_risk(user_query, context)
        intent = self._extract_intent(user_query)
        
        logger.info(
            f"Routing analysis - Intent: {intent}, "
            f"Complexity: {complexity}/10, Risk: {risk}/10"
        )
        
        # Check for manual overrides
        if override_tool:
            tool = override_tool
            strategy = self._get_tool_strategy(tool, override_strategy)
            reasoning = f"Manual override to {tool}"
            confidence = 1.0
        else:
            # Use intelligent routing
            tool, strategy, reasoning, confidence = self._select_tool(
                user_query, intent, complexity, risk
            )
        
        # Get alternatives
        alternatives = self._get_alternative_tools(intent, complexity, risk, exclude=tool)
        
        # Create routing decision
        decision = RoutingDecision(
            tool=tool,
            strategy=strategy,
            complexity=complexity,
            risk=risk,
            confidence=confidence,
            intent=intent,
            reasoning=reasoning,
            alternative_tools=alternatives,
            metadata={
                "user_query": user_query[:200],
                "file_count": len(files),
                "context_keys": list(context.keys()),
            }
        )
        
        logger.info(
            f"Routing decision - Tool: {tool}, Strategy: {strategy.value}, "
            f"Confidence: {confidence:.2f}"
        )
        
        return decision
    
    def _analyze_complexity(
        self,
        user_query: str,
        context: Dict,
        files: List[str]
    ) -> int:
        """
        Analyze task complexity (1-10 scale).
        
        Args:
            user_query: User's query
            context: Context dictionary
            files: List of files involved
            
        Returns:
            Complexity score (1-10)
        """
        complexity = 1  # Base complexity
        query_lower = user_query.lower()
        
        # Check complexity indicators
        for indicator, score in self.COMPLEXITY_INDICATORS.items():
            if indicator.replace("_", " ") in query_lower:
                complexity += score
        
        # File count factor
        if len(files) > 10:
            complexity += 3
        elif len(files) > 5:
            complexity += 2
        elif len(files) > 1:
            complexity += 1
        
        # Query length factor (longer queries often more complex)
        if len(user_query) > 500:
            complexity += 2
        elif len(user_query) > 200:
            complexity += 1
        
        # Context complexity
        if context.get("multi_step"):
            complexity += 2
        if context.get("dependencies"):
            complexity += 1
        
        # Check for multiple questions
        question_count = user_query.count("?")
        if question_count > 2:
            complexity += 1
        
        # Check for lists/enumerations (often indicates complexity)
        if re.search(r"\d+\.", user_query):  # Numbered lists
            complexity += 1
        
        # Cap at 10
        return min(complexity, 10)
    
    def _assess_risk(self, user_query: str, context: Dict) -> int:
        """
        Assess task risk level (1-10 scale).
        
        Args:
            user_query: User's query
            context: Context dictionary
            
        Returns:
            Risk score (1-10)
        """
        risk = 1  # Base risk
        query_lower = user_query.lower()
        
        # Check risk indicators
        for indicator, score in self.RISK_INDICATORS.items():
            if indicator.replace("_", " ") in query_lower:
                risk += score
        
        # Environment risk
        if context.get("environment") == "production":
            risk += 3
        elif context.get("environment") == "staging":
            risk += 1
        
        # Urgency indicator
        if any(word in query_lower for word in ["urgent", "critical", "asap", "emergency"]):
            risk += 2
        
        # Negation words often indicate problems (higher risk)
        if any(word in query_lower for word in ["don't", "doesn't", "won't", "can't", "not working"]):
            risk += 1
        
        # Cap at 10
        return min(risk, 10)
    
    def _extract_intent(self, user_query: str) -> str:
        """
        Extract user intent from natural language query.
        
        Args:
            user_query: User's query
            
        Returns:
            Intent category (review, debug, design, implement, etc.)
        """
        query_lower = user_query.lower()
        
        # Track matches for each intent
        intent_scores: Dict[str, int] = {}
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, query_lower, re.IGNORECASE)
                score += len(matches)
            
            if score > 0:
                intent_scores[intent] = score
        
        # Return intent with highest score
        if intent_scores:
            return max(intent_scores.items(), key=lambda x: x[1])[0]
        
        # Default to general if no clear intent
        return "general"
    
    def _select_tool(
        self,
        user_query: str,
        intent: str,
        complexity: int,
        risk: int
    ) -> Tuple[str, RoutingStrategy, str, float]:
        """
        Select the best tool based on analysis.
        
        Args:
            user_query: User's query
            intent: Extracted intent
            complexity: Complexity score
            risk: Risk score
            
        Returns:
            Tuple of (tool, strategy, reasoning, confidence)
        """
        # Priority 1: High risk -> Consensus
        if risk >= 8:
            return (
                "consensus",
                RoutingStrategy.CONSENSUS,
                f"High risk ({risk}/10) requires multi-model consensus",
                0.95
            )
        
        # Priority 2: Check historical patterns
        if self.analytics:
            try:
                recommendation = self.analytics.get_best_tool_for(
                    intent=intent,
                    complexity=complexity,
                    risk=risk,
                    days=30
                )
                
                if recommendation and recommendation["success_rate"] >= 0.7:
                    tool = recommendation["tool"]
                    strategy = RoutingStrategy[recommendation["strategy"]]
                    reasoning = (
                        f"Historical data suggests {tool} "
                        f"(success rate: {recommendation['success_rate']:.1%}, "
                        f"used {recommendation['usage_count']} times)"
                    )
                    confidence = recommendation["success_rate"]
                    
                    return (tool, strategy, reasoning, confidence)
            except Exception as e:
                logger.warning(f"Failed to get historical recommendation: {e}")
        
        # Priority 3: Match intent to tool capabilities
        best_tool = None
        best_score = 0
        
        for tool, capabilities in self.TOOL_CAPABILITIES.items():
            score = 0
            
            # Check if tool can handle complexity
            if complexity > capabilities["max_complexity"]:
                continue
            
            # Check intent match
            for keyword in capabilities["best_for"]:
                if keyword in intent or keyword in user_query.lower():
                    score += 5
            
            # Prefer simpler tools for simpler tasks
            if complexity <= 4 and tool == "chat":
                score += 3
            
            if score > best_score:
                best_score = score
                best_tool = tool
        
        # Priority 4: Complexity-based routing
        if not best_tool:
            if complexity >= 8:
                best_tool = "thinkdeep"
            elif complexity >= 6:
                best_tool = "planner"
            elif risk >= 6:
                best_tool = "consensus"
            else:
                best_tool = "chat"
        
        # Get strategy for selected tool
        strategy = self._get_tool_strategy(best_tool)
        
        # Calculate confidence
        confidence = 0.7 if best_score > 0 else 0.5
        
        reasoning = self._generate_reasoning(best_tool, intent, complexity, risk)
        
        return (best_tool, strategy, reasoning, confidence)
    
    def _get_tool_strategy(
        self,
        tool: str,
        override: Optional[str] = None
    ) -> RoutingStrategy:
        """Get the routing strategy for a tool"""
        if override:
            try:
                return RoutingStrategy[override.upper()]
            except KeyError:
                logger.warning(f"Invalid strategy override: {override}")
        
        capabilities = self.TOOL_CAPABILITIES.get(tool, {})
        strategies = capabilities.get("strategies", [RoutingStrategy.SOLO])
        return strategies[0]  # Use first/default strategy
    
    def _get_alternative_tools(
        self,
        intent: str,
        complexity: int,
        risk: int,
        exclude: str
    ) -> List[str]:
        """Get alternative tool suggestions"""
        alternatives = []
        
        for tool, capabilities in self.TOOL_CAPABILITIES.items():
            if tool == exclude:
                continue
            
            # Check if tool can handle the task
            if complexity > capabilities["max_complexity"]:
                continue
            
            # Check intent match
            for keyword in capabilities["best_for"]:
                if keyword in intent:
                    alternatives.append(tool)
                    break
        
        return alternatives[:3]  # Return top 3 alternatives
    
    def _generate_reasoning(
        self,
        tool: str,
        intent: str,
        complexity: int,
        risk: int
    ) -> str:
        """Generate human-readable reasoning for the routing decision"""
        capabilities = self.TOOL_CAPABILITIES.get(tool, {})
        description = capabilities.get("description", tool)
        
        reasons = [f"Selected {tool}: {description}"]
        
        if complexity >= 7:
            reasons.append(f"High complexity ({complexity}/10) requires systematic approach")
        elif complexity <= 3:
            reasons.append(f"Low complexity ({complexity}/10) allows quick response")
        
        if risk >= 6:
            reasons.append(f"Elevated risk ({risk}/10) requires careful analysis")
        
        if intent != "general":
            reasons.append(f"Intent matches '{intent}' use case")
        
        return ". ".join(reasons)
    
    def get_routing_suggestion(
        self,
        user_query: str,
        context: Optional[Dict] = None,
        files: Optional[List[str]] = None,
    ) -> str:
        """
        Get a human-readable routing suggestion.
        
        Args:
            user_query: User's query
            context: Optional context
            files: Optional file list
            
        Returns:
            Human-readable suggestion string
        """
        decision = self.route_request(user_query, context, files)
        
        suggestion = f"""
🎯 Routing Suggestion:
   Tool: {decision.tool}
   Strategy: {decision.strategy.value}
   Confidence: {decision.confidence:.0%}
   
📊 Analysis:
   Complexity: {decision.complexity}/10
   Risk: {decision.risk}/10
   Intent: {decision.intent}
   
💡 Reasoning:
   {decision.reasoning}
"""
        
        if decision.alternative_tools:
            alternatives = ", ".join(decision.alternative_tools)
            suggestion += f"\n🔄 Alternatives: {alternatives}"
        
        return suggestion.strip()

