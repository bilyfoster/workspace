#!/usr/bin/env python3
"""
Agent Runner for Workspace (Thread-based)

Runs an agent as a thread within the main process.
This allows the MessageBus singleton to work properly.
"""
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from herbie.core.ollama_client import OllamaClient, ChatMessage
from herbie.core.config import config
from shared.bus.message_bus import MessageBus, Message, MessageType
from shared.bus.handoff import handoff_manager, HandoffContext

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SoulManifest:
    """Parsed soul.md manifest"""
    name: str
    role: str
    avatar: str
    essence: str
    personality: List[str]
    values: List[str]
    voice: str
    expertise: List[str]
    model: str
    temperature: float

class AgentRunner:
    """
    Runs an agent in a thread (not a separate process)
    
    This allows proper communication via the shared MessageBus.
    """
    
    def __init__(self, agent_id: str, name: str, soul_path: Path, stop_event: threading.Event):
        self.id = agent_id
        self.name = name
        self.soul_path = soul_path
        self.stop_event = stop_event
        
        # Parse soul manifest
        self.soul = self._load_soul()
        
        # State
        self.status = "initializing"
        self.current_task: Optional[Dict] = None
        
        # Ollama client
        self.ollama = OllamaClient(config.ollama_host)
        
        # Message bus (shared with orchestrator - same process!)
        self.bus = MessageBus()
        self.message_queue: List[Message] = []
        
        # Conversation/memory
        self.messages: List[ChatMessage] = []
        self._load_memory()
        
        # Build system prompt from soul
        self._build_system_prompt()
        
        logger.info(f"AgentRunner {self.name} ({self.id}) initialized")
    
    def _load_soul(self) -> SoulManifest:
        """Parse the soul.md file"""
        content = self.soul_path.read_text()
        
        def extract_section(text: str, header: str) -> str:
            lines = text.split('\n')
            capturing = False
            result = []
            for line in lines:
                if line.startswith(f"## {header}") or line.startswith(f"# {header}"):
                    capturing = True
                    continue
                if capturing and line.startswith('#'):
                    break
                if capturing:
                    result.append(line)
            return '\n'.join(result).strip()
        
        def extract_list(text: str, header: str) -> List[str]:
            section = extract_section(text, header)
            return [line.strip('- ').strip() for line in section.split('\n') if line.strip().startswith('-')]
        
        def extract_field(text: str, field: str) -> str:
            for line in text.split('\n'):
                if line.startswith(f'**{field}:**'):
                    return line.split(':', 1)[1].strip().strip('*')
            return ""
        
        # Extract model config from YAML block
        model = config.default_model
        temperature = 0.7
        if 'model:' in content:
            for line in content.split('\n'):
                if 'model:' in line and not line.strip().startswith('#'):
                    model = line.split(':')[1].strip()
                if 'temperature:' in line:
                    try:
                        temperature = float(line.split(':')[1].strip())
                    except:
                        pass
        
        return SoulManifest(
            name=extract_field(content, 'Name'),
            role=extract_field(content, 'Role'),
            avatar=extract_field(content, 'Avatar'),
            essence=extract_section(content, 'Essence'),
            personality=extract_list(content, 'Personality Traits'),
            values=extract_list(content, 'Core Values'),
            voice=extract_section(content, 'Voice & Tone'),
            expertise=extract_list(content, 'Expertise'),
            model=model,
            temperature=temperature
        )
    
    def _build_system_prompt(self):
        """Build the system prompt from soul manifest"""
        expertise = '\n'.join([f"- {e}" for e in self.soul.expertise])
        values = '\n'.join([f"- {v}" for v in self.soul.values])
        personality = ', '.join(self.soul.personality[:3])
        
        system_prompt = f"""You are {self.soul.name}, {self.soul.role}.

{self.soul.essence}

Core Values:
{values}

Your Expertise:
{expertise}

Voice & Tone: {self.soul.voice}

Personality: {personality}

Guidelines:
- Stay in character as {self.soul.name}
- Be concise but thorough
- Acknowledge when something is outside your expertise
- Think step-by-step for complex tasks"""

        self.messages.append(ChatMessage(role="system", content=system_prompt))
    
    def _load_memory(self):
        """Load conversation memory from disk"""
        import json
        memory_file = self.soul_path.parent / 'memory' / 'conversations.json'
        if memory_file.exists():
            try:
                data = json.loads(memory_file.read_text())
                for msg in data.get('messages', [])[-10:]:
                    self.messages.append(ChatMessage(**msg))
                logger.info(f"Loaded {len(data.get('messages', []))} messages from memory")
            except Exception as e:
                logger.warning(f"Failed to load memory: {e}")
    
    def _save_memory(self):
        """Save conversation memory to disk"""
        import json
        try:
            memory_dir = self.soul_path.parent / 'memory'
            memory_dir.mkdir(parents=True, exist_ok=True)
            memory_file = memory_dir / 'conversations.json'
            data = {
                'messages': [{'role': m.role, 'content': m.content} for m in self.messages],
                'last_updated': time.time()
            }
            memory_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def run(self):
        """Main agent loop - runs in thread"""
        logger.info(f"Starting agent thread {self.name} ({self.id})")
        
        # Register with message bus
        # For threads, we use a simple list-based queue
        self._setup_message_handler()
        
        # Announce online
        self.bus.publish(Message.create(
            MessageType.AGENT_ONLINE,
            sender=self.id,
            payload={
                'name': self.soul.name,
                'role': self.soul.role,
                'avatar': self.soul.avatar,
                'model': self.soul.model
            }
        ))
        
        self.status = "idle"
        logger.info(f"Agent {self.name} is now online and idle")
        
        # Main loop
        while not self.stop_event.is_set():
            try:
                # Process any pending messages
                if self.message_queue:
                    message = self.message_queue.pop(0)
                    self._handle_message(message)
                
                time.sleep(0.1)  # Small sleep to prevent busy-waiting
                
            except Exception as e:
                logger.exception(f"Error in agent {self.name} loop")
                self.status = "error"
        
        # Shutdown
        logger.info(f"Agent {self.name} shutting down")
        self.bus.publish(Message.create(
            MessageType.AGENT_OFFLINE,
            sender=self.id,
            payload={'name': self.soul.name}
        ))
        self._save_memory()
    
    def _setup_message_handler(self):
        """Set up a handler to receive messages"""
        # Store reference to ourselves in the bus's agent_queues
        # Using a list as a queue for thread safety
        self.bus._agent_queues[self.id] = self.message_queue
    
    def _handle_message(self, message: Message):
        """Handle incoming messages"""
        logger.info(f"Agent {self.name} received {message.type} from {message.sender}")
        
        if message.type == MessageType.TASK_ASSIGNED.value:
            self._handle_task(message)
        
        elif message.type == MessageType.AGENT_MESSAGE.value:
            # Another agent is messaging us
            response = self._chat(message.payload.get('content', ''))
            self.bus.publish(Message.create(
                MessageType.AGENT_MESSAGE,
                sender=self.id,
                recipient=message.sender,
                payload={'content': response},
                correlation_id=message.correlation_id
            ))
        
        elif message.type == MessageType.USER_MESSAGE.value:
            # User is messaging us directly
            response = self._chat(message.payload.get('content', ''))
            self.bus.publish(Message.create(
                MessageType.AGENT_MESSAGE,
                sender=self.id,
                recipient=message.sender,
                payload={'content': response},
                correlation_id=message.correlation_id
            ))
        
        elif message.type == MessageType.HANDOFF_REQUEST.value:
            # Received a handoff request
            self._handle_handoff_request(message)
        
        elif message.type == MessageType.HANDOFF_ACCEPT.value:
            # Our handoff was accepted or rejected
            self._handle_handoff_response(message)
        
        elif message.type == 'ping':
            # Respond to ping
            self.bus.publish(Message.create(
                MessageType.AGENT_STATUS,
                sender=self.id,
                recipient=message.sender,
                payload={'status': self.status, 'pong': True}
            ))
    
    def _handle_task(self, message: Message):
        """Execute an assigned task"""
        task = message.payload
        self.current_task = task
        self.status = "working"
        
        # Announce task start
        self.bus.publish(Message.create(
            MessageType.TASK_STARTED,
            sender=self.id,
            payload={
                'task_id': task.get('id'),
                'description': task.get('description')
            },
            correlation_id=message.correlation_id
        ))
        
        try:
            # Build task prompt
            task_prompt = f"Task: {task.get('description')}\n\n"
            if task.get('context'):
                import json
                task_prompt += f"Context: {json.dumps(task.get('context'))}\n\n"
            
            # Execute
            self.messages.append(ChatMessage(role="user", content=task_prompt))
            
            response_content = ""
            for response in self.ollama.chat(
                model=self.soul.model,
                messages=self.messages,
                stream=False,
                temperature=self.soul.temperature
            ):
                response_content += response.message.content
            
            self.messages.append(ChatMessage(role="assistant", content=response_content))
            
            # Save memory
            self._save_memory()
            
            # Announce completion
            self.bus.publish(Message.create(
                MessageType.TASK_COMPLETED,
                sender=self.id,
                payload={
                    'task_id': task.get('id'),
                    'result': response_content,
                    'model_used': self.soul.model
                },
                correlation_id=message.correlation_id
            ))
            
        except Exception as e:
            logger.exception("Task execution failed")
            self.bus.publish(Message.create(
                MessageType.TASK_FAILED,
                sender=self.id,
                payload={
                    'task_id': task.get('id'),
                    'error': str(e)
                },
                correlation_id=message.correlation_id
            ))
        
        finally:
            self.current_task = None
            self.status = "idle"
    
    def _chat(self, message: str) -> str:
        """Handle a chat message"""
        self.messages.append(ChatMessage(role="user", content=message))
        
        response_content = ""
        for response in self.ollama.chat(
            model=self.soul.model,
            messages=self.messages,
            stream=False,
            temperature=self.soul.temperature
        ):
            response_content += response.message.content
        
        self.messages.append(ChatMessage(role="assistant", content=response_content))
        self._save_memory()
        
        return response_content
    
    def _handle_handoff_request(self, message: Message):
        """Handle an incoming handoff request"""
        payload = message.payload
        context = payload.get('context', {})
        
        logger.info(f"Agent {self.name} received handoff request from {message.sender}")
        
        # Build prompt from handoff context
        handoff_prompt = f"""You've been handed off a task from another agent.

**Original Task:** {context.get('original_task', 'Unknown')}

**Work Already Done:**
{context.get('work_done', 'None documented')}

**Key Findings:**
"""
        for key, finding in context.get('findings', {}).items():
            handoff_prompt += f"- {finding}\n"
        
        handoff_prompt += f"""
**Suggested Next Steps:**
"""
        for step in context.get('next_steps', []):
            handoff_prompt += f"- {step}\n"
        
        handoff_prompt += f"""
**Notes:** {context.get('notes', 'None')}

Please review this handoff and acknowledge that you understand the task and can proceed. If you need clarification, state what you need."""

        # Have the agent process the handoff
        response = self._chat(handoff_prompt)
        
        # Accept the handoff
        handoff_manager.accept_handoff(payload.get('id'), self.id, notes=response[:200])
        
        # Notify orchestrator
        self.bus.publish(Message.create(
            MessageType.AGENT_MESSAGE,
            sender=self.id,
            recipient=message.sender,
            payload={'content': f"Handoff accepted. I'm ready to proceed.\n\nMy understanding: {response[:300]}..."},
            correlation_id=message.correlation_id
        ))
    
    def _handle_handoff_response(self, message: Message):
        """Handle handoff acceptance/rejection"""
        payload = message.payload
        accepted = payload.get('accepted', False)
        
        if accepted:
            logger.info(f"Handoff was accepted by {message.sender}")
        else:
            logger.warning(f"Handoff was rejected: {payload.get('reason')}")
