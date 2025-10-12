#!/usr/bin/env python3
"""
Demo script for Voting Strategies in Consensus Tool.
Shows how different voting strategies produce different outcomes.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.voting_strategies import ConsensusVoter, VotingStrategy


def create_scenario_1():
    """Scenario 1: Clear consensus across all models"""
    return {
        "title": "Clear Consensus - All Models Agree",
        "question": "Should we upgrade to Python 3.12?",
        "responses": [
            {
                "model": "gpt-5",
                "stance": "for",
                "verdict": (
                    "Strong recommendation to upgrade. Python 3.12 offers significant performance "
                    "improvements (10-60% faster), better error messages, and enhanced type hints. "
                    "The migration path is straightforward with comprehensive documentation. "
                    "Risks are minimal as we're already on 3.11."
                ),
                "tokens_used": 100,
            },
            {
                "model": "claude-3.5-sonnet",
                "stance": "for",
                "verdict": (
                    "I recommend proceeding with the upgrade. The benefits include improved "
                    "performance and new language features. Migration should be straightforward."
                ),
                "tokens_used": 60,
            },
            {
                "model": "gemini-2.5-pro",
                "stance": "for",
                "verdict": (
                    "Approve this upgrade. Python 3.12 is production-ready and widely adopted. "
                    "The performance gains alone justify the upgrade effort."
                ),
                "tokens_used": 50,
            },
        ]
    }


def create_scenario_2():
    """Scenario 2: Split decision with quality difference"""
    return {
        "title": "Split Decision - Quality Matters",
        "question": "Should we rewrite our API in Rust?",
        "responses": [
            {
                "model": "gpt-5",
                "stance": "against",
                "verdict": (
                    "I advise against a full rewrite at this time. First, the current Python API "
                    "is stable and well-tested. Second, team expertise is primarily in Python. "
                    "Third, a rewrite would take 6-9 months with high risk of introducing bugs. "
                    "Fourth, the performance gains (2-3x) don't justify the cost and risk. "
                    "Instead, I recommend: 1) Profile and optimize hot paths in Python, "
                    "2) Consider Rust for specific performance-critical microservices, "
                    "3) Gradually introduce Rust where it provides clear value. "
                    "Evidence: Similar projects that did full rewrites experienced 40% schedule "
                    "overruns and 3-6 month feature freezes."
                ),
                "tokens_used": 200,
            },
            {
                "model": "gemini-2.5-pro",
                "stance": "for",
                "verdict": (
                    "The performance benefits of Rust make this worthwhile. We should proceed."
                ),
                "tokens_used": 30,
            },
            {
                "model": "claude-3.5-sonnet",
                "stance": "against",
                "verdict": (
                    "A full rewrite is too risky. The Python API works well and is maintainable. "
                    "Consider incremental improvements instead."
                ),
                "tokens_used": 50,
            },
            {
                "model": "o3-pro",
                "stance": "for",
                "verdict": "Rust is faster. Do it.",
                "tokens_used": 15,
            },
        ]
    }


def create_scenario_3():
    """Scenario 3: Token optimization matters"""
    return {
        "title": "Token Efficiency - Conciseness Wins",
        "question": "Should we enable two-factor authentication?",
        "responses": [
            {
                "model": "gpt-5",
                "stance": "for",
                "verdict": (
                    "I strongly recommend implementing two-factor authentication (2FA) for your application. "
                    "Here's a comprehensive analysis of why this is crucial:\n\n"
                    "**Security Benefits:**\n"
                    "1. Reduces account takeover risk by 99.9% according to Microsoft research\n"
                    "2. Protects against password breaches and credential stuffing attacks\n"
                    "3. Adds defense-in-depth layer following security best practices\n"
                    "4. Meets compliance requirements for SOC 2, ISO 27001, and GDPR\n\n"
                    "**Implementation Considerations:**\n"
                    "- Use TOTP (Time-based One-Time Passwords) as primary method\n"
                    "- Offer SMS as backup (despite known vulnerabilities)\n"
                    "- Provide recovery codes for account access\n"
                    "- Consider hardware tokens for high-privilege accounts\n\n"
                    "**User Experience:**\n"
                    "- Initial friction offset by long-term security benefits\n"
                    "- Remember-me options for trusted devices\n"
                    "- Clear onboarding flow reduces support tickets\n\n"
                    "**Cost Analysis:**\n"
                    "Implementation: $5,000-10,000\n"
                    "Maintenance: $500/month\n"
                    "ROI: Prevention of single breach ($50,000+ average) justifies investment\n\n"
                    "This is a high-priority security enhancement with proven effectiveness."
                ),
                "tokens_used": 350,
            },
            {
                "model": "claude-3.5-sonnet",
                "stance": "for",
                "verdict": (
                    "Implement 2FA immediately. It's a security requirement that prevents 99.9% of "
                    "automated attacks. Use TOTP with SMS backup. Low cost, high value."
                ),
                "tokens_used": 60,
            },
            {
                "model": "gemini-2.5-pro",
                "stance": "for",
                "verdict": (
                    "Yes, enable 2FA. Critical security feature, industry standard, easy to implement."
                ),
                "tokens_used": 30,
            },
        ]
    }


def create_scenario_4():
    """Scenario 4: Tie-breaking scenario"""
    return {
        "title": "Tie Situation - Default to Conditional",
        "question": "Should we migrate to Kubernetes now?",
        "responses": [
            {
                "model": "gpt-5",
                "stance": "for",
                "verdict": (
                    "Kubernetes provides excellent scalability and is industry standard for "
                    "container orchestration. I recommend proceeding with migration."
                ),
                "tokens_used": 80,
            },
            {
                "model": "claude-3.5-sonnet",
                "stance": "against",
                "verdict": (
                    "The current infrastructure is stable. Kubernetes adds significant complexity. "
                    "Consider whether the benefits justify the operational overhead."
                ),
                "tokens_used": 70,
            },
        ]
    }


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def print_subheader(text):
    """Print a formatted subheader"""
    print(f"\n{text}")
    print("-" * 70)


def run_scenario(scenario_data):
    """Run a voting scenario and display results"""
    print_header(f"SCENARIO: {scenario_data['title']}")
    print(f"\nQuestion: {scenario_data['question']}")
    print(f"Models consulted: {len(scenario_data['responses'])}")
    
    # Show model responses
    print_subheader("Model Responses")
    for i, response in enumerate(scenario_data['responses'], 1):
        print(f"\n{i}. {response['model']} ({response['stance']}):")
        verdict_preview = response['verdict'][:150] + "..." if len(response['verdict']) > 150 else response['verdict']
        print(f"   {verdict_preview}")
        print(f"   Tokens: {response['tokens_used']}")
    
    # Compare voting strategies
    voter = ConsensusVoter()
    results = voter.compare_strategies(scenario_data['responses'])
    
    print_subheader("Voting Results Comparison")
    
    print(f"\n{'Strategy':<25} {'Decision':<15} {'Confidence':<12} {'Key Insight'}")
    print("-" * 90)
    
    for strategy_name, result in results.items():
        key_insight = ""
        
        if strategy_name == "democratic":
            votes = result.vote_breakdown.get("votes_by_decision", {})
            key_insight = f"Votes: {votes}"
        elif strategy_name == "quality_weighted":
            key_insight = f"Weighted by reasoning quality"
        elif strategy_name == "token_optimized":
            total_tokens = result.metadata.get("total_tokens", 0)
            key_insight = f"Total tokens: {total_tokens}"
        
        print(f"{strategy_name:<25} {result.winning_decision:<15} {result.confidence:<12.2%} {key_insight}")
    
    # Check for agreement
    print_subheader("Analysis")
    
    decisions = set(r.winning_decision for r in results.values())
    confidences = {name: r.confidence for name, r in results.items()}
    
    if len(decisions) == 1:
        decision = decisions.pop()
        print(f"\n✅ All strategies agree: {decision}")
        print(f"   This indicates strong consensus regardless of weighting method.")
    else:
        print(f"\n📊 Strategies produce different results: {decisions}")
        print(f"   This highlights how voting method affects outcomes!")
        
        # Show which strategy is most confident
        most_confident = max(confidences.items(), key=lambda x: x[1])
        print(f"\n   Most confident: {most_confident[0]} at {most_confident[1]:.2%}")
    
    # Recommendation
    print(f"\n💡 Recommendation:")
    
    if scenario_data['title'].startswith("Clear Consensus"):
        print(f"   When all models agree, any strategy works.")
        print(f"   Use democratic voting for simplicity.")
    
    elif scenario_data['title'].startswith("Split Decision"):
        print(f"   When models disagree, quality-weighted voting")
        print(f"   gives more weight to well-reasoned arguments.")
        print(f"   Notice how brief responses have less impact.")
    
    elif scenario_data['title'].startswith("Token Efficiency"):
        print(f"   Token-optimized voting rewards conciseness.")
        print(f"   Useful when token costs are a concern or when")
        print(f"   you want to avoid verbose but shallow analysis.")
    
    elif scenario_data['title'].startswith("Tie"):
        print(f"   Democratic voting defaults to 'conditional' on ties.")
        print(f"   Quality/token-weighted can break ties by considering")
        print(f"   the strength and efficiency of arguments.")


def main():
    """Run all voting strategy demos"""
    print("\n" + "=" * 70)
    print("VOTING STRATEGIES DEMONSTRATION")
    print("Zen MCP Server - Phase 4")
    print("=" * 70)
    
    print("\nThis demo shows how different voting strategies produce different")
    print("outcomes when synthesizing consensus from multiple AI models.")
    
    scenarios = [
        create_scenario_1(),
        create_scenario_2(),
        create_scenario_3(),
        create_scenario_4(),
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        run_scenario(scenario)
        
        if i < len(scenarios):
            input("\n\nPress Enter to continue to next scenario...")
    
    # Final summary
    print_header("SUMMARY: Choosing the Right Voting Strategy")
    
    print("\n📋 Strategy Guide:\n")
    
    print("1. DEMOCRATIC VOTING (one model, one vote)")
    print("   ✓ Use when: All models are equally trusted")
    print("   ✓ Use when: Simple majority is desired")
    print("   ✓ Pros: Simple, transparent, fair")
    print("   ✓ Cons: Ignores reasoning quality")
    print()
    
    print("2. QUALITY-WEIGHTED VOTING (weighted by reasoning quality)")
    print("   ✓ Use when: Reasoning depth matters more than vote count")
    print("   ✓ Use when: Some models provide better analysis")
    print("   ✓ Pros: Rewards thorough, evidence-based arguments")
    print("   ✓ Cons: Quality assessment is heuristic-based")
    print()
    
    print("3. TOKEN-OPTIMIZED VOTING (quality per token)")
    print("   ✓ Use when: Token costs are a concern")
    print("   ✓ Use when: Conciseness is valued")
    print("   ✓ Pros: Rewards efficient, high-quality responses")
    print("   ✓ Cons: May undervalue comprehensive analysis")
    print()
    
    print("💡 General Recommendations:")
    print("   • Use democratic for straightforward decisions")
    print("   • Use quality-weighted for complex technical decisions")
    print("   • Use token-optimized when managing API costs")
    print("   • Compare all three when the decision is critical")
    print()
    
    print("🎯 Integration:")
    print("   These voting strategies can be used independently or")
    print("   integrated into the consensus tool workflow to automatically")
    print("   synthesize final decisions from multi-model consultations.")
    
    print("\n" + "=" * 70)
    print("✅ Demo Complete!")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

