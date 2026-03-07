#!/usr/bin/env python3
"""
Agent Factory - Dynamic Agent Creation

Allows creating new agents on-the-fly with custom roles and capabilities.
"""
import time
import re
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class AgentTemplate:
    """Template for creating a new agent"""
    name: str
    role: str
    avatar: str
    essence: str
    skills: List[str]
    model: str = "qwen3.5:9b"
    temperature: float = 0.7


class AgentFactory:
    """Factory for creating new agent souls dynamically"""
    
    # Pre-defined templates for common roles
    TEMPLATES = {
        "data_analyst": AgentTemplate(
            name="{name}",
            role="Data Analyst",
            avatar="📊",
            essence="You are a meticulous data analyst who excels at finding patterns, creating visualizations, and extracting insights from complex datasets.",
            skills=["Statistical analysis", "Data visualization", "SQL", "Python/pandas", "Report writing"],
            model="qwen3.5:9b"
        ),
        "legal_expert": AgentTemplate(
            name="{name}",
            role="Legal Consultant",
            avatar="⚖️",
            essence="You are a knowledgeable legal consultant who reviews contracts, identifies risks, and provides guidance on legal matters.",
            skills=["Contract review", "Risk assessment", "Regulatory compliance", "Legal research", "Documentation"],
            model="qwen3.5:9b"
        ),
        "financial_analyst": AgentTemplate(
            name="{name}",
            role="Financial Analyst",
            avatar="💰",
            essence="You are a sharp financial analyst who evaluates investments, creates forecasts, and provides strategic financial guidance.",
            skills=["Financial modeling", "Investment analysis", "Budget planning", "Risk assessment", "Market research"],
            model="qwen3.5:9b"
        ),
        "customer_support": AgentTemplate(
            name="{name}",
            role="Customer Support Specialist",
            avatar="🎧",
            essence="You are an empathetic customer support specialist who resolves issues, answers questions, and ensures customer satisfaction.",
            skills=["Issue resolution", "Communication", "Product knowledge", "Ticket management", "Customer relations"],
            model="dolphin3"
        ),
        "content_moderator": AgentTemplate(
            name="{name}",
            role="Content Moderator",
            avatar="🔍",
            essence="You are a vigilant content moderator who reviews content for policy compliance, identifies issues, and maintains community standards.",
            skills=["Content review", "Policy enforcement", "Quality assurance", "Report writing", "Community guidelines"],
            model="qwen3.5:9b"
        ),
        "devops_engineer": AgentTemplate(
            name="{name}",
            role="DevOps Engineer",
            avatar="🔧",
            essence="You are a skilled DevOps engineer who manages infrastructure, automates deployments, and ensures system reliability.",
            skills=["CI/CD pipelines", "Infrastructure as Code", "Docker/Kubernetes", "Monitoring", "Cloud platforms"],
            model="qwen3-coder"
        ),
        "qa_tester": AgentTemplate(
            name="{name}",
            role="QA Tester",
            avatar="🐞",
            essence="You are a thorough QA tester who finds bugs, writes test cases, and ensures software quality.",
            skills=["Test planning", "Bug reporting", "Automated testing", "Regression testing", "User acceptance testing"],
            model="qwen3-coder"
        ),
        "ux_researcher": AgentTemplate(
            name="{name}",
            role="UX Researcher",
            avatar="🧪",
            essence="You are an insightful UX researcher who understands user needs, conducts studies, and drives design decisions.",
            skills=["User interviews", "Usability testing", "Survey design", "Journey mapping", "Insight synthesis"],
            model="gemma3"
        ),
        "technical_writer": AgentTemplate(
            name="{name}",
            role="Technical Writer",
            avatar="📝",
            essence="You are a clear technical writer who creates documentation, API guides, and user manuals.",
            skills=["Documentation", "API docs", "User guides", "Technical editing", "Information architecture"],
            model="gemma3"
        ),
        "sales_representative": AgentTemplate(
            name="{name}",
            role="Sales Representative",
            avatar="💼",
            essence="You are a persuasive sales representative who identifies opportunities, builds relationships, and closes deals.",
            skills=["Lead generation", "Product demos", "Negotiation", "CRM management", "Relationship building"],
            model="dolphin3"
        ),
        "product_manager": AgentTemplate(
            name="{name}",
            role="Product Manager",
            avatar="📱",
            essence="You are a strategic product manager who defines roadmaps, prioritizes features, and drives product success.",
            skills=["Roadmap planning", "Feature prioritization", "User stories", "Market analysis", "Stakeholder management"],
            model="qwen3.5:9b"
        ),
    }
    
    def __init__(self, agents_dir: Path = Path("./agents")):
        self.agents_dir = agents_dir
        
    def create_agent_from_template(
        self, 
        template_key: str, 
        name: str,
        custom_skills: Optional[List[str]] = None
    ) -> Optional[Path]:
        """
        Create a new agent from a predefined template
        
        Args:
            template_key: Key from TEMPLATES dict
            name: Name for the new agent
            custom_skills: Optional additional skills
            
        Returns:
            Path to created soul.md or None if failed
        """
        if template_key not in self.TEMPLATES:
            return None
        
        template = self.TEMPLATES[template_key]
        skills = custom_skills or template.skills
        
        return self._create_soul_file(
            name=name,
            role=template.role,
            avatar=template.avatar,
            essence=template.essence,
            skills=skills,
            model=template.model,
            temperature=template.temperature
        )
    
    def create_custom_agent(
        self,
        name: str,
        role: str,
        avatar: str,
        essence: str,
        skills: List[str],
        model: str = "qwen3.5:9b",
        temperature: float = 0.7
    ) -> Optional[Path]:
        """
        Create a completely custom agent
        
        Args:
            name: Agent name
            role: Job title/role
            avatar: Emoji avatar
            essence: Core personality description
            skills: List of skills
            model: Ollama model to use
            temperature: Response creativity (0.0-1.0)
            
        Returns:
            Path to created soul.md or None if failed
        """
        return self._create_soul_file(
            name=name, role=role, avatar=avatar, essence=essence,
            skills=skills, model=model, temperature=temperature
        )
    
    def _create_soul_file(
        self,
        name: str,
        role: str,
        avatar: str,
        essence: str,
        skills: List[str],
        model: str,
        temperature: float
    ) -> Optional[Path]:
        """Create the soul.md file"""
        # Sanitize name for directory
        dir_name = re.sub(r'[^a-z0-9_]', '', name.lower().replace(' ', '_'))
        if not dir_name:
            dir_name = f"agent_{int(time.time())}"
        
        agent_dir = self.agents_dir / dir_name
        
        # Check if already exists
        if agent_dir.exists():
            # Append number
            counter = 1
            while (self.agents_dir / f"{dir_name}_{counter}").exists():
                counter += 1
            dir_name = f"{dir_name}_{counter}"
            agent_dir = self.agents_dir / dir_name
        
        try:
            agent_dir.mkdir(parents=True, exist_ok=True)
            
            # Build soul.md content
            skills_md = '\n'.join([f"- {skill}" for skill in skills])
            
            soul_content = f"""# {name} - {role}

**Name:** {name}  
**Role:** {role}  
**Avatar:** {avatar}  
**Model:** {model}  
**Temperature:** {temperature}

---

## Essence

{essence}

---

## Personality Traits

- Professional and capable
- Focused on delivering quality work
- Collaborative with other team members
- Proactive in communication

---

## Core Values

1. **Excellence**: Deliver high-quality work
2. **Reliability**: Meet commitments and deadlines
3. **Collaboration**: Work effectively with the team
4. **Growth**: Continuously improve skills

---

## Voice & Tone

Professional, clear, and confident. Communicate in a way that's appropriate for your role while remaining approachable.

---

## Expertise

{skills_md}

---

## Created

Dynamically created by Agent Factory v1.4.0
"""
            
            soul_path = agent_dir / "soul.md"
            soul_path.write_text(soul_content)
            
            return soul_path
            
        except Exception as e:
            print(f"Failed to create agent: {e}")
            return None
    
    def list_templates(self) -> Dict[str, str]:
        """List available templates with descriptions"""
        return {
            key: f"{template.avatar} {template.role}"
            for key, template in self.TEMPLATES.items()
        }
    
    def agent_exists(self, name: str) -> bool:
        """Check if an agent with this name already exists"""
        dir_name = re.sub(r'[^a-z0-9_]', '', name.lower().replace(' ', '_'))
        return (self.agents_dir / dir_name).exists()


# Global instance
agent_factory = AgentFactory()
