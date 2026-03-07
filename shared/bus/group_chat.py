"""
Group Chat System for Workspace

Enables multiple agents to participate in a single conversation thread.
Supports threaded discussions, @mentions, and broadcast messages.
"""
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from shared.bus.message_bus import MessageBus, Message, MessageType

logger = logging.getLogger(__name__)

class GroupChatType(Enum):
    DISCUSSION = "discussion"      # Open discussion
    WORKFLOW = "workflow"          # Task-oriented workflow
    STANDUP = "standup"           # Daily standup style
    BRAINSTORM = "brainstorm"     # Idea generation
    REVIEW = "review"             # Code/design review

@dataclass
class GroupMessage:
    """A message in a group chat"""
    id: str
    group_id: str
    sender: str
    content: str
    timestamp: str
    mentions: List[str] = field(default_factory=list)
    reply_to: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GroupChat:
    """A group chat session"""
    id: str
    name: str
    type: GroupChatType
    members: Set[str]
    created_by: str
    created_at: str
    topic: Optional[str] = None
    is_active: bool = True
    messages: List[GroupMessage] = field(default_factory=list)

class GroupChatManager:
    """
    Manages group chat sessions between agents
    
    Features:
    - Create group chats with specific agents
    - Threaded conversations
    - @mentions for directing messages
    - Broadcast to all members
    - Topic-based organization
    """
    
    def __init__(self):
        self.bus = MessageBus()
        self.groups: Dict[str, GroupChat] = {}
        self.agent_groups: Dict[str, Set[str]] = {}  # agent_id -> set of group_ids
        
        # Subscribe to group messages
        self.bus.subscribe(MessageType.AGENT_MESSAGE, self._on_agent_message)
        
        logger.info("GroupChatManager initialized")
    
    def create_group(
        self,
        name: str,
        members: List[str],
        created_by: str,
        chat_type: GroupChatType = GroupChatType.DISCUSSION,
        topic: Optional[str] = None
    ) -> GroupChat:
        """
        Create a new group chat
        
        Args:
            name: Group name
            members: List of agent IDs to include
            created_by: Creator agent ID
            chat_type: Type of group chat
            topic: Optional topic/purpose
        """
        group_id = f"group-{str(uuid.uuid4())[:8]}"
        
        group = GroupChat(
            id=group_id,
            name=name,
            type=chat_type,
            members=set(members),
            created_by=created_by,
            created_at=datetime.now().isoformat(),
            topic=topic
        )
        
        self.groups[group_id] = group
        
        # Update agent index
        for member in members:
            if member not in self.agent_groups:
                self.agent_groups[member] = set()
            self.agent_groups[member].add(group_id)
        
        # Notify members
        self.broadcast_to_group(
            group_id=group_id,
            sender="system",
            content=f"Group '{name}' created by {created_by}. Topic: {topic or 'General discussion'}",
            exclude_sender=False
        )
        
        logger.info(f"Created group {group_id} with {len(members)} members")
        return group
    
    def add_member(self, group_id: str, agent_id: str, added_by: str) -> bool:
        """Add a member to a group"""
        if group_id not in self.groups:
            return False
        
        group = self.groups[group_id]
        group.members.add(agent_id)
        
        if agent_id not in self.agent_groups:
            self.agent_groups[agent_id] = set()
        self.agent_groups[agent_id].add(group_id)
        
        # Notify group
        self.broadcast_to_group(
            group_id=group_id,
            sender="system",
            content=f"{agent_id} was added to the group by {added_by}"
        )
        
        return True
    
    def remove_member(self, group_id: str, agent_id: str, removed_by: str) -> bool:
        """Remove a member from a group"""
        if group_id not in self.groups:
            return False
        
        group = self.groups[group_id]
        group.members.discard(agent_id)
        
        if agent_id in self.agent_groups:
            self.agent_groups[agent_id].discard(group_id)
        
        # Notify group
        self.broadcast_to_group(
            group_id=group_id,
            sender="system",
            content=f"{agent_id} was removed from the group by {removed_by}"
        )
        
        return True
    
    def send_to_group(
        self,
        group_id: str,
        sender: str,
        content: str,
        reply_to: Optional[str] = None
    ) -> Optional[GroupMessage]:
        """
        Send a message to a group
        
        Returns the created message or None if group doesn't exist
        """
        if group_id not in self.groups:
            return None
        
        group = self.groups[group_id]
        
        if sender not in group.members and sender != "system":
            logger.warning(f"Sender {sender} not in group {group_id}")
            return None
        
        # Parse mentions (@agent_name)
        mentions = []
        for word in content.split():
            if word.startswith("@"):
                mentions.append(word[1:])
        
        message = GroupMessage(
            id=f"msg-{str(uuid.uuid4())[:8]}",
            group_id=group_id,
            sender=sender,
            content=content,
            timestamp=datetime.now().isoformat(),
            mentions=mentions,
            reply_to=reply_to
        )
        
        group.messages.append(message)
        
        # Broadcast to all members
        for member in group.members:
            if member != sender:
                self.bus.send_to_agent(member, Message.create(
                    MessageType.AGENT_MESSAGE,
                    sender=sender,
                    recipient=member,
                    payload={
                        "content": content,
                        "group_id": group_id,
                        "group_name": group.name,
                        "message_id": message.id,
                        "is_group_message": True
                    }
                ))
        
        return message
    
    def broadcast_to_group(
        self,
        group_id: str,
        sender: str,
        content: str,
        exclude_sender: bool = True
    ):
        """Broadcast a message to all group members"""
        if group_id not in self.groups:
            return
        
        group = self.groups[group_id]
        
        for member in group.members:
            if exclude_sender and member == sender:
                continue
            
            self.bus.send_to_agent(member, Message.create(
                MessageType.AGENT_MESSAGE,
                sender=sender,
                recipient=member,
                payload={
                    "content": content,
                    "group_id": group_id,
                    "group_name": group.name,
                    "is_broadcast": True
                }
            ))
    
    def get_group(self, group_id: str) -> Optional[GroupChat]:
        """Get a group by ID"""
        return self.groups.get(group_id)
    
    def get_agent_groups(self, agent_id: str) -> List[GroupChat]:
        """Get all groups an agent is a member of"""
        group_ids = self.agent_groups.get(agent_id, set())
        return [self.groups[gid] for gid in group_ids if gid in self.groups]
    
    def list_groups(self) -> List[Dict[str, Any]]:
        """List all groups with summary info"""
        return [
            {
                "id": g.id,
                "name": g.name,
                "type": g.type.value,
                "members": list(g.members),
                "member_count": len(g.members),
                "message_count": len(g.messages),
                "topic": g.topic,
                "is_active": g.is_active,
                "created_at": g.created_at
            }
            for g in self.groups.values()
        ]
    
    def get_group_history(self, group_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get message history for a group"""
        if group_id not in self.groups:
            return []
        
        group = self.groups[group_id]
        messages = group.messages[-limit:]
        
        return [
            {
                "id": m.id,
                "sender": m.sender,
                "content": m.content,
                "timestamp": m.timestamp,
                "mentions": m.mentions,
                "reply_to": m.reply_to
            }
            for m in messages
        ]
    
    def close_group(self, group_id: str, closed_by: str) -> bool:
        """Close/deactivate a group"""
        if group_id not in self.groups:
            return False
        
        group = self.groups[group_id]
        group.is_active = False
        
        self.broadcast_to_group(
            group_id=group_id,
            sender="system",
            content=f"Group '{group.name}' was closed by {closed_by}"
        )
        
        return True
    
    def _on_agent_message(self, message: Message):
        """Handle agent messages for group routing"""
        # Check if message is intended for a group
        payload = message.payload
        group_id = payload.get("group_id")
        
        if group_id and group_id in self.groups:
            # This is a reply to a group message
            # Could implement threaded reply logic here
            pass
    
    def create_workflow_group(
        self,
        mission_id: str,
        mission_title: str,
        agents: List[str],
        created_by: str = "orchestrator"
    ) -> GroupChat:
        """
        Create a workflow group for a specific mission
        
        This creates a dedicated chat channel for all agents working on a mission.
        """
        return self.create_group(
            name=f"Mission: {mission_title}",
            members=agents,
            created_by=created_by,
            chat_type=GroupChatType.WORKFLOW,
            topic=f"Collaboration space for mission {mission_id}"
        )

# Global instance
group_chat_manager = GroupChatManager()
