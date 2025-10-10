"""
Vibe Check MCP Integration Tool
Provides metacognitive oversight for AI agents via CPI (Chain-Pattern Interrupt)
"""

import requests
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class VibeCheckTool:
    """Integration with Vibe Check MCP server for agent oversight"""
    
    def __init__(self, vibe_check_url: str = "http://localhost:3000"):
        """
        Initialize Vibe Check integration
        
        Args:
            vibe_check_url: URL of Vibe Check MCP server
        """
        self.vibe_check_url = vibe_check_url
        self.session = requests.Session()
    
    def vibe_check(
        self,
        goal: str,
        plan: str,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
        status: str = "planning",
        progress: Optional[str] = None,
        model_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call vibe_check to get metacognitive feedback
        
        Args:
            goal: What the agent is trying to accomplish
            plan: Current plan/approach
            context: Additional context about the task
            session_id: Optional session ID for history continuity
            status: Current status (planning, implementing, reviewing)
            progress: Optional progress description
            model_override: Optional model to use instead of default
            
        Returns:
            Dictionary with questions, recommendations, and risk_level
        """
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "vibe_check",
                    "arguments": {
                        "goal": goal,
                        "plan": plan,
                        "status": status
                    }
                }
            }
            
            # Add optional parameters
            if context:
                payload["params"]["arguments"]["context"] = context
            if session_id:
                payload["params"]["arguments"]["sessionId"] = session_id
            if progress:
                payload["params"]["arguments"]["progress"] = progress
            if model_override:
                payload["params"]["arguments"]["model"] = model_override
            
            logger.info(f"Calling vibe_check for session: {session_id or 'default'}")
            
            response = self.session.post(
                self.vibe_check_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "result" in result:
                content = result["result"]["content"]
                # Parse the response
                if isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get("text", "")
                    
                    # Extract questions and recommendations
                    lines = text_content.split("\n")
                    questions = []
                    recommendations = []
                    risk_level = "medium"
                    
                    current_section = None
                    for line in lines:
                        line = line.strip()
                        if "question" in line.lower() or line.startswith("?"):
                            current_section = "questions"
                        elif "recommend" in line.lower() or "suggest" in line.lower():
                            current_section = "recommendations"
                        elif "risk" in line.lower() and ("high" in line.lower() or "low" in line.lower()):
                            if "high" in line.lower():
                                risk_level = "high"
                            elif "low" in line.lower():
                                risk_level = "low"
                        elif line and current_section == "questions":
                            questions.append(line)
                        elif line and current_section == "recommendations":
                            recommendations.append(line)
                    
                    return {
                        "questions": questions,
                        "recommendations": recommendations,
                        "risk_level": risk_level,
                        "raw_response": text_content
                    }
                
                return {
                    "questions": [],
                    "recommendations": [],
                    "risk_level": "medium",
                    "raw_response": str(content)
                }
            
            logger.error(f"Unexpected response format: {result}")
            return self._fallback_response()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Vibe Check request failed: {e}")
            return self._fallback_response()
        except Exception as e:
            logger.error(f"Vibe Check error: {e}")
            return self._fallback_response()
    
    def vibe_learn(
        self,
        mistake: str,
        fix: str,
        session_id: str,
        tags: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Log a mistake and fix for future learning
        
        Args:
            mistake: Description of what went wrong
            fix: Description of how it was fixed
            session_id: Session ID for tracking
            tags: Optional tags for categorization
            
        Returns:
            Confirmation dictionary
        """
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "vibe_learn",
                    "arguments": {
                        "mistake": mistake,
                        "fix": fix,
                        "sessionId": session_id
                    }
                }
            }
            
            if tags:
                payload["params"]["arguments"]["tags"] = tags
            
            logger.info(f"Logging learning entry for session: {session_id}")
            
            response = self.session.post(
                self.vibe_check_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                "status": "logged",
                "session_id": session_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Vibe Learn error: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def update_constitution(
        self,
        session_id: str,
        rules: list
    ) -> Dict[str, Any]:
        """
        Update or set session constitution rules
        
        Args:
            session_id: Session ID
            rules: List of rule strings
            
        Returns:
            Confirmation dictionary
        """
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "update_constitution",
                    "arguments": {
                        "sessionId": session_id,
                        "rules": rules
                    }
                }
            }
            
            logger.info(f"Updating constitution for session: {session_id}")
            
            response = self.session.post(
                self.vibe_check_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                "status": "updated",
                "session_id": session_id,
                "rules_count": len(rules),
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Update Constitution error: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _fallback_response(self) -> Dict[str, Any]:
        """Fallback response when Vibe Check is unavailable"""
        return {
            "questions": [
                "Is this approach aligned with the user's actual needs?",
                "Have you considered simpler alternatives?",
                "What are the potential risks or downsides?"
            ],
            "recommendations": [
                "Verify assumptions before proceeding",
                "Consider if this is the minimal viable solution"
            ],
            "risk_level": "medium",
            "raw_response": "Fallback response (Vibe Check unavailable)"
        }


# Singleton instance
_vibe_check_tool = None

def get_vibe_check_tool(vibe_check_url: str = None) -> VibeCheckTool:
    """Get or create VibeCheckTool instance"""
    global _vibe_check_tool
    
    if _vibe_check_tool is None:
        import os
        url = vibe_check_url or os.getenv("VIBE_CHECK_MCP_URL", "http://localhost:3000")
        _vibe_check_tool = VibeCheckTool(url)
    
    return _vibe_check_tool


















