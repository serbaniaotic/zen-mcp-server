"""
Constitution Loader for Vibe Check Integration
Loads rules from tamdac/CONSTITUTION.md and converts to Vibe Check format
"""

import os
import re
from typing import List, Dict
from pathlib import Path

def load_constitution(constitution_path: str = None) -> Dict[str, List[str]]:
    """
    Load constitution from tamdac/CONSTITUTION.md
    
    Args:
        constitution_path: Optional path to constitution file
        
    Returns:
        Dictionary with 'principles' and 'rules' lists
    """
    if constitution_path is None:
        # Try to find tamdac/CONSTITUTION.md relative to this file
        current_dir = Path(__file__).parent.parent.parent
        constitution_path = current_dir / "tamdac" / "CONSTITUTION.md"
    
    if not os.path.exists(constitution_path):
        # Return default rules if constitution not found
        return {
            "principles": [
                "This is a PERSONAL tool, not a SaaS product",
                "No marketplace language (library, discovery, suggestions)",
                "CLI is sufficient - defer elaborate UI",
                "Prioritize intelligence over interface",
                "Check against vibe-coded essence: 'Find hope in knowledge and grace in wisdom'"
            ],
            "rules": []
        }
    
    with open(constitution_path, 'r') as f:
        content = f.read()
    
    principles = []
    rules = []
    
    # Extract principles (lines starting with ## or ### followed by principle-like text)
    principle_pattern = r'^#{2,3}\s+(.+)$'
    for match in re.finditer(principle_pattern, content, re.MULTILINE):
        principle = match.group(1).strip()
        # Filter out section headers
        if not any(skip in principle.lower() for skip in ['table of contents', 'overview', 'summary', 'version']):
            principles.append(principle)
    
    # Extract rules (lines starting with - or * that look like rules/constraints)
    rule_pattern = r'^[\-\*]\s+(.+)$'
    for match in re.finditer(rule_pattern, content, re.MULTILINE):
        rule = match.group(1).strip()
        # Filter for actionable rules
        if any(keyword in rule.lower() for keyword in ['must', 'should', 'never', 'always', 'no ', 'don\'t']):
            rules.append(rule)
    
    # If no rules extracted, create from principles
    if not rules and principles:
        rules = [f"Follow principle: {p}" for p in principles[:5]]  # Top 5
    
    return {
        "principles": principles[:10],  # Limit to top 10 principles
        "rules": rules[:15]  # Limit to top 15 rules
    }


def format_for_vibe_check(constitution: Dict[str, List[str]], session_type: str = "default") -> List[str]:
    """
    Format constitution for Vibe Check session rules
    
    Args:
        constitution: Dictionary with principles and rules
        session_type: Type of session (default, ticket, refactor, etc.)
        
    Returns:
        List of formatted rules for Vibe Check
    """
    formatted_rules = []
    
    # Add core principles
    if constitution.get("principles"):
        formatted_rules.append("=== Core Principles ===")
        for principle in constitution["principles"][:5]:  # Top 5 principles
            formatted_rules.append(f"• {principle}")
    
    # Add specific rules
    if constitution.get("rules"):
        formatted_rules.append("=== Specific Rules ===")
        for rule in constitution["rules"][:10]:  # Top 10 rules
            formatted_rules.append(f"• {rule}")
    
    # Add session-specific rules
    if session_type == "ticket":
        formatted_rules.extend([
            "=== Ticket Work Rules ===",
            "• Document all decisions in ticket evidence",
            "• Update ticket status after major milestones",
            "• Validate against ticket scope before expanding"
        ])
    elif session_type == "refactor":
        formatted_rules.extend([
            "=== Refactoring Rules ===",
            "• Test before and after changes",
            "• Preserve existing behavior unless explicitly changing it",
            "• Don't mix refactoring with feature additions"
        ])
    
    return formatted_rules


# Example usage in zen-mcp tools
def get_session_constitution(session_id: str, session_type: str = "default") -> List[str]:
    """
    Get constitution rules for a session
    
    Args:
        session_id: Session identifier
        session_type: Type of session for context-specific rules
        
    Returns:
        List of rules formatted for Vibe Check
    """
    constitution = load_constitution()
    return format_for_vibe_check(constitution, session_type)






