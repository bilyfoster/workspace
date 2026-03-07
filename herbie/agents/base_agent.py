"""Base Agent class for Herbie's squad"""
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from herbie.core.ollama_client import OllamaClient, ChatMessage
from herbie.core.config import config

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    ERROR = "error"
    PAUSED = "paused"

@dataclass
class Task:
    """A task assigned to an agent"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

class BaseAgent:
    """
    Base class for all Herbie agents
    
    Each agent has:
    - A persona (name, role, personality, skills)
    - A message history (context/conversation)
    - A status (idle, working, etc.)
    - Methods to execute tasks
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        personality: str = "",
        skills: List[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.role = role
        self.personality = personality
        self.skills = skills or []
        self.model = model or config.default_model
        self.temperature = temperature
        self.status = AgentStatus.IDLE
        
        # Build system prompt from persona
        self.system_prompt = system_prompt or self._build_system_prompt()
        
        # Conversation history
        self.messages: List[ChatMessage] = [
            ChatMessage(role="system", content=self.system_prompt)
        ]
        
        # Task history
        self.tasks: List[Task] = []
        self.current_task: Optional[Task] = None
        
        # Ollama client
        self.client = OllamaClient(config.ollama_host)
        
        logger.info(f"Agent '{name}' ({self.id}) initialized with model {self.model}")
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt from persona attributes"""
        skills_str = ", ".join(self.skills) if self.skills else "general assistance"
        
        prompt = f"""You are {self.name}, {self.role}.

Personality: {self.personality or "Professional and helpful"}

Your skills: {skills_str}

Guidelines:
- Stay in character as {self.name}
- Be concise but thorough
- If you need clarification, ask specific questions
- Focus on delivering actionable results
- Acknowledge when a task is outside your expertise

When given a task, think step-by-step and provide your best work."""
        
        return prompt.strip()
    
    def execute_task(self, task_description: str, context: Dict[str, Any] = None) -> Task:
        """
        Execute a task and return the result
        
        Args:
            task_description: What needs to be done
            context: Additional context (files, previous results, etc.)
        
        Returns:
            Task object with result
        """
        # Create task
        task = Task(
            description=task_description,
            context=context or {}
        )
        self.current_task = task
        self.tasks.append(task)
        self.status = AgentStatus.WORKING
        
        logger.info(f"Agent {self.name} starting task: {task_description[:50]}...")
        
        try:
            # Build prompt with context
            context_str = self._format_context(context)
            user_message = f"Task: {task_description}\n\n{context_str}".strip()
            
            # Add to conversation
            self.messages.append(ChatMessage(role="user", content=user_message))
            
            # Get response from LLM
            response_content = ""
            for response in self.client.chat(
                model=self.model,
                messages=self.messages,
                stream=False,
                temperature=self.temperature
            ):
                response_content += response.message.content
            
            # Update conversation history
            self.messages.append(ChatMessage(role="assistant", content=response_content))
            
            # Update task
            task.result = response_content
            task.status = "completed"
            task.completed_at = datetime.now()
            self.status = AgentStatus.IDLE
            
            logger.info(f"Agent {self.name} completed task in {len(response_content)} chars")
            
        except Exception as e:
            task.status = "failed"
            task.result = f"Error: {str(e)}"
            self.status = AgentStatus.ERROR
            logger.error(f"Agent {self.name} failed task: {e}")
        
        self.current_task = None
        return task
    
    def chat(self, message: str) -> str:
        """Have a conversation with the agent (not a formal task)"""
        self.messages.append(ChatMessage(role="user", content=message))
        
        response_content = ""
        for response in self.client.chat(
            model=self.model,
            messages=self.messages,
            stream=False,
            temperature=self.temperature
        ):
            response_content += response.message.content
        
        self.messages.append(ChatMessage(role="assistant", content=response_content))
        return response_content
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dict into a string"""
        if not context:
            return ""
        
        parts = []
        for key, value in context.items():
            if value:
                parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return "\n\n".join(parts) if parts else ""
    
    def clear_history(self, keep_system: bool = True):
        """Clear conversation history"""
        if keep_system:
            self.messages = [self.messages[0]]  # Keep system prompt
        else:
            self.messages = []
    
    def get_summary(self) -> Dict[str, Any]:
        """Get agent summary for display"""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
            "model": self.model,
            "tasks_completed": len([t for t in self.tasks if t.status == "completed"]),
            "current_task": self.current_task.description if self.current_task else None
        }
    
    def __repr__(self):
        return f"<Agent {self.name} ({self.role}) - {self.status.value}>"
