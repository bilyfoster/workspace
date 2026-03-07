"""Load and manage agent personas from YAML files"""
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from herbie.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

@dataclass
class Persona:
    """Agent persona definition"""
    name: str
    role: str
    personality: str
    skills: List[str]
    model: Optional[str] = None
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    avatar: Optional[str] = None  # Emoji or short string
    
    @classmethod
    def from_yaml(cls, path: Path) -> "Persona":
        """Load persona from YAML file"""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(
            name=data.get('name'),
            role=data.get('role'),
            personality=data.get('personality', ''),
            skills=data.get('skills', []),
            model=data.get('model'),
            temperature=data.get('temperature', 0.7),
            system_prompt=data.get('system_prompt'),
            avatar=data.get('avatar', '🤖')
        )

class PersonaRegistry:
    """Registry of available agent personas"""
    
    def __init__(self, personas_dir: str = "./personas"):
        self.personas_dir = Path(personas_dir)
        self._personas: Dict[str, Persona] = {}
        self._load_personas()
    
    def _load_personas(self):
        """Load all personas from the personas directory"""
        if not self.personas_dir.exists():
            logger.warning(f"Personas directory not found: {self.personas_dir}")
            return
        
        for file_path in self.personas_dir.glob("*.yaml"):
            try:
                persona = Persona.from_yaml(file_path)
                self._personas[persona.name.lower()] = persona
                logger.info(f"Loaded persona: {persona.name}")
            except Exception as e:
                logger.error(f"Failed to load persona from {file_path}: {e}")
    
    def get(self, name: str) -> Optional[Persona]:
        """Get a persona by name (case-insensitive)"""
        return self._personas.get(name.lower())
    
    def list_personas(self) -> List[str]:
        """List all available persona names"""
        return list(self._personas.keys())
    
    def create_agent(self, name: str) -> Optional[BaseAgent]:
        """Create an agent instance from a persona"""
        persona = self.get(name)
        if not persona:
            logger.error(f"Persona not found: {name}")
            return None
        
        return BaseAgent(
            name=persona.name,
            role=persona.role,
            personality=persona.personality,
            skills=persona.skills,
            model=persona.model,
            temperature=persona.temperature,
            system_prompt=persona.system_prompt
        )
    
    def reload(self):
        """Reload all personas from disk"""
        self._personas.clear()
        self._load_personas()

# Global registry instance
registry = PersonaRegistry()
