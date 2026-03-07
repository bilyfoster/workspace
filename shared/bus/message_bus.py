"""Message Bus for Inter-Agent Communication"""
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Callable, Optional, Any, Union
from queue import Queue as ThreadQueue
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

class MessageType(Enum):
    # Task-related
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    
    # Agent lifecycle
    AGENT_ONLINE = "agent.online"
    AGENT_OFFLINE = "agent.offline"
    AGENT_STATUS = "agent.status"
    
    # Mission
    MISSION_CREATED = "mission.created"
    MISSION_UPDATED = "mission.updated"
    MISSION_COMPLETED = "mission.completed"
    
    # Communication
    AGENT_MESSAGE = "agent.message"  # Agent-to-agent
    USER_MESSAGE = "user.message"    # User-to-agent
    SYSTEM_MESSAGE = "system.message"
    
    # Handoff
    HANDOFF_REQUEST = "handoff.request"
    HANDOFF_ACCEPT = "handoff.accept"

@dataclass
class Message:
    """A message in the Workspace system"""
    id: str
    type: str
    sender: str  # agent_id or "user" or "orchestrator"
    recipient: Optional[str]  # agent_id or None for broadcast
    payload: Dict[str, Any]
    timestamp: str
    correlation_id: Optional[str] = None  # Links related messages
    
    @classmethod
    def create(
        cls,
        msg_type: MessageType,
        sender: str,
        payload: Dict[str, Any],
        recipient: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> "Message":
        import uuid
        return cls(
            id=str(uuid.uuid4())[:8],
            type=msg_type.value,
            sender=sender,
            recipient=recipient,
            payload=payload,
            timestamp=datetime.now().isoformat(),
            correlation_id=correlation_id
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())

class MessageBus:
    """
    Central message bus for Workspace
    
    Handles routing of messages between orchestrator and agents.
    In-memory for now; can be swapped for Redis/RabbitMQ for scale.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - only one message bus per process"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._agent_queues: Dict[str, Union[asyncio.Queue, ThreadQueue, List]] = {}
        self._message_history: List[Message] = []
        self._history_limit = 1000
        self._lock = threading.Lock()
        
        self._initialized = True
        logger.info("MessageBus initialized")
    
    def subscribe(self, message_type: MessageType, callback: Callable[[Message], None]):
        """Subscribe to a message type"""
        self._subscribers[message_type.value].append(callback)
        logger.debug(f"Subscriber added for {message_type.value}")
    
    def unsubscribe(self, message_type: MessageType, callback: Callable[[Message], None]):
        """Unsubscribe from a message type"""
        if callback in self._subscribers[message_type.value]:
            self._subscribers[message_type.value].remove(callback)
    
    def publish(self, message: Message):
        """Publish a message to the bus"""
        # Store in history
        with self._lock:
            self._message_history.append(message)
            if len(self._message_history) > self._history_limit:
                self._message_history.pop(0)
        
        # Notify type-specific subscribers
        if message.type in self._subscribers:
            for callback in self._subscribers[message.type]:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Error in subscriber callback: {e}")
        
        # Notify broadcast subscribers (recipient=None)
        if message.recipient is None and "*" in self._subscribers:
            for callback in self._subscribers["*"]:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Error in broadcast callback: {e}")
        
        logger.debug(f"Published {message.type} from {message.sender}")
    
    def send_to_agent(self, agent_id: str, message: Message) -> bool:
        """Send a message directly to an agent's queue"""
        if agent_id in self._agent_queues:
            queue = self._agent_queues[agent_id]
            if isinstance(queue, asyncio.Queue):
                asyncio.create_task(queue.put(message))
            elif isinstance(queue, ThreadQueue):
                queue.put(message)
            elif isinstance(queue, list):
                queue.append(message)
            return True
        return False
    
    def register_agent_queue(self, agent_id: str, queue: Union[asyncio.Queue, ThreadQueue, List]):
        """Register an agent's message queue"""
        self._agent_queues[agent_id] = queue
        logger.info(f"Agent {agent_id} registered with message queue")
    
    def unregister_agent_queue(self, agent_id: str):
        """Unregister an agent's message queue"""
        if agent_id in self._agent_queues:
            del self._agent_queues[agent_id]
            logger.info(f"Agent {agent_id} unregistered from message bus")
    
    def get_history(
        self,
        message_type: Optional[str] = None,
        sender: Optional[str] = None,
        limit: int = 100
    ) -> List[Message]:
        """Get message history with optional filtering"""
        messages = self._message_history
        
        if message_type:
            messages = [m for m in messages if m.type == message_type]
        
        if sender:
            messages = [m for m in messages if m.sender == sender]
        
        return messages[-limit:]
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all registered agents"""
        return {
            "registered_agents": list(self._agent_queues.keys()),
            "total_subscribers": sum(len(s) for s in self._subscribers.values()),
            "message_count": len(self._message_history)
        }

# Global message bus instance
bus = MessageBus()
