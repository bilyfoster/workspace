#!/usr/bin/env python3
"""
Standalone Agent Process for Workspace

Each agent runs as a separate process with:
- Its own soul.md (identity, values, personality)
- Its own memory/conversation history
- Direct Ollama connection (can use different models)
- Message bus connection to orchestrator

Usage:
    python agent_process.py --name hunter --soul ./agents/hunter/soul.md
"""
import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))

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
    memory_path: Path
    knowledge_path: Path

class SubAgent:
    """
    A full sub-agent process with its own identity and memory
    """
    
    def __init__(self, name: str, soul_path: Path):
        self.name = name
        self.soul_path = soul_path
        self.agent_dir = soul_path.parent
        
        # Parse soul manifest
        self.soul = self._load_soul()
        
        # State
        self.id = f"{self.soul.name.lower()}-{int(time.time())}"
        self.status = "initializing"
        self.current_task: Optional[Dict] = None
        
        # Ollama client (separate connection)
        self.ollama = OllamaClient(config.ollama_host)
        
        # Message bus
        self.bus = MessageBus()
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Conversation/memory
        self.messages: List[ChatMessage] = []
        self._load_memory()
        
        # Build system prompt from soul
        self._build_system_prompt()
        
        # Shutdown flag
        self._shutdown = False
        
        logger.info(f"Agent {self.name} initialized with soul from {soul_path}")
    
    def _load_soul(self) -> SoulManifest:
        """Parse the soul.md file"""
        content = self.soul_path.read_text()
        
        # Simple markdown parsing
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
        
        # Extract model config from YAML block
        model = config.default_model
        temperature = 0.7
        if 'model:' in content:
            for line in content.split('\n'):
                if 'model:' in line and not line.strip().startswith('#'):
                    model = line.split(':')[1].strip()
                if 'temperature:' in line:
                    temperature = float(line.split(':')[1].strip())
        
        return SoulManifest(
            name=self._extract_field(content, 'Name'),
            role=self._extract_field(content, 'Role'),
            avatar=self._extract_field(content, 'Avatar'),
            essence=extract_section(content, 'Essence'),
            personality=extract_list(content, 'Personality Traits'),
            values=extract_list(content, 'Core Values'),
            voice=extract_section(content, 'Voice & Tone'),
            expertise=extract_list(content, 'Expertise'),
            model=model,
            temperature=temperature,
            memory_path=self.agent_dir / 'memory',
            knowledge_path=self.agent_dir / 'knowledge'
        )
    
    def _extract_field(self, content: str, field: str) -> str:
        """Extract a simple field like 'Name: value'"""
        for line in content.split('\n'):
            if line.startswith(f'**{field}:**'):
                return line.split(':', 1)[1].strip().strip('*')
        return ""
    
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
        memory_file = self.soul.memory_path / 'conversations.json'
        if memory_file.exists():
            try:
                data = json.loads(memory_file.read_text())
                for msg in data.get('messages', [])[-10:]:  # Last 10 messages
                    self.messages.append(ChatMessage(**msg))
                logger.info(f"Loaded {len(data.get('messages', []))} messages from memory")
            except Exception as e:
                logger.warning(f"Failed to load memory: {e}")
    
    def _save_memory(self):
        """Save conversation memory to disk"""
        try:
            self.soul.memory_path.mkdir(parents=True, exist_ok=True)
            memory_file = self.soul.memory_path / 'conversations.json'
            data = {
                'messages': [{'role': m.role, 'content': m.content} for m in self.messages],
                'last_updated': time.time()
            }
            memory_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    async def start(self):
        """Start the agent process"""
        logger.info(f"Starting agent {self.name} ({self.id})")
        
        # Register with message bus
        self.bus.register_agent_queue(self.id, self.message_queue)
        
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
        
        # Main message loop
        while not self._shutdown:
            try:
                # Wait for messages with timeout
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                await self._handle_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.exception("Error in message loop")
    
    async def _handle_message(self, message: Message):
        """Handle incoming messages"""
        logger.info(f"Received {message.type} from {message.sender}")
        
        if message.type == MessageType.TASK_ASSIGNED.value:
            await self._handle_task(message)
        
        elif message.type == MessageType.AGENT_MESSAGE.value:
            # Another agent is messaging us
            response = await self._chat(message.payload.get('content', ''))
            self.bus.publish(Message.create(
                MessageType.AGENT_MESSAGE,
                sender=self.id,
                recipient=message.sender,
                payload={'content': response},
                correlation_id=message.correlation_id
            ))
        
        elif message.type == MessageType.USER_MESSAGE.value:
            # User is messaging us directly
            response = await self._chat(message.payload.get('content', ''))
            self.bus.publish(Message.create(
                MessageType.AGENT_MESSAGE,
                sender=self.id,
                recipient=message.sender,
                payload={'content': response},
                correlation_id=message.correlation_id
            ))
        
        elif message.type == MessageType.HANDOFF_REQUEST.value:
            # Received a handoff request
            await self._handle_handoff_request(message)
        
        elif message.type == MessageType.HANDOFF_ACCEPT.value:
            # Our handoff was accepted or rejected
            await self._handle_handoff_response(message)
    
    async def _handle_task(self, message: Message):
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
    
    async def _chat(self, message: str) -> str:
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
    
    async def _handle_handoff_request(self, message: Message):
        """Handle an incoming handoff request"""
        payload = message.payload
        context = payload.get('context', {})
        
        logger.info(f"Received handoff request from {message.sender}")
        
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
        response = await self._chat(handoff_prompt)
        
        # Accept the handoff (agents auto-accept for now)
        handoff_manager.accept_handoff(payload.get('id'), self.id, notes=response[:200])
        
        # Notify orchestrator
        self.bus.publish(Message.create(
            MessageType.AGENT_MESSAGE,
            sender=self.id,
            recipient=message.sender,
            payload={'content': f"Handoff accepted. I'm ready to proceed.\n\nMy understanding: {response[:300]}..."},
            correlation_id=message.correlation_id
        ))
    
    async def _handle_handoff_response(self, message: Message):
        """Handle handoff acceptance/rejection"""
        payload = message.payload
        accepted = payload.get('accepted', False)
        
        if accepted:
            logger.info(f"Handoff {payload.get('handoff_id')} was accepted by {message.sender}")
        else:
            logger.warning(f"Handoff {payload.get('handoff_id')} was rejected: {payload.get('reason')}")
    
    async def request_handoff_to(
        self,
        to_agent_id: str,
        original_task: str,
        work_done: str,
        next_steps: list,
        reason: str = ""
    ) -> str:
        """Request to handoff current work to another agent"""
        context = HandoffContext(
            original_task=original_task,
            work_done=work_done,
            findings={},  # Could extract from memory
            next_steps=next_steps,
            questions=[],
            files=[],
            notes=reason
        )
        
        handoff_id = handoff_manager.request_handoff(
            from_agent=self.id,
            to_agent=to_agent_id,
            context=context,
            reason=reason
        )
        
        return handoff_id
    
    def stop(self):
        """Graceful shutdown"""
        logger.info(f"Stopping agent {self.name}")
        self._shutdown = True
        self.bus.unregister_agent_queue(self.id)
        self.bus.publish(Message.create(
            MessageType.AGENT_OFFLINE,
            sender=self.id,
            payload={'name': self.soul.name}
        ))
        self._save_memory()

def main():
    parser = argparse.ArgumentParser(description='Workspace Sub-Agent Process')
    parser.add_argument('--name', required=True, help='Agent name')
    parser.add_argument('--soul', required=True, help='Path to soul.md')
    args = parser.parse_args()
    
    soul_path = Path(args.soul)
    if not soul_path.exists():
        logger.error(f"Soul file not found: {soul_path}")
        sys.exit(1)
    
    agent = SubAgent(args.name, soul_path)
    
    # Handle signals
    def signal_handler(sig, frame):
        agent.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        agent.stop()

if __name__ == "__main__":
    main()
