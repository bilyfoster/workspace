#!/usr/bin/env python3
"""
Workspace Orchestrator

Manages agents, coordinates missions, and provides
a unified interface for the dashboard and CLI.

Usage:
    python workspace_orchestrator.py
"""
import asyncio
import json
import logging
import signal
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from herbie.core.config import config
from herbie.core.ollama_client import OllamaClient, ChatMessage
from herbie.core.mission_manager import MissionManager, Mission, MissionStatus
from shared.bus.message_bus import MessageBus, Message, MessageType
from shared.bus.activity_tracker import tracker, ActivityTracker
from shared.bus.handoff import handoff_manager, HandoffManager
from shared.bus.auto_handoff import auto_handoff, AutoHandoffDetector
from shared.bus.group_chat import group_chat_manager, GroupChatManager
from shared.bus.alerts import alert_manager, AlertManager
from shared.bus.analytics import analytics, AnalyticsCollector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AgentThread:
    """Represents a running agent thread"""
    id: str
    name: str
    role: str
    avatar: str
    soul_path: Path
    thread: Optional[threading.Thread] = None
    status: str = "starting"
    current_task: Optional[str] = None
    tasks_completed: int = 0
    started_at: str = ""
    model: str = ""
    stop_event: Optional[threading.Event] = None

