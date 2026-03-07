"""
Persistent Chat History for Workspace

Saves and loads chat conversations to disk.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    """A single chat message"""
    role: str  # "user" or "agent"
    content: str
    timestamp: str
    agent_name: Optional[str] = None
    agent_id: Optional[str] = None

class ChatHistoryManager:
    """
    Manages persistent chat history
    
    Saves conversations to disk so they survive restarts.
    """
    
    def __init__(self, storage_dir: str = "./chat_history"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        logger.info(f"ChatHistoryManager initialized: {storage_dir}")
    
    def _get_chat_file(self, agent_id: str) -> Path:
        """Get the file path for an agent's chat history"""
        return self.storage_dir / f"{agent_id}.json"
    
    def save_message(self, agent_id: str, agent_name: str, role: str, content: str):
        """
        Save a chat message
        
        Args:
            agent_id: Agent's unique ID
            agent_name: Agent's display name
            role: "user" or "agent"
            content: Message content
        """
        chat_file = self._get_chat_file(agent_id)
        
        # Load existing history
        history = self.load_history(agent_id)
        
        # Add new message
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            agent_name=agent_name,
            agent_id=agent_id
        )
        history.append(message)
        
        # Save back to disk
        try:
            data = {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "updated_at": datetime.now().isoformat(),
                "messages": [asdict(m) for m in history]
            }
            chat_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Saved chat message for {agent_name}")
        except Exception as e:
            logger.error(f"Failed to save chat history: {e}")
    
    def load_history(self, agent_id: str) -> List[ChatMessage]:
        """
        Load chat history for an agent
        
        Args:
            agent_id: Agent's unique ID
            
        Returns:
            List of chat messages
        """
        chat_file = self._get_chat_file(agent_id)
        
        if not chat_file.exists():
            return []
        
        try:
            data = json.loads(chat_file.read_text())
            messages = [ChatMessage(**m) for m in data.get("messages", [])]
            return messages
        except Exception as e:
            logger.error(f"Failed to load chat history: {e}")
            return []
    
    def load_all_chats(self) -> Dict[str, List[ChatMessage]]:
        """
        Load all chat histories
        
        Returns:
            Dict mapping agent_id to message list
        """
        all_chats = {}
        
        for chat_file in self.storage_dir.glob("*.json"):
            agent_id = chat_file.stem
            history = self.load_history(agent_id)
            if history:
                all_chats[agent_id] = history
        
        return all_chats
    
    def clear_history(self, agent_id: str):
        """Clear chat history for an agent"""
        chat_file = self._get_chat_file(agent_id)
        if chat_file.exists():
            chat_file.unlink()
            logger.info(f"Cleared chat history for {agent_id}")
    
    def clear_all_history(self):
        """Clear all chat history"""
        for chat_file in self.storage_dir.glob("*.json"):
            chat_file.unlink()
        logger.info("Cleared all chat history")
    
    def export_chat(self, agent_id: str, format: str = "markdown") -> Optional[Path]:
        """
        Export chat history to file
        
        Args:
            agent_id: Agent's unique ID
            format: 'markdown' or 'txt'
        """
        history = self.load_history(agent_id)
        if not history:
            return None
        
        agent_name = history[0].agent_name or agent_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        exports_dir = Path("./exports/chats")
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        if format == "markdown":
            filepath = exports_dir / f"{agent_name}_chat_{timestamp}.md"
            
            content = f"# Chat with {agent_name}\n\n"
            for msg in history:
                role_label = "**You**" if msg.role == "user" else f"**{agent_name}**"
                content += f"{role_label}: {msg.content}\n\n"
            
            filepath.write_text(content)
        else:
            filepath = exports_dir / f"{agent_name}_chat_{timestamp}.txt"
            
            lines = [f"Chat with {agent_name}", "="*50, ""]
            for msg in history:
                role_label = "You" if msg.role == "user" else agent_name
                lines.append(f"[{msg.timestamp[:16]}] {role_label}:")
                lines.append(msg.content)
                lines.append("")
            
            filepath.write_text("\n".join(lines))
        
        logger.info(f"Exported chat to {filepath}")
        return filepath

# Global instance
chat_history = ChatHistoryManager()
