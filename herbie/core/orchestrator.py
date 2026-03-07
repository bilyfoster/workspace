"""Herbie - Main AI Orchestrator"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from herbie.core.config import config
from herbie.core.ollama_client import OllamaClient, ChatMessage
from herbie.core.mission_manager import MissionManager, Mission, MissionStatus
from herbie.agents.base_agent import BaseAgent
from herbie.agents.persona_loader import PersonaRegistry

logger = logging.getLogger(__name__)

@dataclass
class SquadMember:
    """An agent in Herbie's squad"""
    name: str
    role: str
    agent: BaseAgent
    avatar: str = "🤖"

class Herbie:
    """
    Herbie - AI Squad Leader
    
    Coordinates missions, manages agents, and delegates tasks.
    """
    
    def __init__(self):
        self.name = "Herbie"
        self.role = "AI Squad Leader & Mission Coordinator"
        
        # Core components
        self.ollama = OllamaClient(config.ollama_host)
        self.mission_manager = MissionManager(config.get('missions.storage_path', './missions'))
        self.persona_registry = PersonaRegistry()
        
        # Active squad members (always-alive agents)
        self.squad: Dict[str, SquadMember] = {}
        
        # Herbie's conversation context
        self.messages: List[ChatMessage] = []
        self._init_system_prompt()
        
        logger.info("Herbie initialized and ready for duty")
    
    def _init_system_prompt(self):
        """Initialize Herbie's system prompt"""
        available_agents = self.persona_registry.list_personas()
        
        system_prompt = f"""You are Herbie, an AI Squad Leader coordinating a team of specialized AI agents.

Your role:
1. Understand user missions (goals/projects)
2. Break missions into specific tasks
3. Delegate tasks to the right specialists
4. Monitor progress and coordinate handoffs
5. Deliver consolidated results to the user

Available Squad Members:
{chr(10).join([f"- {name.title()}" for name in available_agents])}

When a user describes a mission:
1. Summarize the goal back to confirm understanding
2. Break it down into discrete tasks
3. Recommend which agent should handle each task
4. Ask for confirmation before executing

When responding:
- Be concise but thorough
- Think step-by-step
- Delegate specific, actionable tasks
- Track progress and report back"""

        self.messages.append(ChatMessage(role="system", content=system_prompt))
    
    def recruit_squad(self, agent_names: List[str]) -> List[str]:
        """
        Recruit (instantiate) agents for the squad
        
        Args:
            agent_names: List of agent persona names to recruit
        
        Returns:
            List of successfully recruited agent names
        """
        recruited = []
        
        for name in agent_names:
            if name.lower() in self.squad:
                logger.info(f"{name} is already in the squad")
                recruited.append(name)
                continue
            
            agent = self.persona_registry.create_agent(name)
            if agent:
                persona = self.persona_registry.get(name)
                self.squad[name.lower()] = SquadMember(
                    name=agent.name,
                    role=agent.role,
                    agent=agent,
                    avatar=persona.avatar if persona else "🤖"
                )
                recruited.append(name)
                logger.info(f"Recruited {name} to the squad")
            else:
                logger.error(f"Failed to recruit {name}")
        
        return recruited
    
    def get_squad_status(self) -> Dict[str, Any]:
        """Get status of all squad members"""
        return {
            "active_agents": len(self.squad),
            "members": [
                {
                    "name": member.name,
                    "role": member.role,
                    "avatar": member.avatar,
                    **member.agent.get_summary()
                }
                for member in self.squad.values()
            ]
        }
    
    def plan_mission(self, goal: str) -> Dict[str, Any]:
        """
        Plan a mission by breaking it down into tasks
        
        Args:
            goal: The user's mission description
        
        Returns:
            Mission plan with recommended tasks and assignments
        """
        # Add user goal to context
        self.messages.append(ChatMessage(role="user", content=f"Plan this mission: {goal}"))
        
        # Get Herbie's analysis
        plan_prompt = f"""Analyze this mission and create a task breakdown:

MISSION: {goal}

Provide your response in this format:
1. MISSION SUMMARY: (1-2 sentences describing what we're accomplishing)
2. SUGGESTED TASKS:
   - Task 1 → Recommended Agent: [Agent Name]
   - Task 2 → Recommended Agent: [Agent Name]
   etc.
3. QUESTIONS: (any clarifying questions before we proceed)

Be specific about deliverables for each task."""

        response = self.ollama.chat_complete(
            model=config.orchestrator_model,
            messages=[
                self.messages[0],  # System prompt
                ChatMessage(role="user", content=plan_prompt)
            ],
            temperature=0.7
        )
        
        return {
            "goal": goal,
            "plan": response,
            "available_agents": list(self.squad.keys())
        }
    
    def create_mission(
        self,
        title: str,
        description: str,
        goal: str,
        tasks: List[Dict[str, str]]
    ) -> Mission:
        """
        Create a mission and add initial tasks
        
        Args:
            title: Mission title
            description: Mission description
            goal: The main goal
            tasks: List of dicts with 'description' and 'assigned_to'
        
        Returns:
            Created Mission object
        """
        mission = self.mission_manager.create_mission(
            title=title,
            description=description,
            goal=goal
        )
        
        for task_data in tasks:
            self.mission_manager.add_task(
                mission_id=mission.id,
                description=task_data['description'],
                assigned_to=task_data.get('assigned_to')
            )
        
        logger.info(f"Created mission '{title}' with {len(tasks)} tasks")
        return mission
    
    def execute_task(
        self,
        mission_id: str,
        task_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        task_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a single task
        
        Args:
            mission_id: Mission ID
            task_id: Specific task ID (optional if providing description)
            agent_name: Agent to assign (optional, will pick from squad)
            task_description: Task description (optional if using task_id)
        
        Returns:
            Task execution result
        """
        # Get or create task
        if task_id:
            mission = self.mission_manager.get_mission(mission_id)
            task = next((t for t in mission.tasks if t.id == task_id), None) if mission else None
            if not task:
                return {"error": f"Task {task_id} not found"}
            description = task.description
            assigned_agent = task.assigned_to
        else:
            description = task_description
            assigned_agent = agent_name
        
        if not description:
            return {"error": "No task description provided"}
        
        # Determine which agent to use
        if not assigned_agent:
            # Ask Herbie to recommend
            agent = self._recommend_agent(description)
        else:
            agent = self.squad.get(assigned_agent.lower())
        
        if not agent:
            return {"error": f"Agent {assigned_agent} not found in squad"}
        
        # Update task status
        if task_id:
            self.mission_manager.update_task_status(mission_id, task_id, "in_progress")
        
        # Execute task
        logger.info(f"Delegating to {agent.name}: {description[:50]}...")
        result = agent.agent.execute_task(description)
        
        # Update mission
        if task_id:
            self.mission_manager.update_task_status(
                mission_id, task_id, result.status, result.result
            )
        
        return {
            "agent": agent.name,
            "task": description,
            "status": result.status,
            "result": result.result
        }
    
    def _recommend_agent(self, task_description: str) -> Optional[SquadMember]:
        """Recommend the best agent for a task"""
        if not self.squad:
            return None
        
        if len(self.squad) == 1:
            return list(self.squad.values())[0]
        
        # Get agent descriptions
        agent_descriptions = []
        for member in self.squad.values():
            skills = ", ".join(member.agent.skills[:5])
            agent_descriptions.append(f"{member.name}: {member.role}. Skills: {skills}")
        
        # Ask Herbie to pick
        prompt = f"""Given this task: "{task_description}"

Which of these agents is best suited?
{chr(10).join(agent_descriptions)}

Respond with ONLY the agent name."""

        response = self.ollama.chat_complete(
            model=config.orchestrator_model,
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.3
        ).strip().lower()
        
        # Find matching agent
        for name, member in self.squad.items():
            if name in response or member.name.lower() in response:
                return member
        
        # Default to first available
        return list(self.squad.values())[0]
    
    def chat(self, message: str) -> str:
        """Chat with Herbie directly"""
        self.messages.append(ChatMessage(role="user", content=message))
        
        response = self.ollama.chat_complete(
            model=config.orchestrator_model,
            messages=self.messages,
            temperature=0.7
        )
        
        self.messages.append(ChatMessage(role="assistant", content=response))
        return response
    
    def get_mission_report(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Get full report on a mission"""
        return self.mission_manager.get_mission_summary(mission_id)
