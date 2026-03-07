"""
Agent-to-Agent Handoff Protocol

Enables agents to pass tasks, context, and partial results to each other.
"""
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

from shared.bus.message_bus import MessageBus, Message, MessageType

logger = logging.getLogger(__name__)

class HandoffStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class HandoffContext:
    """Context passed during handoff"""
    original_task: str
    work_done: str
    findings: Dict[str, Any]
    next_steps: List[str]
    questions: List[str]
    files: List[str]  # References to files/artifacts
    notes: str

class HandoffManager:
    """
    Manages agent-to-agent handoffs
    
    Workflow:
    1. Agent A completes partial work
    2. Agent A calls request_handoff() to Agent B
    3. Agent B receives HANDOFF_REQUEST with context
    4. Agent B accepts/rejects
    5. If accepted, Agent B continues work
    6. Agent B can handoff again or complete
    """
    
    def __init__(self):
        self.bus = MessageBus()
        self._handoffs: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, Callable] = {}
        
        # Subscribe to handoff messages
        self.bus.subscribe(MessageType.HANDOFF_REQUEST, self._on_handoff_request)
        self.bus.subscribe(MessageType.HANDOFF_ACCEPT, self._on_handoff_accept)
    
    def request_handoff(
        self,
        from_agent: str,
        to_agent: str,
        context: HandoffContext,
        mission_id: Optional[str] = None,
        reason: str = ""
    ) -> str:
        """
        Request a handoff from one agent to another
        
        Args:
            from_agent: Agent ID handing off
            to_agent: Agent ID receiving
            context: HandoffContext with work done and next steps
            mission_id: Associated mission
            reason: Why this handoff is happening
        
        Returns:
            handoff_id for tracking
        """
        import uuid
        handoff_id = str(uuid.uuid4())[:8]
        
        handoff_data = {
            "id": handoff_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "status": HandoffStatus.PENDING.value,
            "context": {
                "original_task": context.original_task,
                "work_done": context.work_done,
                "findings": context.findings,
                "next_steps": context.next_steps,
                "questions": context.questions,
                "files": context.files,
                "notes": context.notes
            },
            "mission_id": mission_id,
            "reason": reason,
            "created_at": MessageBus().get_history(limit=1)[0].timestamp if MessageBus().get_history(limit=1) else ""
        }
        
        self._handoffs[handoff_id] = handoff_data
        
        # Publish handoff request
        msg = Message.create(
            MessageType.HANDOFF_REQUEST,
            sender=from_agent,
            recipient=to_agent,
            payload=handoff_data,
            correlation_id=mission_id
        )
        self.bus.publish(msg)
        
        logger.info(f"Handoff {handoff_id} requested: {from_agent} → {to_agent}")
        return handoff_id
    
    def accept_handoff(
        self,
        handoff_id: str,
        agent_id: str,
        notes: str = ""
    ) -> bool:
        """
        Accept a handoff request
        
        Args:
            handoff_id: The handoff to accept
            agent_id: Agent accepting (should match to_agent)
            notes: Optional acceptance notes
        """
        if handoff_id not in self._handoffs:
            logger.error(f"Handoff {handoff_id} not found")
            return False
        
        handoff = self._handoffs[handoff_id]
        
        if handoff["to_agent"] != agent_id:
            logger.error(f"Agent {agent_id} cannot accept handoff intended for {handoff['to_agent']}")
            return False
        
        handoff["status"] = HandoffStatus.ACCEPTED.value
        handoff["accepted_notes"] = notes
        
        # Publish acceptance
        msg = Message.create(
            MessageType.HANDOFF_ACCEPT,
            sender=agent_id,
            recipient=handoff["from_agent"],
            payload={
                "handoff_id": handoff_id,
                "accepted": True,
                "notes": notes
            },
            correlation_id=handoff.get("mission_id")
        )
        self.bus.publish(msg)
        
        logger.info(f"Handoff {handoff_id} accepted by {agent_id}")
        return True
    
    def reject_handoff(
        self,
        handoff_id: str,
        agent_id: str,
        reason: str = ""
    ) -> bool:
        """Reject a handoff request with reason"""
        if handoff_id not in self._handoffs:
            return False
        
        handoff = self._handoffs[handoff_id]
        handoff["status"] = HandoffStatus.REJECTED.value
        handoff["rejection_reason"] = reason
        
        msg = Message.create(
            MessageType.HANDOFF_ACCEPT,  # Reuse accept channel but with accepted=False
            sender=agent_id,
            recipient=handoff["from_agent"],
            payload={
                "handoff_id": handoff_id,
                "accepted": False,
                "reason": reason
            },
            correlation_id=handoff.get("mission_id")
        )
        self.bus.publish(msg)
        
        logger.info(f"Handoff {handoff_id} rejected by {agent_id}: {reason}")
        return True
    
    def _on_handoff_request(self, message: Message):
        """Handle incoming handoff request"""
        payload = message.payload
        handoff_id = payload.get("id")
        
        logger.info(f"Handoff request received: {handoff_id}")
        
        # If there's a callback registered, call it
        if handoff_id in self._callbacks:
            self._callbacks[handoff_id](payload)
    
    def _on_handoff_accept(self, message: Message):
        """Handle handoff acceptance/rejection"""
        payload = message.payload
        handoff_id = payload.get("handoff_id")
        
        if handoff_id in self._handoffs:
            if payload.get("accepted"):
                self._handoffs[handoff_id]["status"] = HandoffStatus.ACCEPTED.value
            else:
                self._handoffs[handoff_id]["status"] = HandoffStatus.REJECTED.value
                self._handoffs[handoff_id]["rejection_reason"] = payload.get("reason", "")
    
    def get_handoff(self, handoff_id: str) -> Optional[Dict[str, Any]]:
        """Get handoff details"""
        return self._handoffs.get(handoff_id)
    
    def get_handoffs_for_mission(self, mission_id: str) -> List[Dict[str, Any]]:
        """Get all handoffs for a mission"""
        return [
            h for h in self._handoffs.values()
            if h.get("mission_id") == mission_id
        ]
    
    def get_recent_handoffs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent handoffs"""
        sorted_handoffs = sorted(
            self._handoffs.values(),
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )
        return sorted_handoffs[:limit]

# Global instance
handoff_manager = HandoffManager()
