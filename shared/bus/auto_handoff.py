"""
Auto-Handoff System for Workspace

Intelligently detects when an agent should handoff to another agent
based on task content, agent capabilities, and confidence scores.
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from shared.bus.message_bus import MessageBus, Message, MessageType
from shared.bus.handoff import handoff_manager, HandoffContext, HandoffStatus

logger = logging.getLogger(__name__)

class HandoffTrigger(Enum):
    SKILL_MISMATCH = "skill_mismatch"      # Task requires skills agent doesn't have
    CONFIDENCE_LOW = "confidence_low"      # Agent is unsure how to proceed
    SCOPE_CHANGE = "scope_change"          # Task evolved beyond original scope
    DELEGATION = "delegation"              # Sub-task should be handled by specialist
    COMPLETION = "completion"              # Agent finished their part
    ERROR_RECOVERY = "error_recovery"      # Agent failed, needs help

@dataclass
class HandoffRecommendation:
    """Recommendation for a handoff"""
    should_handoff: bool
    trigger: HandoffTrigger
    from_agent: str
    to_agent: str
    reason: str
    confidence: float  # 0.0 to 1.0
    context_summary: str

class AutoHandoffDetector:
    """
    Detects when agents should handoff work to other agents
    
    Analyzes:
    - Task content vs agent skills
    - Agent confidence in responses
    - Task completion state
    - Natural breakpoints in workflows
    """
    
    def __init__(self):
        self.bus = MessageBus()
        self.agent_skills = {}  # agent_id -> list of skills
        self.task_history = {}  # agent_id -> list of recent tasks
        
        # Subscribe to relevant events
        self.bus.subscribe(MessageType.TASK_COMPLETED, self._on_task_completed)
        self.bus.subscribe(MessageType.AGENT_MESSAGE, self._on_agent_message)
        
        logger.info("AutoHandoffDetector initialized")
    
    def register_agent_skills(self, agent_id: str, skills: List[str]):
        """Register an agent's skills for matching"""
        self.agent_skills[agent_id] = [s.lower() for s in skills]
    
    def analyze_for_handoff(
        self,
        agent_id: str,
        task_description: str,
        agent_response: str,
        mission_context: Optional[Dict] = None
    ) -> Optional[HandoffRecommendation]:
        """
        Analyze if agent should handoff to another agent
        
        Returns HandoffRecommendation if handoff recommended, None otherwise
        """
        agent_skills = self.agent_skills.get(agent_id, [])
        
        # Check 1: Skill mismatch
        # Look for keywords in task that don't match agent skills
        task_lower = task_description.lower()
        response_lower = agent_response.lower()
        
        # Detect low confidence indicators
        uncertainty_phrases = [
            "i'm not sure", "i don't know", "outside my expertise",
            "not my specialty", "you should ask", "i recommend consulting",
            "beyond my scope", "not qualified", "i can't help with"
        ]
        
        confidence_low = any(phrase in response_lower for phrase in uncertainty_phrases)
        
        if confidence_low:
            # Find best agent for this task
            best_agent = self._find_best_agent_for_task(task_description, exclude=[agent_id])
            if best_agent:
                return HandoffRecommendation(
                    should_handoff=True,
                    trigger=HandoffTrigger.CONFIDENCE_LOW,
                    from_agent=agent_id,
                    to_agent=best_agent,
                    reason="Agent expressed uncertainty about task",
                    confidence=0.85,
                    context_summary=task_description[:100]
                )
        
        # Check 2: Completion handoff patterns
        # Look for phrases indicating work is done and next phase needed
        completion_phrases = [
            "ready for", "next step is", "now you can", "hand this off to",
            "should be reviewed by", "needs to be implemented by",
            "pass this to", "over to", "next phase"
        ]
        
        completion_detected = any(phrase in response_lower for phrase in completion_phrases)
        
        if completion_detected:
            # Determine who should receive based on context
            next_agent = self._infer_next_agent(response_lower, agent_id)
            if next_agent:
                return HandoffRecommendation(
                    should_handoff=True,
                    trigger=HandoffTrigger.COMPLETION,
                    from_agent=agent_id,
                    to_agent=next_agent,
                    reason="Agent indicated work is ready for next phase",
                    confidence=0.75,
                    context_summary=task_description[:100]
                )
        
        # Check 3: Skill-based delegation
        # Look for tasks that clearly belong to another specialty
        skill_keywords = {
            "code": ["programming", "coding", "debugging", "refactor", "implement", "function", "api"],
            "hunter": ["outreach", "email", "sales", "prospect", "pitch", "campaign"],
            "pepper": ["email marketing", "campaign", "subject line", "open rate"],
            "quill": ["social media", "tweet", "linkedin", "post", "content"],
            "scout": ["research", "analyze competitors", "market research", "investigate"],
            "sage": ["data analysis", "sql", "metrics", "kpi", "dashboard", "analytics"],
            "shuri": ["product strategy", "roadmap", "prioritize", "user research"],
            "wong": ["documentation", "readme", "docs", "guide", "manual"],
            "guardian": ["test", "qa", "bug", "quality assurance", "testing"],
            "pixel": ["design", "ui", "ux", "mockup", "wireframe", "user interface"],
            "lingua": ["translate", "localization", "language", "multilingual"]
        }
        
        for agent_name, keywords in skill_keywords.items():
            if agent_name in agent_id.lower():
                continue  # Don't suggest handoff to self
            
            if any(kw in task_lower for kw in keywords):
                # Check if current agent has this skill
                has_skill = any(kw in ' '.join(agent_skills) for kw in keywords)
                
                if not has_skill:
                    return HandoffRecommendation(
                        should_handoff=True,
                        trigger=HandoffTrigger.SKILL_MISMATCH,
                        from_agent=agent_id,
                        to_agent=agent_name,
                        reason=f"Task involves {agent_name}'s specialty",
                        confidence=0.80,
                        context_summary=task_description[:100]
                    )
        
        return None
    
    def _find_best_agent_for_task(self, task_description: str, exclude: List[str] = None) -> Optional[str]:
        """Find the best agent for a given task"""
        exclude = exclude or []
        task_lower = task_description.lower()
        
        # Score each agent by skill match
        scores = {}
        
        for agent_id, skills in self.agent_skills.items():
            if any(ex in agent_id for ex in exclude):
                continue
            
            score = sum(1 for skill in skills if skill in task_lower)
            if score > 0:
                scores[agent_id] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return None
    
    def _infer_next_agent(self, response: str, current_agent: str) -> Optional[str]:
        """Infer which agent should receive handoff based on response content"""
        response_lower = response.lower()
        
        # Look for explicit mentions
        mentions = {
            "code": ["developer", "engineer", "code", "implement", "build"],
            "hunter": ["sales", "outreach", "hunter"],
            "pepper": ["email marketing", "campaign automation"],
            "quill": ["social media", "content creator"],
            "scout": ["research", "investigate"],
            "sage": ["data", "analytics", "analyze"],
            "shuri": ["product", "strategy"],
            "wong": ["documentation", "docs"],
            "guardian": ["test", "qa", "quality"],
            "pixel": ["design", "ui", "ux"],
            "lingua": ["translate", "localization"]
        }
        
        for agent_name, keywords in mentions.items():
            if any(kw in response_lower for kw in keywords):
                return agent_name
        
        # Default: find by skill matching
        return self._find_best_agent_for_task(response, exclude=[current_agent])
    
    def _on_task_completed(self, message: Message):
        """Analyze completed tasks for handoff opportunities"""
        # Could implement automatic handoff chain here
        pass
    
    def _on_agent_message(self, message: Message):
        """Monitor agent messages for handoff cues"""
        # Could implement proactive handoff detection here
        pass
    
    def suggest_handoff_chain(
        self,
        mission_description: str,
        available_agents: List[str]
    ) -> List[Dict[str, str]]:
        """
        Suggest a chain of handoffs for a complex mission
        
        Returns list of dicts with 'agent' and 'task'
        """
        mission_lower = mission_description.lower()
        
        # Define workflow patterns
        workflows = {
            "sales": ["scout", "hunter", "pepper", "sage"],
            "product_launch": ["shuri", "code", "guardian", "wong", "quill"],
            "research": ["scout", "sage", "shuri"],
            "marketing": ["scout", "quill", "pepper", "sage"],
            "development": ["shuri", "code", "guardian", "wong"]
        }
        
        # Detect workflow type
        detected_workflow = None
        for workflow_name, indicators in {
            "sales": ["campaign", "outreach", "leads", "sales"],
            "product_launch": ["launch", "product", "feature"],
            "research": ["research", "analyze", "study", "investigate"],
            "marketing": ["marketing", "promote", "brand"],
            "development": ["develop", "build", "code", "implement"]
        }.items():
            if any(ind in mission_lower for ind in indicators):
                detected_workflow = workflow_name
                break
        
        if not detected_workflow:
            return []
        
        # Filter to available agents
        chain = workflows.get(detected_workflow, [])
        return [{"agent": agent, "task": f"Phase: {agent}"} for agent in chain if agent in available_agents]

# Global instance
auto_handoff = AutoHandoffDetector()
