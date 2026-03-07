#!/usr/bin/env python3
"""
Agent Health Monitor - Proactive monitoring and auto-remediation

Monitors agent health, detects issues, and can automatically
spawn troubleshooting agents or take corrective action.
"""
import threading
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AgentState(Enum):
    HEALTHY = "healthy"
    IDLE = "idle"
    WORKING = "working"
    STUCK = "stuck"  # Working too long
    ERROR = "error"
    UNRESPONSIVE = "unresponsive"
    OFFLINE = "offline"


@dataclass
class AgentHealthRecord:
    """Health record for an agent"""
    agent_id: str
    agent_name: str
    status: str
    state: AgentState
    last_seen: datetime
    last_status_change: datetime
    current_task: Optional[str] = None
    task_start_time: Optional[datetime] = None
    consecutive_errors: int = 0
    total_restarts: int = 0
    alerts: List[Dict] = field(default_factory=list)
    
    @property
    def time_in_current_state(self) -> timedelta:
        return datetime.now() - self.last_status_change
    
    @property
    def time_on_current_task(self) -> Optional[timedelta]:
        if self.task_start_time:
            return datetime.now() - self.task_start_time
        return None


class AgentHealthMonitor:
    """
    Monitors agent health and can auto-remediate issues
    
    Features:
    - Detects stuck agents (working too long)
    - Detects unresponsive agents
    - Auto-respawn failed agents
    - Spawn troubleshooting agents for complex issues
    - Report issues to user/Manager
    """
    
    # Thresholds
    STUCK_THRESHOLD_SECONDS = 300  # 5 minutes working = stuck
    UNRESPONSIVE_THRESHOLD_SECONDS = 60  # 1 minute no response
    MAX_CONSECUTIVE_ERRORS = 3
    AUTO_RESPAWN_MAX_RETRIES = 2
    
    def __init__(self):
        self.health_records: Dict[str, AgentHealthRecord] = {}
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable] = []
        self._lock = threading.Lock()
        
    def register_callback(self, callback: Callable):
        """Register a callback for health alerts"""
        self._callbacks.append(callback)
    
    def update_agent_status(self, agent_id: str, agent_name: str, status: str, 
                           current_task: Optional[str] = None):
        """Update agent status in health record"""
        with self._lock:
            now = datetime.now()
            
            if agent_id not in self.health_records:
                self.health_records[agent_id] = AgentHealthRecord(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    status=status,
                    state=AgentState(status) if status in [s.value for s in AgentState] else AgentState.IDLE,
                    last_seen=now,
                    last_status_change=now,
                    current_task=current_task
                )
            else:
                record = self.health_records[agent_id]
                
                # Check if status changed
                if record.status != status:
                    record.last_status_change = now
                    record.status = status
                    
                    # Reset error count on successful status change
                    if status == "idle":
                        record.consecutive_errors = 0
                
                # Update task tracking
                if current_task and current_task != record.current_task:
                    record.current_task = current_task
                    record.task_start_time = now
                elif not current_task:
                    record.current_task = None
                    record.task_start_time = None
                
                record.last_seen = now
                
                # Update state based on status and timing
                record.state = self._determine_state(record)
    
    def _determine_state(self, record: AgentHealthRecord) -> AgentState:
        """Determine agent state based on status and timing"""
        if record.status == "error":
            return AgentState.ERROR
        elif record.status == "offline":
            return AgentState.OFFLINE
        elif record.status == "working":
            # Check if stuck
            if record.time_on_current_task:
                if record.time_on_current_task.seconds > self.STUCK_THRESHOLD_SECONDS:
                    return AgentState.STUCK
            return AgentState.WORKING
        elif record.status == "idle":
            return AgentState.IDLE
        else:
            return AgentState.HEALTHY
    
    def record_error(self, agent_id: str, error_message: str):
        """Record an error for an agent"""
        with self._lock:
            if agent_id in self.health_records:
                record = self.health_records[agent_id]
                record.consecutive_errors += 1
                record.alerts.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "error",
                    "message": error_message
                })
    
    def start_monitoring(self, interval: float = 10.0):
        """Start the health monitoring loop"""
        if self._monitoring:
            return
        
        self._monitoring = True
        
        def monitor_loop():
            while self._monitoring:
                self._check_health()
                time.sleep(interval)
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"AgentHealthMonitor started (interval: {interval}s)")
    
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
    
    def _check_health(self):
        """Check health of all agents and trigger remediation if needed"""
        with self._lock:
            for agent_id, record in self.health_records.items():
                issues = self._detect_issues(record)
                
                if issues:
                    for issue in issues:
                        self._trigger_alert(record, issue)
    
    def _detect_issues(self, record: AgentHealthRecord) -> List[Dict]:
        """Detect issues with an agent"""
        issues = []
        
        # Check for stuck agents
        if record.state == AgentState.STUCK:
            issues.append({
                "type": "stuck",
                "severity": "warning",
                "message": f"{record.agent_name} has been working for {record.time_on_current_task.seconds // 60} minutes",
                "suggested_action": "check_task_or_respawn"
            })
        
        # Check for error state
        if record.state == AgentState.ERROR:
            issues.append({
                "type": "error",
                "severity": "critical",
                "message": f"{record.agent_name} is in error state",
                "suggested_action": "respawn"
            })
        
        # Check for unresponsive (haven't seen in a while)
        time_since_seen = (datetime.now() - record.last_seen).seconds
        if time_since_seen > self.UNRESPONSIVE_THRESHOLD_SECONDS and record.status != "offline":
            issues.append({
                "type": "unresponsive",
                "severity": "warning",
                "message": f"{record.agent_name} hasn't been seen for {time_since_seen} seconds",
                "suggested_action": "ping_or_respawn"
            })
        
        # Check for too many consecutive errors
        if record.consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
            issues.append({
                "type": "repeated_errors",
                "severity": "critical",
                "message": f"{record.agent_name} has {record.consecutive_errors} consecutive errors",
                "suggested_action": "respawn_and_investigate"
            })
        
        return issues
    
    def _trigger_alert(self, record: AgentHealthRecord, issue: Dict):
        """Trigger alert callbacks"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": record.agent_id,
            "agent_name": record.agent_name,
            "issue": issue,
            "record": record
        }
        
        # Log it
        logger.warning(f"Health alert: {record.agent_name} - {issue['message']}")
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Health callback error: {e}")
    
    def get_health_summary(self) -> Dict:
        """Get summary of agent health"""
        with self._lock:
            summary = {
                "total_agents": len(self.health_records),
                "healthy": 0,
                "idle": 0,
                "working": 0,
                "stuck": 0,
                "error": 0,
                "unresponsive": 0,
                "offline": 0,
                "agents": {}
            }
            
            for agent_id, record in self.health_records.items():
                state_name = record.state.value
                summary[state_name] = summary.get(state_name, 0) + 1
                
                summary["agents"][agent_id] = {
                    "name": record.agent_name,
                    "status": record.status,
                    "state": record.state.value,
                    "time_in_state": str(record.time_in_current_state),
                    "consecutive_errors": record.consecutive_errors,
                    "current_task": record.current_task
                }
            
            return summary
    
    def get_agent_health(self, agent_id: str) -> Optional[AgentHealthRecord]:
        """Get health record for specific agent"""
        return self.health_records.get(agent_id)
    
    def should_auto_respawn(self, agent_id: str) -> bool:
        """Check if agent should be auto-respawned"""
        record = self.health_records.get(agent_id)
        if not record:
            return False
        
        # Don't respawn if already respawned too many times
        if record.total_restarts >= self.AUTO_RESPAWN_MAX_RETRIES:
            return False
        
        # Respawn on error or stuck
        return record.state in [AgentState.ERROR, AgentState.STUCK]


# Global instance
health_monitor = AgentHealthMonitor()