class WorkspaceOrchestrator:
    """
    Central orchestrator for Workspace
    
    Coordinates missions, manages agents, routes messages.
    Uses threads for agents (shared memory) so MessageBus works.
    """
    
    def __init__(self):
        self.name = "Workspace"
        self.version = "1.1.5"
        
        # Components
        self.ollama = OllamaClient(config.ollama_host)
        self.mission_manager = MissionManager()
        self.bus = MessageBus()
        self.tracker = tracker
        self.handoff_manager = handoff_manager
        self.auto_handoff = auto_handoff
        self.group_chat = group_chat_manager
        self.alerts = alert_manager
        self.analytics = analytics
        
        # Agent threads (not processes - shared memory for MessageBus)
        self.agents: Dict[str, AgentThread] = {}
        self.agent_dir = Path("./agents")
        
        # Missions
        self.active_missions: Dict[str, Mission] = {}
        
        # State
        self.running = False
        self._shutdown_event = threading.Event()
        
        # Subscribe to messages
        self._setup_subscriptions()
        
        logger.info("Workspace Orchestrator initialized")
    
    def _setup_subscriptions(self):
        """Subscribe to message bus events"""
        self.bus.subscribe(MessageType.AGENT_ONLINE, self._on_agent_online)
        self.bus.subscribe(MessageType.AGENT_OFFLINE, self._on_agent_offline)
        self.bus.subscribe(MessageType.TASK_STARTED, self._on_task_started)
        self.bus.subscribe(MessageType.TASK_COMPLETED, self._on_task_completed)
        self.bus.subscribe(MessageType.TASK_FAILED, self._on_task_failed)
        self.bus.subscribe(MessageType.AGENT_STATUS, self._on_agent_status)
    
    def _on_agent_online(self, message: Message):
        """Handle agent coming online"""
        agent_id = message.sender
        payload = message.payload
        
        if agent_id in self.agents:
            self.agents[agent_id].status = "idle"
            self.agents[agent_id].model = payload.get('model', '')
            logger.info(f"Agent {payload.get('name')} is online")
    
    def _on_agent_offline(self, message: Message):
        """Handle agent going offline"""
        agent_id = message.sender
        if agent_id in self.agents:
            self.agents[agent_id].status = "offline"
            logger.info(f"Agent {message.payload.get('name')} went offline")
    
    def _on_task_started(self, message: Message):
        """Handle task start"""
        agent_id = message.sender
        if agent_id in self.agents:
            self.agents[agent_id].status = "working"
            self.agents[agent_id].current_task = message.payload.get('description')
            logger.info(f"Agent {agent_id} started task: {message.payload.get('description', '')[:50]}...")
    
    def _on_task_completed(self, message: Message):
        """Handle task completion"""
        agent_id = message.sender
        task_id = message.payload.get('task_id')
        result = message.payload.get('result')
        
        if agent_id in self.agents:
            self.agents[agent_id].status = "idle"
            self.agents[agent_id].current_task = None
            self.agents[agent_id].tasks_completed += 1
        
        # Update mission if this was part of one
        if message.correlation_id:
            mission_id = message.correlation_id.split(':')[0] if ':' in message.correlation_id else message.correlation_id
            self.mission_manager.update_task_status(
                mission_id, task_id, "completed", result
            )
        
        logger.info(f"Agent {agent_id} completed task")
    
    def _on_task_failed(self, message: Message):
        """Handle task failure"""
        agent_id = message.sender
        if agent_id in self.agents:
            self.agents[agent_id].status = "error"
            self.agents[agent_id].current_task = None
        
        logger.error(f"Agent {agent_id} failed task: {message.payload.get('error')}")
    
    def _on_agent_status(self, message: Message):
        """Handle status updates"""
        pass
    
    def spawn_agent(self, name: str) -> Optional[AgentThread]:
        """
        Spawn a new agent as a thread (not process)
        
        Args:
            name: Agent name (e.g., "hunter", "pepper")
        
        Returns:
            AgentThread if successful
        """
        soul_path = self.agent_dir / name / "soul.md"
        if not soul_path.exists():
            logger.error(f"Soul not found for agent: {name}")
            return None
        
        # Check if already running
        for agent in self.agents.values():
            if agent.name.lower() == name.lower() and agent.status not in ("offline", "stopped"):
                logger.info(f"Agent {name} is already running")
                return agent
        
        agent_id = f"{name}-{int(time.time())}"
        
        # Parse soul for metadata
        soul_content = soul_path.read_text()
        role = self._extract_soul_field(soul_content, 'Role')
        avatar = self._extract_soul_field(soul_content, 'Avatar')
        
        stop_event = threading.Event()
        
        agent_thread = AgentThread(
            id=agent_id,
            name=name.title(),
            role=role,
            avatar=avatar,
            soul_path=soul_path,
            started_at=datetime.now().isoformat(),
            stop_event=stop_event
        )
        
        # Import and start agent runner
        try:
            from agent_runner import AgentRunner
            
            runner = AgentRunner(agent_id, name, soul_path, stop_event)
            thread = threading.Thread(target=runner.run, daemon=True)
            thread.start()
            
            agent_thread.thread = thread
            self.agents[agent_id] = agent_thread
            
            logger.info(f"Spawned agent {name} as thread {thread.ident}")
            return agent_thread
            
        except Exception as e:
            logger.error(f"Failed to spawn agent {name}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_soul_field(self, content: str, field: str) -> str:
        """Extract a field from soul.md"""
        for line in content.split('\n'):
            if line.startswith(f'**{field}:**'):
                return line.split(':', 1)[1].strip().strip('*')
        return ""
    
    def kill_agent(self, agent_id: str) -> bool:
        """Stop a running agent thread"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        if agent.stop_event:
            agent.stop_event.set()
        agent.status = "offline"
        
        logger.info(f"Stopped agent {agent.name}")
        return True
    
    def list_available_agents(self) -> List[str]:
        """List all agents that have soul.md files"""
        available = []
        for agent_dir in self.agent_dir.iterdir():
            if agent_dir.is_dir() and (agent_dir / "soul.md").exists():
                available.append(agent_dir.name)
        return sorted(available)
    
    def get_agent_status(self) -> List[Dict[str, Any]]:
        """Get status of all agents"""
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "avatar": agent.avatar,
                "status": agent.status,
                "model": agent.model,
                "current_task": agent.current_task,
                "tasks_completed": agent.tasks_completed,
                "started_at": agent.started_at,
                "thread_alive": agent.thread.is_alive() if agent.thread else False
            }
            for agent in self.agents.values()
        ]
    
    def assign_task(
        self,
        agent_name: str,
        task_description: str,
        mission_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> bool:
        """
        Assign a task to an agent
        
        Args:
            agent_name: Name of agent (e.g., "hunter")
            task_description: What to do
            mission_id: Optional mission ID for tracking
            context: Additional context
        """
        # Find running agent
        agent = None
        for a in self.agents.values():
            if a.name.lower() == agent_name.lower() and a.status != "offline":
                agent = a
                break
        
        if not agent:
            logger.error(f"Agent {agent_name} not found or offline")
            return False
        
        # Create task message
        task_id = f"task-{int(time.time())}"
        correlation_id = f"{mission_id}:{task_id}" if mission_id else task_id
        
        message = Message.create(
            MessageType.TASK_ASSIGNED,
            sender="orchestrator",
            recipient=agent.id,
            payload={
                "id": task_id,
                "description": task_description,
                "context": context or {},
                "assigned_at": datetime.now().isoformat()
            },
            correlation_id=correlation_id
        )
        
        # Send to agent
        sent = self.bus.send_to_agent(agent.id, message)
        if sent:
            logger.info(f"Assigned task to {agent_name}: {task_description[:50]}...")
        
        return sent
    
    def chat_with_agent(self, agent_name: str, message: str) -> bool:
        """Send a chat message to an agent"""
        agent = None
        for a in self.agents.values():
            if a.name.lower() == agent_name.lower() and a.status != "offline":
                agent = a
                break
        
        if not agent:
            return False
        
        msg = Message.create(
            MessageType.USER_MESSAGE,
            sender="user",
            recipient=agent.id,
            payload={"content": message}
        )
        
        return self.bus.send_to_agent(agent.id, msg)
    
    def create_mission(
        self,
        title: str,
        description: str,
        tasks: List[Dict[str, str]]
    ) -> Mission:
        """
        Create a mission and add initial tasks
        
        Args:
            title: Mission title
            description: Mission description
            tasks: List of dicts with 'description' and 'assigned_to'
        
        Returns:
            Created Mission object
        """
        mission = self.mission_manager.create_mission(
            title=title,
            description=description,
            goal=description
        )
        
        for task_data in tasks:
            self.mission_manager.add_task(
                mission_id=mission.id,
                description=task_data['description'],
                assigned_to=task_data.get('assigned_to')
            )
        
        self.active_missions[mission.id] = mission
        
        # Announce mission
        self.bus.publish(Message.create(
            MessageType.MISSION_CREATED,
            sender="orchestrator",
            payload={
                "mission_id": mission.id,
                "title": title,
                "task_count": len(tasks)
            }
        ))
        
        logger.info(f"Created mission '{title}' with {len(tasks)} tasks")
        return mission
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all data needed for dashboard"""
        missions = self.mission_manager.list_missions()
        
        return {
            "system": {
                "name": self.name,
                "version": self.version,
                "status": "running" if self.running else "stopped",
                "ollama_connected": self.ollama.is_healthy()
            },
            "agents": self.get_agent_status(),
            "available_agents": self.list_available_agents(),
            "missions": [
                {
                    "id": m.id,
                    "title": m.title,
                    "status": m.status.value,
                    "progress": self._calculate_progress(m),
                    "tasks": len(m.tasks)
                }
                for m in missions
            ],
            "recent_messages": [
                m.to_dict() for m in self.bus.get_history(limit=20)
            ],
            "activity_summary": self.tracker.get_activity_summary(),
            "recent_handoffs": self.handoff_manager.get_recent_handoffs(10),
            "groups": self.group_chat.list_groups(),
            "active_alerts": self.alerts.get_active_alerts(),
            "system_metrics": self.analytics.get_system_metrics(),
            "agent_performance": self.analytics.get_agent_performance(),
            "activity_timeline": self.analytics.get_activity_timeline()
        }
    
    def _calculate_progress(self, mission: Mission) -> Dict[str, int]:
        """Calculate mission progress"""
        total = len(mission.tasks)
        if total == 0:
            return {"total": 0, "completed": 0, "percent": 0}
        
        completed = len([t for t in mission.tasks if t.status == "completed"])
        return {
            "total": total,
            "completed": completed,
            "percent": int((completed / total) * 100)
        }
    
    async def run(self):
        """Main orchestrator loop"""
        self.running = True
        logger.info("Workspace Orchestrator running")
        
        while not self._shutdown_event.is_set():
            # Health check agents
            for agent_id, agent in list(self.agents.items()):
                if agent.thread and not agent.thread.is_alive():
                    if agent.status != "offline":
                        agent.status = "offline"
                        logger.warning(f"Agent {agent.name} thread died")
            
            await asyncio.sleep(5)
        
        self.running = False
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Workspace")
        self._shutdown_event.set()
        
        # Stop all agents
        for agent_id in list(self.agents.keys()):
            self.kill_agent(agent_id)

# Singleton instance
_orchestrator: Optional[WorkspaceOrchestrator] = None

def get_orchestrator() -> WorkspaceOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = WorkspaceOrchestrator()
    return _orchestrator

async def main():
    """Entry point"""
    orchestrator = get_orchestrator()
    
    # Handle signals
    def signal_handler(sig, frame):
        orchestrator.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await orchestrator.run()
    except KeyboardInterrupt:
        orchestrator.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
