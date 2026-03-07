"""
Activity Tracker for Workspace

Monitors and logs all agent activity, conversations, and handoffs.
Provides real-time visibility into who's talking to whom.
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import deque
from pathlib import Path
import threading

from shared.bus.message_bus import MessageBus, Message, MessageType

logger = logging.getLogger(__name__)

@dataclass
class ActivityEvent:
    """A single activity event"""
    id: str
    timestamp: str
    type: str  # message, task, handoff, status
    from_agent: str
    to_agent: Optional[str]
    content: str
    mission_id: Optional[str]
    metadata: Dict[str, Any]

class ActivityTracker:
    """
    Tracks all activity in the Workspace system
    
    Provides:
    - Real-time activity feed
    - Conversation threads between agents
    - Task lifecycle tracking
    - Handoff visualization
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, max_history: int = 1000):
        if self._initialized:
            return
        
        self.max_history = max_history
        self.events: deque = deque(maxlen=max_history)
        self.conversations: Dict[str, List[ActivityEvent]] = {}  # conversation_id -> events
        self.agent_activities: Dict[str, List[ActivityEvent]] = {}  # agent_id -> events
        self.mission_activities: Dict[str, List[ActivityEvent]] = {}  # mission_id -> events
        
        self._setup_subscriptions()
        self._initialized = True
        
        logger.info("ActivityTracker initialized")
    
    def _setup_subscriptions(self):
        """Subscribe to all message types"""
        bus = MessageBus()
        
        # Agent lifecycle
        bus.subscribe(MessageType.AGENT_ONLINE, self._on_agent_online)
        bus.subscribe(MessageType.AGENT_OFFLINE, self._on_agent_offline)
        bus.subscribe(MessageType.AGENT_STATUS, self._on_agent_status)
        
        # Task events
        bus.subscribe(MessageType.TASK_ASSIGNED, self._on_task_event)
        bus.subscribe(MessageType.TASK_STARTED, self._on_task_event)
        bus.subscribe(MessageType.TASK_COMPLETED, self._on_task_event)
        bus.subscribe(MessageType.TASK_FAILED, self._on_task_event)
        
        # Communication
        bus.subscribe(MessageType.AGENT_MESSAGE, self._on_agent_message)
        bus.subscribe(MessageType.USER_MESSAGE, self._on_user_message)
        bus.subscribe(MessageType.SYSTEM_MESSAGE, self._on_system_message)
        
        # Handoffs
        bus.subscribe(MessageType.HANDOFF_REQUEST, self._on_handoff)
        bus.subscribe(MessageType.HANDOFF_ACCEPT, self._on_handoff)
        
        # Missions
        bus.subscribe(MessageType.MISSION_CREATED, self._on_mission_event)
        bus.subscribe(MessageType.MISSION_UPDATED, self._on_mission_event)
        bus.subscribe(MessageType.MISSION_COMPLETED, self._on_mission_event)
    
    def _log_event(self, event: ActivityEvent):
        """Log an event to all tracking structures"""
        self.events.append(event)
        
        # Track by agent
        if event.from_agent not in self.agent_activities:
            self.agent_activities[event.from_agent] = []
        self.agent_activities[event.from_agent].append(event)
        
        if event.to_agent and event.to_agent not in self.agent_activities:
            self.agent_activities[event.to_agent] = []
        if event.to_agent:
            self.agent_activities[event.to_agent].append(event)
        
        # Track by mission
        if event.mission_id:
            if event.mission_id not in self.mission_activities:
                self.mission_activities[event.mission_id] = []
            self.mission_activities[event.mission_id].append(event)
        
        # Track conversations
        if event.to_agent:
            conv_id = self._get_conversation_id(event.from_agent, event.to_agent)
            if conv_id not in self.conversations:
                self.conversations[conv_id] = []
            self.conversations[conv_id].append(event)
    
    def _get_conversation_id(self, agent1: str, agent2: str) -> str:
        """Generate consistent conversation ID for two agents"""
        sorted_agents = sorted([agent1, agent2])
        return f"{sorted_agents[0]}__{sorted_agents[1]}"
    
    def _on_agent_online(self, message: Message):
        """Agent came online"""
        event = ActivityEvent(
            id=message.id,
            timestamp=message.timestamp,
            type="agent_online",
            from_agent=message.sender,
            to_agent=None,
            content=f"Agent {message.payload.get('name')} came online",
            mission_id=None,
            metadata=message.payload
        )
        self._log_event(event)
    
    def _on_agent_offline(self, message: Message):
        """Agent went offline"""
        event = ActivityEvent(
            id=message.id,
            timestamp=message.timestamp,
            type="agent_offline",
            from_agent=message.sender,
            to_agent=None,
            content=f"Agent went offline",
            mission_id=None,
            metadata=message.payload
        )
        self._log_event(event)
    
    def _on_agent_status(self, message: Message):
        """Agent status update"""
        pass  # Can be verbose, skip for now
    
    def _on_task_event(self, message: Message):
        """Task lifecycle event"""
        event_type = message.type.replace("task.", "task_")
        task_desc = message.payload.get('description', '')[:50]
        
        event = ActivityEvent(
            id=message.id,
            timestamp=message.timestamp,
            type=event_type,
            from_agent=message.sender,
            to_agent=None,
            content=f"Task {message.type.split('.')[1]}: {task_desc}...",
            mission_id=message.correlation_id.split(':')[0] if message.correlation_id and ':' in message.correlation_id else message.correlation_id,
            metadata=message.payload
        )
        self._log_event(event)
    
    def _on_agent_message(self, message: Message):
        """Agent-to-agent message"""
        event = ActivityEvent(
            id=message.id,
            timestamp=message.timestamp,
            type="agent_message",
            from_agent=message.sender,
            to_agent=message.recipient,
            content=message.payload.get('content', '')[:100],
            mission_id=message.correlation_id,
            metadata=message.payload
        )
        self._log_event(event)
    
    def _on_user_message(self, message: Message):
        """User message to agent"""
        event = ActivityEvent(
            id=message.id,
            timestamp=message.timestamp,
            type="user_message",
            from_agent="user",
            to_agent=message.recipient,
            content=message.payload.get('content', '')[:100],
            mission_id=message.correlation_id,
            metadata={}
        )
        self._log_event(event)
    
    def _on_system_message(self, message: Message):
        """System message"""
        event = ActivityEvent(
            id=message.id,
            timestamp=message.timestamp,
            type="system",
            from_agent="system",
            to_agent=message.recipient,
            content=message.payload.get('content', ''),
            mission_id=message.correlation_id,
            metadata=message.payload
        )
        self._log_event(event)
    
    def _on_handoff(self, message: Message):
        """Handoff event"""
        is_accept = message.type == MessageType.HANDOFF_ACCEPT.value
        
        if is_accept:
            accepted = message.payload.get("accepted", False)
            handoff_type = "handoff_accept" if accepted else "handoff_reject"
        else:
            handoff_type = "handoff_request"
        
        payload = message.payload
        
        event = ActivityEvent(
            id=message.id,
            timestamp=message.timestamp,
            type=handoff_type,
            from_agent=message.sender,
            to_agent=message.recipient,
            content=f"Handoff {handoff_type.split('_')[1]}: {payload.get('reason', payload.get('context', {}).get('original_task', 'Unknown'))[:50]}...",
            mission_id=payload.get("mission_id") or message.correlation_id,
            metadata=payload
        )
        self._log_event(event)
    
    def _on_mission_event(self, message: Message):
        """Mission lifecycle event"""
        event_type = message.type.replace("mission.", "mission_")
        
        event = ActivityEvent(
            id=message.id,
            timestamp=message.timestamp,
            type=event_type,
            from_agent=message.sender,
            to_agent=None,
            content=f"Mission {message.type.split('.')[1]}: {message.payload.get('title', 'Unknown')}",
            mission_id=message.payload.get("mission_id"),
            metadata=message.payload
        )
        self._log_event(event)
    
    # Query methods
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get most recent events"""
        return [asdict(e) for e in list(self.events)[-limit:]]
    
    def get_agent_conversation(self, agent1: str, agent2: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation between two agents"""
        conv_id = self._get_conversation_id(agent1, agent2)
        events = self.conversations.get(conv_id, [])
        return [asdict(e) for e in events[-limit:]]
    
    def get_agent_activity(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all activity for an agent"""
        events = self.agent_activities.get(agent_id, [])
        return [asdict(e) for e in events[-limit:]]
    
    def get_mission_activity(self, mission_id: str) -> List[Dict[str, Any]]:
        """Get all activity for a mission"""
        events = self.mission_activities.get(mission_id, [])
        return [asdict(e) for e in events]
    
    def get_conversation_partners(self, agent_id: str) -> List[str]:
        """Get list of agents this agent has talked to"""
        partners = set()
        for conv_id, events in self.conversations.items():
            if agent_id in conv_id:
                other = conv_id.replace(agent_id, "").replace("__", "")
                partners.add(other)
        return list(partners)
    
    def get_activity_summary(self) -> Dict[str, Any]:
        """Get summary of all activity"""
        total_events = len(self.events)
        
        # Count by type
        type_counts = {}
        for event in self.events:
            type_counts[event.type] = type_counts.get(event.type, 0) + 1
        
        # Most active agents
        agent_counts = {}
        for agent_id, events in self.agent_activities.items():
            agent_counts[agent_id] = len(events)
        
        top_agents = sorted(agent_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Recent conversations
        recent_convs = []
        for conv_id, events in list(self.conversations.items())[-10:]:
            if events:
                agents = conv_id.split("__")
                recent_convs.append({
                    "agents": agents,
                    "message_count": len(events),
                    "last_activity": events[-1].timestamp
                })
        
        return {
            "total_events": total_events,
            "event_types": type_counts,
            "active_agents": len(self.agent_activities),
            "top_agents": top_agents,
            "conversations": recent_convs,
            "missions_tracked": len(self.mission_activities)
        }
    
    def export_mission_log(self, mission_id: str, filepath: Path):
        """Export mission activity to file"""
        events = self.get_mission_activity(mission_id)
        
        log_data = {
            "mission_id": mission_id,
            "exported_at": datetime.now().isoformat(),
            "event_count": len(events),
            "events": events
        }
        
        filepath.write_text(json.dumps(log_data, indent=2))
        logger.info(f"Exported mission log to {filepath}")

# Global instance
tracker = ActivityTracker()
