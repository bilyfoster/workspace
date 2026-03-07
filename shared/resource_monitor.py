#!/usr/bin/env python3
"""
Resource Monitor for Workspace
Tracks CPU, memory, and other system resources per agent
"""
import psutil
import time
import threading
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ResourceSnapshot:
    """Resource usage at a point in time"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    thread_count: int
    

@dataclass
class AgentResources:
    """Resource tracking for a single agent"""
    agent_id: str
    agent_name: str
    pid: Optional[int] = None
    thread_id: Optional[int] = None
    snapshots: List[ResourceSnapshot] = field(default_factory=list)
    total_tasks_completed: int = 0
    total_tokens_used: int = 0
    
    def add_snapshot(self, cpu: float, memory_mb: float, memory_pct: float, threads: int):
        """Add a new resource snapshot"""
        snapshot = ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu,
            memory_mb=memory_mb,
            memory_percent=memory_pct,
            thread_count=threads
        )
        self.snapshots.append(snapshot)
        # Keep last 100 snapshots
        if len(self.snapshots) > 100:
            self.snapshots = self.snapshots[-100:]
    
    def get_current(self) -> Optional[ResourceSnapshot]:
        """Get most recent snapshot"""
        return self.snapshots[-1] if self.snapshots else None
    
    def get_average_cpu(self, last_n: int = 10) -> float:
        """Get average CPU over last N snapshots"""
        if not self.snapshots:
            return 0.0
        recent = self.snapshots[-last_n:]
        return sum(s.cpu_percent for s in recent) / len(recent)
    
    def get_peak_memory(self) -> float:
        """Get peak memory usage"""
        if not self.snapshots:
            return 0.0
        return max(s.memory_mb for s in self.snapshots)


class ResourceMonitor:
    """Monitors system resources for all agents"""
    
    def __init__(self):
        self.agent_resources: Dict[str, AgentResources] = {}
        self._lock = threading.Lock()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
    def register_agent(self, agent_id: str, agent_name: str, thread_id: Optional[int] = None):
        """Register a new agent for monitoring"""
        with self._lock:
            self.agent_resources[agent_id] = AgentResources(
                agent_id=agent_id,
                agent_name=agent_name,
                thread_id=thread_id,
                pid=psutil.Process().pid  # Same process for all threads
            )
    
    def unregister_agent(self, agent_id: str):
        """Remove an agent from monitoring"""
        with self._lock:
            if agent_id in self.agent_resources:
                del self.agent_resources[agent_id]
    
    def update_agent_task_count(self, agent_id: str, increment: int = 1):
        """Update task completion count"""
        with self._lock:
            if agent_id in self.agent_resources:
                self.agent_resources[agent_id].total_tasks_completed += increment
    
    def update_agent_tokens(self, agent_id: str, tokens: int):
        """Update token usage count"""
        with self._lock:
            if agent_id in self.agent_resources:
                self.agent_resources[agent_id].total_tokens_used += tokens
    
    def _collect_snapshot(self):
        """Collect resource snapshot for all agents"""
        try:
            process = psutil.Process()
            
            with self._lock:
                for agent_id, resources in self.agent_resources.items():
                    # For threads, we estimate based on process totals
                    # In a more advanced setup, we'd use per-thread CPU times
                    cpu_percent = process.cpu_percent() / max(1, len(self.agent_resources))
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    memory_percent = process.memory_percent()
                    thread_count = process.num_threads()
                    
                    resources.add_snapshot(
                        cpu=cpu_percent,
                        memory_mb=memory_mb / max(1, len(self.agent_resources)),  # Estimate per agent
                        memory_pct=memory_percent / max(1, len(self.agent_resources)),
                        threads=thread_count
                    )
        except Exception as e:
            # Log error but don't crash
            print(f"Resource monitoring error: {e}")
    
    def start_monitoring(self, interval: float = 5.0):
        """Start the monitoring thread"""
        if self._monitoring:
            return
        
        self._monitoring = True
        
        def monitor_loop():
            while self._monitoring:
                self._collect_snapshot()
                time.sleep(interval)
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
    
    def get_agent_resources(self, agent_id: str) -> Optional[AgentResources]:
        """Get resources for a specific agent"""
        with self._lock:
            return self.agent_resources.get(agent_id)
    
    def get_all_resources(self) -> Dict[str, AgentResources]:
        """Get resources for all agents"""
        with self._lock:
            return dict(self.agent_resources)
    
    def get_system_summary(self) -> dict:
        """Get overall system resource summary"""
        try:
            process = psutil.Process()
            memory = psutil.virtual_memory()
            
            return {
                "total_agents": len(self.agent_resources),
                "process_cpu_percent": process.cpu_percent(),
                "process_memory_mb": process.memory_info().rss / 1024 / 1024,
                "system_memory_percent": memory.percent,
                "system_memory_available_gb": memory.available / 1024 / 1024 / 1024,
                "system_cpu_percent": psutil.cpu_percent(interval=0.1),
            }
        except Exception as e:
            return {"error": str(e)}


# Global instance
resource_monitor = ResourceMonitor()
