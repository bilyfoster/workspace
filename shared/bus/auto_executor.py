"""
Auto-Executor for Workspace MVP

Features:
- Automatic handoffs between agents
- Parallel task execution
- Export results to files
"""
import json
import logging
import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from shared.bus.message_bus import MessageBus, Message, MessageType
from shared.bus.handoff import handoff_manager, HandoffContext
from herbie.core.mission_manager import MissionManager

logger = logging.getLogger(__name__)

class AutoExecutor:
    """
    Automatically executes missions with:
    - Parallel task execution
    - Automatic handoffs
    - File exports
    """
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.bus = MessageBus()
        self.running_missions: Dict[str, threading.Thread] = {}
        
        # Export directory
        self.exports_dir = Path("./exports")
        self.exports_dir.mkdir(exist_ok=True)
        
        logger.info("AutoExecutor initialized")
    
    def execute_mission_parallel(self, mission_id: str, auto_handoff: bool = True) -> threading.Thread:
        """
        Execute all tasks in a mission in parallel
        
        Args:
            mission_id: Mission to execute
            auto_handoff: Whether to automatically handoff between agents
        """
        def run_execution():
            logger.info(f"Starting parallel execution of mission {mission_id}")
            
            mission = self.orchestrator.mission_manager.get_mission(mission_id)
            if not mission:
                logger.error(f"Mission {mission_id} not found")
                return
            
            # Start all pending tasks in parallel
            threads = []
            for task in mission.tasks:
                if task.status == "pending" and task.assigned_to:
                    t = threading.Thread(
                        target=self._execute_single_task,
                        args=(mission_id, task.id, task.assigned_to, task.description)
                    )
                    t.start()
                    threads.append(t)
                    logger.info(f"Started task {task.id} with {task.assigned_to}")
            
            # Wait for all to complete
            for t in threads:
                t.join()
            
            # Export results
            self.export_mission_results(mission_id)
            
            # Auto-handoff if enabled and there are follow-up tasks
            if auto_handoff:
                self._process_handoffs(mission_id)
            
            logger.info(f"Mission {mission_id} execution complete")
        
        thread = threading.Thread(target=run_execution)
        thread.start()
        self.running_missions[mission_id] = thread
        return thread
    
    def _execute_single_task(self, mission_id: str, task_id: str, agent_name: str, description: str):
        """Execute a single task and wait for completion"""
        # Assign task
        success = self.orchestrator.assign_task(agent_name, description, mission_id, task_id)
        
        if not success:
            logger.error(f"Failed to assign task {task_id} to {agent_name}")
            return
        
        # Wait for completion
        max_wait = 300  # 5 minutes max
        start = datetime.now()
        
        while (datetime.now() - start).seconds < max_wait:
            mission = self.orchestrator.mission_manager.get_mission(mission_id)
            task = next((t for t in mission.tasks if t.id == task_id), None)
            
            if task and task.status in ["completed", "failed"]:
                logger.info(f"Task {task_id} finished with status: {task.status}")
                break
            
            asyncio.sleep(1)
    
    def _process_handoffs(self, mission_id: str):
        """Process automatic handoffs based on task results"""
        mission = self.orchestrator.mission_manager.get_mission(mission_id)
        
        for task in mission.tasks:
            if task.status == "completed" and task.result:
                # Check if agent mentioned handoff
                result_lower = task.result.lower()
                
                # Detect handoff keywords
                handoff_indicators = [
                    "pass this to", "hand off to", "next step:", 
                    "should be reviewed by", "over to", "ready for"
                ]
                
                if any(ind in result_lower for ind in handoff_indicators):
                    # Find next agent based on context
                    next_agent = self._infer_next_agent_from_result(task.result)
                    
                    if next_agent:
                        # Find next pending task
                        next_task = next((t for t in mission.tasks if t.status == "pending"), None)
                        
                        if next_task:
                            logger.info(f"Auto-handoff: {task.assigned_to} → {next_agent}")
                            
                            # Create handoff context
                            context = HandoffContext(
                                original_task=task.description,
                                work_done=task.result[:500],
                                findings={},
                                next_steps=[next_task.description],
                                questions=[],
                                files=[],
                                notes="Auto-generated handoff based on task completion"
                            )
                            
                            handoff_manager.request_handoff(
                                from_agent=task.assigned_to,
                                to_agent=next_agent,
                                context=context,
                                mission_id=mission_id
                            )
    
    def _infer_next_agent_from_result(self, result: str) -> Optional[str]:
        """Infer which agent should receive handoff"""
        result_lower = result.lower()
        
        agent_keywords = {
            "code": ["code", "implement", "develop", "build", "programming"],
            "guardian": ["test", "qa", "review", "quality", "bug"],
            "wong": ["document", "docs", "readme", "guide", "manual"],
            "quill": ["social", "post", "tweet", "content", "marketing"],
            "pepper": ["email", "campaign", "newsletter"],
            "pixel": ["design", "ui", "ux", "mockup", "visual"],
            "scout": ["research", "analyze", "investigate"],
            "sage": ["data", "analytics", "metrics", "report"],
            "shuri": ["product", "strategy", "roadmap", "plan"],
        }
        
        for agent, keywords in agent_keywords.items():
            if any(kw in result_lower for kw in keywords):
                return agent
        
        return None
    
    def export_mission_results(self, mission_id: str, format: str = "markdown") -> Path:
        """
        Export mission results to file
        
        Args:
            mission_id: Mission to export
            format: 'markdown' or 'json'
        
        Returns:
            Path to exported file
        """
        mission = self.orchestrator.mission_manager.get_mission(mission_id)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{mission.title.replace(' ', '_')}_{timestamp}"
        
        if format == "json":
            return self._export_json(mission, filename)
        else:
            return self._export_markdown(mission, filename)
    
    def _export_markdown(self, mission, filename: str) -> Path:
        """Export as Markdown"""
        filepath = self.exports_dir / f"{filename}.md"
        
        md_content = f"""# {mission.title}

**Created:** {mission.created_at}  
**Status:** {mission.status.value}  
**Goal:** {mission.goal}

---

## Tasks

"""
        
        for i, task in enumerate(mission.tasks, 1):
            status_icon = "✅" if task.status == "completed" else "❌" if task.status == "failed" else "⏳"
            
            md_content += f"""### {i}. {status_icon} {task.description}

**Assigned to:** {task.assigned_to or 'Unassigned'}  
**Status:** {task.status}

"""
            if task.result:
                md_content += f"**Result:**\n\n```\n{task.result}\n```\n\n"
            
            md_content += "---\n\n"
        
        md_content += f"""
## Summary

- **Total Tasks:** {len(mission.tasks)}
- **Completed:** {len([t for t in mission.tasks if t.status == 'completed'])}
- **Failed:** {len([t for t in mission.tasks if t.status == 'failed'])}
- **Pending:** {len([t for t in mission.tasks if t.status == 'pending'])}

---

*Exported from Workspace on {datetime.now().isoformat()}*
"""
        
        filepath.write_text(md_content)
        logger.info(f"Exported mission to {filepath}")
        return filepath
    
    def _export_json(self, mission, filename: str) -> Path:
        """Export as JSON"""
        filepath = self.exports_dir / f"{filename}.json"
        
        data = {
            "mission": mission.to_dict(),
            "exported_at": datetime.now().isoformat()
        }
        
        filepath.write_text(json.dumps(data, indent=2))
        logger.info(f"Exported mission to {filepath}")
        return filepath
    
    def get_running_missions(self) -> List[str]:
        """Get list of currently running mission IDs"""
        # Clean up finished threads
        for mid, thread in list(self.running_missions.items()):
            if not thread.is_alive():
                del self.running_missions[mid]
        
        return list(self.running_missions.keys())

# Global instance
auto_executor: Optional[AutoExecutor] = None

def get_auto_executor(orchestrator) -> AutoExecutor:
    global auto_executor
    if auto_executor is None:
        auto_executor = AutoExecutor(orchestrator)
    return auto_executor
