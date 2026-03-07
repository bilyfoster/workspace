"""Ollama API client for local LLM inference"""
import requests
import json
import logging
from typing import Iterator, Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant"
    content: str

@dataclass
class ChatResponse:
    message: ChatMessage
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None

class OllamaClient:
    """Client for Ollama API"""
    
    def __init__(self, host: str = "http://localhost:11434", timeout: int = 120):
        self.host = host.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        logger.info(f"Ollama client initialized: {host}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models from Ollama"""
        try:
            response = self.session.get(f"{self.host}/api/tags", timeout=self.timeout)
            response.raise_for_status()
            return response.json().get('models', [])
        except requests.RequestException as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    def chat(
        self,
        model: str,
        messages: List[ChatMessage],
        stream: bool = False,
        temperature: float = 0.7,
        **kwargs
    ) -> Iterator[ChatResponse]:
        """
        Send chat completion request to Ollama
        
        Args:
            model: Model name (e.g., "qwen3.5:9b")
            messages: List of ChatMessage objects
            stream: Whether to stream the response
            temperature: Sampling temperature
            **kwargs: Additional options (top_p, top_k, etc.)
        
        Yields:
            ChatResponse objects
        """
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "options": {
                "temperature": temperature,
                **kwargs
            }
        }
        
        try:
            response = self.session.post(
                f"{self.host}/api/chat",
                json=payload,
                stream=stream,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if stream:
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        yield self._parse_response(data)
            else:
                yield self._parse_response(response.json())
                
        except requests.RequestException as e:
            logger.error(f"Ollama API error: {e}")
            raise
    
    def chat_complete(
        self,
        model: str,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Simple chat completion that returns just the content string"""
        full_response = ""
        for response in self.chat(model, messages, stream=False, temperature=temperature, **kwargs):
            full_response += response.message.content
        return full_response
    
    def _parse_response(self, data: Dict[str, Any]) -> ChatResponse:
        """Parse Ollama API response into ChatResponse"""
        message_data = data.get('message', {})
        return ChatResponse(
            message=ChatMessage(
                role=message_data.get('role', 'assistant'),
                content=message_data.get('content', '')
            ),
            done=data.get('done', False),
            total_duration=data.get('total_duration'),
            load_duration=data.get('load_duration'),
            prompt_eval_count=data.get('prompt_eval_count'),
            eval_count=data.get('eval_count')
        )
    
    def is_healthy(self) -> bool:
        """Check if Ollama server is reachable"""
        try:
            response = self.session.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
