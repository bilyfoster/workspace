#!/usr/bin/env python3
"""
Agent Tools - Functions agents can actually execute

Inspired by swarms' approach - agents don't just talk, they DO things.
The Manager can call these tools to actually spawn agents, check status, etc.
"""
import json
import re
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class ToolCall:
    """A tool call from an agent"""
    tool_name: str
    arguments: Dict[str, Any]
    raw_text: str  # The original text that triggered this


class AgentTool:
    """A tool that an agent can call"""
    
    def __init__(self, name: str, description: str, func: Callable, params: Dict):
        self.name = name
        self.description = description
        self.func = func
        self.params = params
        
    def execute(self, **kwargs) -> str:
        """Execute the tool with given arguments"""
        try:
            result = self.func(**kwargs)
            return json.dumps({"success": True, "result": result})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


class ToolRegistry:
    """
    Registry of tools available to agents
    
    Tools can be called by agents via patterns like:
    - [tool:spawn_agent]{"name": "code"}
    - ```json\n{"tool": "spawn_agent", "name": "code"}\n```
    """
    
    # Pattern to detect tool calls in agent responses
    # Supports multiple formats:
    # - [tool:name]{"arg": "value"}
    # - ```json {"tool": "name", "arg": "value"} ```
    # - ```json [tool:name]{"arg": "value"} ```  (LLM sometimes wraps in code blocks)
    # - TOOL_CALL: name : {"arg": "value"}
    # Note: We use a non-greedy match for JSON args to handle nested braces
    TOOL_PATTERN = re.compile(
        r'```(?:json)?\s*\n?\[tool:(\w+)\](\{.*?\})\n?```'  # ```json [tool:name]{...} ``` (non-greedy)
        r'|\[tool:(\w+)\](\{[^\}]*(?:\{[^\}]*\}[^\}]*)*\})'  # [tool:name]{"arg": "value"} with nested braces
        r'|```(?:json)?\s*\n?(\{[^\}]*"tool"[^\}]*\})\n?```'  # ```json {"tool": "name"} ```
        r'|TOOL_CALL:\s*(\w+)\s*:\s*(\{[^\}]*\})',  # TOOL_CALL: name : {"arg": "value"}
        re.DOTALL | re.IGNORECASE
    )
    
    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.tools: Dict[str, AgentTool] = {}
        self._register_default_tools()
        
    def _register_default_tools(self):
        """Register default tools if orchestrator is available"""
        if not self.orchestrator:
            return
            
        # Tool: spawn_agent
        self.register_tool(
            name="spawn_agent",
            description="Spawn a new agent by name (e.g., 'code', 'pixel', 'shuri')",
            func=self._tool_spawn_agent,
            params={"name": "Name of agent to spawn (required)"}
        )
        
        # Tool: kill_agent
        self.register_tool(
            name="kill_agent",
            description="Stop/kill a running agent by name",
            func=self._tool_kill_agent,
            params={"name": "Name of agent to kill (required)"}
        )
        
        # Tool: list_agents
        self.register_tool(
            name="list_agents",
            description="List all currently running agents and their status",
            func=self._tool_list_agents,
            params={}
        )
        
        # Tool: get_status
        self.register_tool(
            name="get_status",
            description="Get detailed status of the workspace - agents, missions, health",
            func=self._tool_get_status,
            params={}
        )
        
        # Tool: create_mission
        self.register_tool(
            name="create_mission",
            description="Create a new mission with tasks",
            func=self._tool_create_mission,
            params={
                "title": "Mission title (required)",
                "tasks": "List of task descriptions (required)"
            }
        )
        
        # Tool: get_missions
        self.register_tool(
            name="get_missions",
            description="List all missions with their tasks and progress",
            func=self._tool_get_missions,
            params={}
        )
        
        # Tool: assign_task
        self.register_tool(
            name="assign_task",
            description="Assign a mission task to an agent",
            func=self._tool_assign_task,
            params={
                "mission_id": "Mission ID (required)",
                "task_index": "Task number (0-based index, required)",
                "agent_name": "Name of agent to assign (required)"
            }
        )
        
        # Tool: execute_mission
        self.register_tool(
            name="execute_mission",
            description="Start executing a mission (auto-assigns tasks to available agents)",
            func=self._tool_execute_mission,
            params={
                "mission_id": "Mission ID to execute (required)"
            }
        )
        
    def register_tool(self, name: str, description: str, func: Callable, params: Dict):
        """Register a new tool"""
        self.tools[name] = AgentTool(name, description, func, params)
        
    def parse_tool_calls(self, text: str) -> List[ToolCall]:
        """
        Parse tool calls from agent response text
        
        Returns list of ToolCall objects found
        """
        calls = []
        
        for match in self.TOOL_PATTERN.finditer(text):
            # Determine which group matched
            # Group 1 & 2: ```json [tool:name]{args} ```
            # Group 3 & 4: [tool:name]{args} (plain)
            # Group 5: ```json {"tool": "name", ...} ```
            # Group 6 & 7: TOOL_CALL format
            
            if match.group(1) and match.group(2):
                # Code block with [tool:name]{args}
                tool_name = match.group(1)
                args_json = match.group(2)
            elif match.group(3) and match.group(4):
                # Plain [tool:name]{args} format
                tool_name = match.group(3)
                args_json = match.group(4)
            elif match.group(5):
                # ```json {"tool": "name", ...} format
                try:
                    full_json = json.loads(match.group(5))
                    tool_name = full_json.pop('tool', None)
                    # Handle "param" wrapper that LLM sometimes adds
                    if 'param' in full_json and isinstance(full_json['param'], dict):
                        args = full_json['param']
                        calls.append(ToolCall(
                            tool_name=tool_name,
                            arguments=args,
                            raw_text=match.group(0)
                        ))
                        continue
                    args_json = json.dumps(full_json)
                except json.JSONDecodeError:
                    continue
            elif match.group(6) and match.group(7):
                # TOOL_CALL format
                tool_name = match.group(6)
                args_json = match.group(7)
            else:
                continue
                
            try:
                args = json.loads(args_json)
                # Handle "param" wrapper that LLM sometimes adds
                if 'param' in args and isinstance(args['param'], dict):
                    args = args['param']
                calls.append(ToolCall(
                    tool_name=tool_name,
                    arguments=args,
                    raw_text=match.group(0)
                ))
            except json.JSONDecodeError:
                continue
                
        return calls
        
    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name"""
        if tool_name not in self.tools:
            return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})
            
        tool = self.tools[tool_name]
        return tool.execute(**kwargs)
        
    def get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for agent prompts"""
        lines = ["\n## Available Tools", "\nYou can call these tools to take action:"]
        
        for name, tool in self.tools.items():
            lines.append(f"\n### {name}")
            lines.append(f"{tool.description}")
            if tool.params:
                lines.append("Parameters:")
                for param, desc in tool.params.items():
                    lines.append(f"  - {param}: {desc}")
            lines.append(f"\nUsage: [tool:{name}]{{\"param\": \"value\"}}")
            
        return "\n".join(lines)
        
    # ============ Tool Implementations ============
    
    def _tool_spawn_agent(self, name: str) -> Dict:
        """Actually spawn an agent"""
        if not self.orchestrator:
            return {"error": "No orchestrator available"}
            
        from shared.resource_monitor import resource_monitor
        
        result = self.orchestrator.spawn_agent(name.lower())
        if result:
            resource_monitor.register_agent(result.id, result.name)
            return {
                "spawned": True,
                "agent_id": result.id,
                "agent_name": result.name,
                "status": result.status
            }
        return {"spawned": False, "error": "Agent may already be running or soul not found"}
        
    def _tool_kill_agent(self, name: str) -> Dict:
        """Kill an agent"""
        if not self.orchestrator:
            return {"error": "No orchestrator available"}
            
        # Find agent by name
        for aid, agent in self.orchestrator.agents.items():
            if agent.name.lower() == name.lower():
                self.orchestrator.kill_agent(aid)
                return {"killed": True, "agent_name": agent.name}
                
        return {"killed": False, "error": f"Agent {name} not found"}
        
    def _tool_list_agents(self) -> Dict:
        """List all agents"""
        if not self.orchestrator:
            return {"error": "No orchestrator available"}
            
        agents = []
        for aid, agent in self.orchestrator.agents.items():
            agents.append({
                "id": aid,
                "name": agent.name,
                "status": agent.status,
                "role": agent.role,
                "tasks_completed": agent.tasks_completed,
                "current_task": agent.current_task
            })
            
        return {"agents": agents, "count": len(agents)}
        
    def _tool_get_status(self) -> Dict:
        """Get full workspace status"""
        if not self.orchestrator:
            return {"error": "No orchestrator available"}
            
        data = self.orchestrator.get_dashboard_data()
        
        return {
            "agents": {
                "total": len(data['agents']),
                "working": len([a for a in data['agents'] if a['status'] == 'working']),
                "idle": len([a for a in data['agents'] if a['status'] == 'idle']),
                "error": len([a for a in data['agents'] if a['status'] == 'error'])
            },
            "missions": len(data['missions']),
            "health": data.get('health_summary', {})
        }
        
    def _tool_create_mission(self, title: str, tasks: List[str]) -> Dict:
        """Create a new mission"""
        if not self.orchestrator:
            return {"error": "No orchestrator available"}
            
        task_dicts = [{"description": t, "assigned_to": None} for t in tasks]
        mission = self.orchestrator.create_mission(title, "", task_dicts)
        
        return {
            "created": True,
            "mission_id": mission.id,
            "title": mission.title,
            "task_count": len(tasks)
        }
        
    def _tool_get_missions(self) -> Dict:
        """Get all missions with details"""
        if not self.orchestrator:
            return {"error": "No orchestrator available"}
            
        missions = []
        for mission in self.orchestrator.mission_manager.list_missions():
            total = len(mission.tasks)
            completed = len([t for t in mission.tasks if t.status == "completed"])
            pending = len([t for t in mission.tasks if t.status == "pending"])
            in_progress = len([t for t in mission.tasks if t.status == "in_progress"])
            
            missions.append({
                "id": mission.id,
                "title": mission.title,
                "status": mission.status.value,
                "progress": {
                    "total": total,
                    "completed": completed,
                    "pending": pending,
                    "in_progress": in_progress,
                    "percent": round((completed / total * 100), 1) if total > 0 else 0
                },
                "tasks": [
                    {
                        "id": t.id,
                        "description": t.description,
                        "status": t.status,
                        "assigned_to": t.assigned_to
                    }
                    for t in mission.tasks
                ]
            })
            
        return {"missions": missions, "count": len(missions)}
        
    def _tool_assign_task(self, mission_id: str, task_index: int, agent_name: str) -> Dict:
        """Assign a task to an agent"""
        if not self.orchestrator:
            return {"error": "No orchestrator available"}
            
        mission = self.orchestrator.mission_manager.get_mission(mission_id)
        if not mission:
            return {"error": f"Mission {mission_id} not found"}
            
        if task_index < 0 or task_index >= len(mission.tasks):
            return {"error": f"Invalid task index {task_index}. Mission has {len(mission.tasks)} tasks."}
            
        task = mission.tasks[task_index]
        task.assigned_to = agent_name
        self.orchestrator.mission_manager._save_mission(mission)
        
        return {
            "assigned": True,
            "task_id": task.id,
            "task_description": task.description,
            "assigned_to": agent_name
        }
        
    def _tool_execute_mission(self, mission_id: str) -> Dict:
        """Execute a mission"""
        if not self.orchestrator:
            return {"error": "No orchestrator available"}
            
        mission = self.orchestrator.mission_manager.get_mission(mission_id)
        if not mission:
            return {"error": f"Mission {mission_id} not found"}
            
        # Start auto-execution
        self.orchestrator.execute_mission_auto(mission_id, parallel=True)
        
        return {
            "executed": True,
            "mission_id": mission_id,
            "title": mission.title,
            "tasks": len(mission.tasks)
        }


# Global registry
_tool_registry: Optional[ToolRegistry] = None

def get_tool_registry(orchestrator=None) -> ToolRegistry:
    """Get or create global tool registry"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry(orchestrator)
    return _tool_registry
