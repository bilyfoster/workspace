"""
Time-based Analytics for Workspace

Collects and visualizes agent activity, performance, and system metrics over time.
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json
from pathlib import Path

from shared.bus.message_bus import MessageBus, Message, MessageType

logger = logging.getLogger(__name__)

@dataclass
class TimeSeriesPoint:
    """A single data point in a time series"""
    timestamp: str
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentMetrics:
    """Metrics for a single agent"""
    agent_id: str
    agent_name: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    handoffs_initiated: int = 0
    handoffs_received: int = 0
    total_work_time: float = 0.0  # seconds
    last_active: Optional[str] = None

class AnalyticsCollector:
    """
    Collects and analyzes time-based metrics for Workspace
    
    Tracks:
    - Agent activity over time
    - Task completion rates
    - Message volumes
    - System performance
    - Mission durations
    """
    
    def __init__(self, data_dir: str = "./analytics"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.bus = MessageBus()
        
        # Metrics storage
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.hourly_activity: Dict[str, List[TimeSeriesPoint]] = defaultdict(list)
        self.task_completion_times: List[TimeSeriesPoint] = []
        self.message_volume: Dict[str, List[TimeSeriesPoint]] = defaultdict(list)
        
        # Session tracking
        self.agent_sessions: Dict[str, Dict[str, Any]] = {}  # agent_id -> session data
        self.task_start_times: Dict[str, str] = {}  # task_id -> start timestamp
        
        # Subscribe to events
        self._setup_subscriptions()
        
        logger.info("AnalyticsCollector initialized")
    
    def _setup_subscriptions(self):
        """Subscribe to relevant events"""
        self.bus.subscribe(MessageType.TASK_STARTED, self._on_task_started)
        self.bus.subscribe(MessageType.TASK_COMPLETED, self._on_task_completed)
        self.bus.subscribe(MessageType.TASK_FAILED, self._on_task_failed)
        self.bus.subscribe(MessageType.AGENT_MESSAGE, self._on_message)
        self.bus.subscribe(MessageType.AGENT_ONLINE, self._on_agent_online)
        self.bus.subscribe(MessageType.AGENT_OFFLINE, self._on_agent_offline)
        self.bus.subscribe(MessageType.HANDOFF_REQUEST, self._on_handoff_request)
        self.bus.subscribe(MessageType.HANDOFF_ACCEPT, self._on_handoff_accept)
        self.bus.subscribe(MessageType.MISSION_CREATED, self._on_mission_created)
        self.bus.subscribe(MessageType.MISSION_COMPLETED, self._on_mission_completed)
    
    def _get_or_create_metrics(self, agent_id: str, agent_name: str = "") -> AgentMetrics:
        """Get or create metrics for an agent"""
        if agent_id not in self.agent_metrics:
            self.agent_metrics[agent_id] = AgentMetrics(
                agent_id=agent_id,
                agent_name=agent_name or agent_id
            )
        return self.agent_metrics[agent_id]
    
    def _on_task_started(self, message: Message):
        """Track task start"""
        task_id = message.payload.get('task_id')
        if task_id:
            self.task_start_times[task_id] = message.timestamp
        
        # Update agent activity
        agent_id = message.sender
        metrics = self._get_or_create_metrics(agent_id)
        metrics.last_active = message.timestamp
    
    def _on_task_completed(self, message: Message):
        """Track task completion"""
        task_id = message.payload.get('task_id')
        agent_id = message.sender
        
        # Calculate duration
        duration = None
        if task_id in self.task_start_times:
            start = datetime.fromisoformat(self.task_start_times[task_id])
            end = datetime.fromisoformat(message.timestamp)
            duration = (end - start).total_seconds()
        
        # Update agent metrics
        metrics = self._get_or_create_metrics(agent_id)
        metrics.tasks_completed += 1
        metrics.total_work_time += duration or 0
        metrics.last_active = message.timestamp
        
        # Record completion time
        if duration:
            self.task_completion_times.append(TimeSeriesPoint(
                timestamp=message.timestamp,
                value=duration,
                metadata={"agent_id": agent_id, "task_id": task_id}
            ))
    
    def _on_task_failed(self, message: Message):
        """Track task failure"""
        agent_id = message.sender
        metrics = self._get_or_create_metrics(agent_id)
        metrics.tasks_failed += 1
        metrics.last_active = message.timestamp
    
    def _on_message(self, message: Message):
        """Track message activity"""
        sender = message.sender
        recipient = message.recipient
        
        # Update sender metrics
        sender_metrics = self._get_or_create_metrics(sender)
        sender_metrics.messages_sent += 1
        sender_metrics.last_active = message.timestamp
        
        # Update recipient metrics
        if recipient:
            recipient_metrics = self._get_or_create_metrics(recipient)
            recipient_metrics.messages_received += 1
            recipient_metrics.last_active = message.timestamp
        
        # Record message volume by hour
        hour_key = message.timestamp[:13]  # YYYY-MM-DDTHH
        self.message_volume[hour_key].append(TimeSeriesPoint(
            timestamp=message.timestamp,
            value=1,
            metadata={"sender": sender, "recipient": recipient}
        ))
    
    def _on_agent_online(self, message: Message):
        """Track agent coming online"""
        agent_id = message.sender
        agent_name = message.payload.get('name', agent_id)
        
        self.agent_sessions[agent_id] = {
            "start": message.timestamp,
            "name": agent_name
        }
        
        # Ensure metrics exist
        self._get_or_create_metrics(agent_id, agent_name)
    
    def _on_agent_offline(self, message: Message):
        """Track agent going offline"""
        agent_id = message.sender
        
        if agent_id in self.agent_sessions:
            session = self.agent_sessions[agent_id]
            start = datetime.fromisoformat(session["start"])
            end = datetime.fromisoformat(message.timestamp)
            duration = (end - start).total_seconds()
            
            # Could track session duration here
            del self.agent_sessions[agent_id]
    
    def _on_handoff_request(self, message: Message):
        """Track handoff requests"""
        from_agent = message.payload.get('from_agent')
        
        if from_agent:
            metrics = self._get_or_create_metrics(from_agent)
            metrics.handoffs_initiated += 1
            metrics.last_active = message.timestamp
    
    def _on_handoff_accept(self, message: Message):
        """Track handoff accepts"""
        to_agent = message.sender
        
        if to_agent:
            metrics = self._get_or_create_metrics(to_agent)
            metrics.handoffs_received += 1
            metrics.last_active = message.timestamp
    
    def _on_mission_created(self, message: Message):
        """Track mission creation"""
        pass  # Could track active missions over time
    
    def _on_mission_completed(self, message: Message):
        """Track mission completion"""
        pass  # Could track completion rates over time
    
    # Query methods for dashboard
    
    def get_agent_performance(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get performance metrics for all agents"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        results = []
        for agent_id, metrics in self.agent_metrics.items():
            total_tasks = metrics.tasks_completed + metrics.tasks_failed
            success_rate = (metrics.tasks_completed / total_tasks * 100) if total_tasks > 0 else 0
            
            # Calculate average task time
            recent_completions = [
                p for p in self.task_completion_times[-50:]
                if p.metadata.get('agent_id') == agent_id
                and datetime.fromisoformat(p.timestamp) > cutoff
            ]
            avg_task_time = sum(p.value for p in recent_completions) / len(recent_completions) if recent_completions else 0
            
            results.append({
                "agent_id": agent_id,
                "agent_name": metrics.agent_name,
                "tasks_completed": metrics.tasks_completed,
                "tasks_failed": metrics.tasks_failed,
                "success_rate": round(success_rate, 1),
                "avg_task_time": round(avg_task_time, 1),
                "messages_sent": metrics.messages_sent,
                "messages_received": metrics.messages_received,
                "handoffs_initiated": metrics.handoffs_initiated,
                "handoffs_received": metrics.handoffs_received,
                "total_work_time": round(metrics.total_work_time / 60, 1),  # minutes
                "last_active": metrics.last_active
            })
        
        return sorted(results, key=lambda x: x['tasks_completed'], reverse=True)
    
    def get_activity_timeline(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get activity timeline for charts"""
        now = datetime.now()
        timeline = []
        
        for i in range(hours):
            hour_start = now - timedelta(hours=i)
            hour_key = hour_start.strftime("%Y-%m-%dT%H")
            
            # Count events in this hour
            message_count = len(self.message_volume.get(hour_key, []))
            
            timeline.append({
                "hour": hour_start.strftime("%H:00"),
                "messages": message_count,
                "timestamp": hour_key
            })
        
        return list(reversed(timeline))
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get overall system metrics"""
        total_tasks = sum(m.tasks_completed + m.tasks_failed for m in self.agent_metrics.values())
        total_completed = sum(m.tasks_completed for m in self.agent_metrics.values())
        total_failed = sum(m.tasks_failed for m in self.agent_metrics.values())
        
        success_rate = (total_completed / total_tasks * 100) if total_tasks > 0 else 0
        
        total_messages = sum(m.messages_sent for m in self.agent_metrics.values())
        total_handoffs = sum(m.handoffs_initiated for m in self.agent_metrics.values())
        
        return {
            "total_agents": len(self.agent_metrics),
            "total_tasks": total_tasks,
            "tasks_completed": total_completed,
            "tasks_failed": total_failed,
            "success_rate": round(success_rate, 1),
            "total_messages": total_messages,
            "total_handoffs": total_handoffs,
            "avg_task_time": self._calculate_avg_task_time()
        }
    
    def _calculate_avg_task_time(self) -> float:
        """Calculate average task completion time"""
        if not self.task_completion_times:
            return 0.0
        
        recent = self.task_completion_times[-100:]  # Last 100 tasks
        return round(sum(p.value for p in recent) / len(recent), 1)
    
    def get_top_collaborations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most active agent-to-agent collaborations"""
        # Analyze message volume between agent pairs
        pairs = defaultdict(int)
        
        for hour, points in self.message_volume.items():
            for point in points:
                sender = point.metadata.get('sender')
                recipient = point.metadata.get('recipient')
                if sender and recipient:
                    pair = tuple(sorted([sender, recipient]))
                    pairs[pair] += 1
        
        sorted_pairs = sorted(pairs.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                "agent_1": pair[0],
                "agent_2": pair[1],
                "message_count": count
            }
            for pair, count in sorted_pairs[:limit]
        ]
    
    def export_daily_report(self, date: Optional[datetime] = None) -> Path:
        """Export a daily analytics report"""
        if date is None:
            date = datetime.now()
        
        report = {
            "date": date.strftime("%Y-%m-%d"),
            "generated_at": datetime.now().isoformat(),
            "system_metrics": self.get_system_metrics(),
            "agent_performance": self.get_agent_performance(hours=24),
            "activity_timeline": self.get_activity_timeline(hours=24),
            "top_collaborations": self.get_top_collaborations()
        }
        
        filepath = self.data_dir / f"report_{date.strftime('%Y%m%d')}.json"
        filepath.write_text(json.dumps(report, indent=2))
        
        logger.info(f"Exported daily report to {filepath}")
        return filepath

# Global instance
analytics = AnalyticsCollector()
