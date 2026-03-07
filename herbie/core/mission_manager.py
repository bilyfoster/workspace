"""Mission management - tracks goals, tasks, and progress"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class MissionStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"

@dataclass
class MissionTask:
    """A task within a mission"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    assigned_to: Optional[str] = None  # Agent name
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

@dataclass
class Mission:
    """A mission (project/goal) with multiple tasks"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    goal: str = ""
    status: MissionStatus = MissionStatus.ACTIVE
    tasks: List[MissionTask] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mission to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "goal": self.goal,
            "status": self.status.value,
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description,
                    "assigned_to": t.assigned_to,
                    "status": t.status,
                    "result": t.result,
                    "created_at": t.created_at,
                    "completed_at": t.completed_at
                }
                for t in self.tasks
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Mission":
        """Create mission from dictionary"""
        mission = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            title=data.get("title", ""),
            description=data.get("description", ""),
            goal=data.get("goal", ""),
            status=MissionStatus(data.get("status", "active")),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            completed_at=data.get("completed_at"),
            metadata=data.get("metadata", {})
        )
        
        for task_data in data.get("tasks", []):
            task = MissionTask(
                id=task_data.get("id", str(uuid.uuid4())[:8]),
                description=task_data.get("description", ""),
                assigned_to=task_data.get("assigned_to"),
                status=task_data.get("status", "pending"),
                result=task_data.get("result"),
                created_at=task_data.get("created_at", datetime.now().isoformat()),
                completed_at=task_data.get("completed_at")
            )
            mission.tasks.append(task)
        
        return mission

class MissionManager:
    """Manages missions and their persistence"""
    
    def __init__(self, storage_path: str = "./missions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._missions: Dict[str, Mission] = {}
        self._load_missions()
    
    def _load_missions(self):
        """Load all missions from storage"""
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    mission = Mission.from_dict(data)
                    self._missions[mission.id] = mission
                    logger.info(f"Loaded mission: {mission.title}")
            except Exception as e:
                logger.error(f"Failed to load mission from {file_path}: {e}")
    
    def _save_mission(self, mission: Mission):
        """Save a mission to disk"""
        file_path = self.storage_path / f"{mission.id}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump(mission.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save mission {mission.id}: {e}")
    
    def create_mission(
        self,
        title: str,
        description: str = "",
        goal: str = "",
        metadata: Dict[str, Any] = None
    ) -> Mission:
        """Create a new mission"""
        mission = Mission(
            title=title,
            description=description,
            goal=goal,
            metadata=metadata or {}
        )
        self._missions[mission.id] = mission
        self._save_mission(mission)
        logger.info(f"Created mission: {title}")
        return mission
    
    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """Get a mission by ID"""
        return self._missions.get(mission_id)
    
    def list_missions(self, status: Optional[MissionStatus] = None) -> List[Mission]:
        """List all missions, optionally filtered by status"""
        missions = list(self._missions.values())
        if status:
            missions = [m for m in missions if m.status == status]
        return sorted(missions, key=lambda m: m.created_at, reverse=True)
    
    def add_task(
        self,
        mission_id: str,
        description: str,
        assigned_to: Optional[str] = None
    ) -> Optional[MissionTask]:
        """Add a task to a mission"""
        mission = self._missions.get(mission_id)
        if not mission:
            return None
        
        task = MissionTask(
            description=description,
            assigned_to=assigned_to
        )
        mission.tasks.append(task)
        mission.updated_at = datetime.now().isoformat()
        self._save_mission(mission)
        return task
    
    def update_task_status(
        self,
        mission_id: str,
        task_id: str,
        status: str,
        result: Optional[str] = None
    ) -> bool:
        """Update a task's status and result"""
        mission = self._missions.get(mission_id)
        if not mission:
            return False
        
        for task in mission.tasks:
            if task.id == task_id:
                task.status = status
                if result:
                    task.result = result
                if status in ("completed", "failed"):
                    task.completed_at = datetime.now().isoformat()
                mission.updated_at = datetime.now().isoformat()
                self._save_mission(mission)
                return True
        
        return False
    
    def update_mission_status(self, mission_id: str, status: MissionStatus) -> bool:
        """Update mission status"""
        mission = self._missions.get(mission_id)
        if not mission:
            return False
        
        mission.status = status
        mission.updated_at = datetime.now().isoformat()
        if status == MissionStatus.COMPLETED:
            mission.completed_at = datetime.now().isoformat()
        
        self._save_mission(mission)
        return True
    
    def get_mission_summary(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of mission progress"""
        mission = self._missions.get(mission_id)
        if not mission:
            return None
        
        total = len(mission.tasks)
        completed = len([t for t in mission.tasks if t.status == "completed"])
        in_progress = len([t for t in mission.tasks if t.status == "in_progress"])
        failed = len([t for t in mission.tasks if t.status == "failed"])
        pending = total - completed - in_progress - failed
        
        return {
            "mission_id": mission.id,
            "title": mission.title,
            "status": mission.status.value,
            "progress": {
                "total": total,
                "completed": completed,
                "in_progress": in_progress,
                "failed": failed,
                "pending": pending,
                "percent": round((completed / total * 100), 1) if total > 0 else 0
            },
            "tasks": [
                {
                    "id": t.id,
                    "description": t.description[:50] + "..." if len(t.description) > 50 else t.description,
                    "assigned_to": t.assigned_to,
                    "status": t.status
                }
                for t in mission.tasks
            ]
        }
