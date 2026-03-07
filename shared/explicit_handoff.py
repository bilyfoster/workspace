#!/usr/bin/env python3
"""
Explicit Handoff System - Swarm-style function-based handoffs

Agents can explicitly transfer to other agents by calling handoff functions.
This works alongside the Manager's orchestration for maximum flexibility.

Example:
    # In an agent's response, they can say:
    "I'll hand this off to Code for implementation. [handoff:code]"
    
    # Or programmatically:
    handoff_manager.explicit_handoff(
        from_agent="shuri",
        to_agent="code", 
        context={"task": "implement the design"}
    )
"""
import json
import re
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class HandoffType(Enum):
    EXPLICIT = "explicit"      # Agent explicitly says "handoff to X"
    TOOL_BASED = "tool_based"  # Agent calls handoff as a tool/function
    AUTO = "auto"              # Manager/auto-detector initiates


@dataclass
class ExplicitHandoff:
    """A handoff request between agents"""
    id: str
    timestamp: str
    from_agent: str
    to_agent: str
    handoff_type: HandoffType
    context: Dict
    status: str = "pending"  # pending, accepted, rejected, completed
    reason: Optional[str] = None


class ExplicitHandoffManager:
    """
    Manages explicit handoffs between agents (Swarm-style)
    
    Key features:
    - Agents can trigger handoffs via text patterns [handoff:agent_name]
    - Agents can call handoff as a tool
    - Context is passed cleanly between agents
    - Manager is notified but doesn't block the handoff
    """
    
    # Pattern to detect handoff in agent responses
    HANDOFF_PATTERN = re.compile(
        r'\[handoff\s*:\s*(\w+)\s*\]'  # [handoff:agent_name]
        r'|\[transfer\s+to\s+(\w+)\s*\]'  # [transfer to agent_name]
        r'|handoff\s+to\s+(\w+)'  # "handoff to agent_name"
        r'|transferring\s+to\s+(\w+)',  # "transferring to agent_name"
        re.IGNORECASE
    )
    
    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.pending_handoffs: Dict[str, ExplicitHandoff] = {}
        self.completed_handoffs: List[ExplicitHandoff] = []
        self._callbacks: List[Callable] = []
        self._counter = 0
        
    def register_callback(self, callback: Callable):
        """Register callback for handoff events"""
        self._callbacks.append(callback)
        
    def check_for_handoff(self, agent_name: str, message: str) -> Optional[ExplicitHandoff]:
        """
        Check if an agent's message contains a handoff request
        
        Args:
            agent_name: Name of the agent sending the message
            message: The agent's message text
            
        Returns:
            ExplicitHandoff if found, None otherwise
        """
        match = self.HANDOFF_PATTERN.search(message)
        if not match:
            return None
            
        # Get the target agent name from whichever group matched
        target_agent = match.group(1) or match.group(2) or match.group(3) or match.group(4)
        if not target_agent:
            return None
            
        # Create context from the message
        context = {
            "original_message": message,
            "handoff_trigger": match.group(0),
            "detected_at": datetime.now().isoformat()
        }
        
        return self.create_handoff(agent_name, target_agent, context, HandoffType.EXPLICIT)
        
    def create_handoff(
        self, 
        from_agent: str, 
        to_agent: str, 
        context: Dict,
        handoff_type: HandoffType = HandoffType.EXPLICIT
    ) -> Optional[ExplicitHandoff]:
        """
        Create a new explicit handoff
        
        Args:
            from_agent: Name of agent handing off
            to_agent: Name of agent to hand off to
            context: Dict with context to pass
            handoff_type: Type of handoff
            
        Returns:
            ExplicitHandoff if successful
        """
        # Validate agents exist
        if not self._agent_exists(to_agent):
            return None
            
        self._counter += 1
        handoff = ExplicitHandoff(
            id=f"handoff-{self._counter}-{int(datetime.now().timestamp())}",
            timestamp=datetime.now().isoformat(),
            from_agent=from_agent,
            to_agent=to_agent,
            handoff_type=handoff_type,
            context=context
        )
        
        self.pending_handoffs[handoff.id] = handoff
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(handoff)
            except Exception as e:
                print(f"Handoff callback error: {e}")
                
        return handoff
        
    def execute_handoff(self, handoff_id: str) -> bool:
        """
        Execute a pending handoff - spawn target if needed and notify
        
        Args:
            handoff_id: ID of handoff to execute
            
        Returns:
            True if successful
        """
        if handoff_id not in self.pending_handoffs:
            return False
            
        handoff = self.pending_handoffs[handoff_id]
        
        # Ensure target agent is running
        if not self._agent_is_running(handoff.to_agent):
            if self.orchestrator:
                print(f"Spawning {handoff.to_agent} for handoff...")
                self.orchestrator.spawn_agent(handoff.to_agent.lower())
        
        # Build handoff message for target agent
        handoff_message = self._build_handoff_message(handoff)
        
        # Send to target agent (if orchestrator available)
        if self.orchestrator:
            # Use the orchestrator to send message
            self.orchestrator.chat_with_agent(
                handoff.to_agent,
                handoff_message
            )
        
        handoff.status = "completed"
        self.completed_handoffs.append(handoff)
        del self.pending_handoffs[handoff_id]
        
        return True
        
    def reject_handoff(self, handoff_id: str, reason: str = "") -> bool:
        """Reject a pending handoff"""
        if handoff_id not in self.pending_handoffs:
            return False
            
        handoff = self.pending_handoffs[handoff_id]
        handoff.status = "rejected"
        handoff.reason = reason
        self.completed_handoffs.append(handoff)
        del self.pending_handoffs[handoff_id]
        
        return True
        
    def _build_handoff_message(self, handoff: ExplicitHandoff) -> str:
        """Build the message to send to target agent"""
        lines = [
            f"🔄 HANDOFF FROM {handoff.from_agent.upper()}",
            "",
            "You've been explicitly handed a task:",
            ""
        ]
        
        # Add context
        if "task" in handoff.context:
            lines.append(f"TASK: {handoff.context['task']}")
        if "original_message" in handoff.context:
            # Show relevant part
            msg = handoff.context['original_message']
            # Remove the handoff trigger
            msg = self.HANDOFF_PATTERN.sub("", msg).strip()
            if msg:
                lines.append(f"CONTEXT: {msg}")
                
        lines.extend([
            "",
            "Please acknowledge this handoff and proceed with the task."
        ])
        
        return "\n".join(lines)
        
    def _agent_exists(self, agent_name: str) -> bool:
        """Check if an agent soul exists"""
        from pathlib import Path
        soul_path = Path(f"./agents/{agent_name.lower()}/soul.md")
        return soul_path.exists()
        
    def _agent_is_running(self, agent_name: str) -> bool:
        """Check if an agent is currently running"""
        if not self.orchestrator:
            return False
        for agent in self.orchestrator.agents.values():
            if agent.name.lower() == agent_name.lower():
                return agent.status != "offline"
        return False
        
    def get_pending(self) -> List[ExplicitHandoff]:
        """Get all pending handoffs"""
        return list(self.pending_handoffs.values())
        
    def get_recent(self, limit: int = 10) -> List[ExplicitHandoff]:
        """Get recent completed handoffs"""
        return self.completed_handoffs[-limit:]
        
    def format_handoff_for_display(self, handoff: ExplicitHandoff) -> str:
        """Format handoff for display"""
        icon = {
            "pending": "⏳",
            "accepted": "✅",
            "rejected": "❌",
            "completed": "✓"
        }.get(handoff.status, "?")
        
        return f"{icon} {handoff.from_agent} → {handoff.to_agent} ({handoff.handoff_type.value})"


# Global instance (lazy init)
_explicit_handoff_manager: Optional[ExplicitHandoffManager] = None

def get_explicit_handoff_manager(orchestrator=None) -> ExplicitHandoffManager:
    """Get or create global handoff manager"""
    global _explicit_handoff_manager
    if _explicit_handoff_manager is None:
        _explicit_handoff_manager = ExplicitHandoffManager(orchestrator)
    return _explicit_handoff_manager
