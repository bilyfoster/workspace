"""
Workspace Shared Message Bus

Enables communication between:
- Orchestrator ↔ Agents
- Agent ↔ Agent
- Dashboard ↔ System
"""
from shared.bus.message_bus import MessageBus, Message, MessageType

__all__ = ['MessageBus', 'Message', 'MessageType']
