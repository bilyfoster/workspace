"""
Activity Alert System for Workspace

Configurable notifications for critical events.
Supports multiple notification channels and alert rules.
"""
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json

from shared.bus.message_bus import MessageBus, Message, MessageType

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertChannel(Enum):
    DASHBOARD = "dashboard"      # In-app notification
    LOG = "log"                  # Log file
    WEBHOOK = "webhook"          # HTTP webhook
    EMAIL = "email"              # Email notification (future)
    TELEGRAM = "telegram"        # Telegram bot (future)

@dataclass
class AlertRule:
    """A rule for triggering alerts"""
    id: str
    name: str
    description: str
    event_types: List[str]
    severity: AlertSeverity
    conditions: Dict[str, Any]  # e.g., {"agent_status": "error"}
    channels: List[AlertChannel]
    cooldown_minutes: int = 5
    enabled: bool = True
    last_triggered: Optional[str] = None

@dataclass
class Alert:
    """An alert instance"""
    id: str
    rule_id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: str
    source: str  # What triggered it
    metadata: Dict[str, Any]
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None

class AlertManager:
    """
    Manages activity alerts for Workspace
    
    Features:
    - Rule-based alert triggering
    - Multiple notification channels
    - Alert history and acknowledgment
    - Cooldown periods to prevent spam
    - Custom alert conditions
    """
    
    def __init__(self):
        self.bus = MessageBus()
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self.max_alerts = 1000
        
        # Callbacks for different channels
        self.channel_handlers: Dict[AlertChannel, Callable] = {
            AlertChannel.DASHBOARD: self._send_dashboard_alert,
            AlertChannel.LOG: self._send_log_alert,
            AlertChannel.WEBHOOK: self._send_webhook_alert,
        }
        
        # Default rules
        self._setup_default_rules()
        
        # Subscribe to events
        self._setup_subscriptions()
        
        logger.info("AlertManager initialized")
    
    def _setup_default_rules(self):
        """Set up default alert rules"""
        default_rules = [
            AlertRule(
                id="agent_offline",
                name="Agent Went Offline",
                description="Alert when an agent process unexpectedly stops",
                event_types=["agent_offline"],
                severity=AlertSeverity.WARNING,
                conditions={},
                channels=[AlertChannel.DASHBOARD, AlertChannel.LOG],
                cooldown_minutes=1
            ),
            AlertRule(
                id="task_failed",
                name="Task Failed",
                description="Alert when an agent fails to complete a task",
                event_types=["task_failed"],
                severity=AlertSeverity.ERROR,
                conditions={},
                channels=[AlertChannel.DASHBOARD, AlertChannel.LOG],
                cooldown_minutes=0
            ),
            AlertRule(
                id="high_error_rate",
                name="High Error Rate",
                description="Alert when multiple tasks fail in short succession",
                event_types=["task_failed"],
                severity=AlertSeverity.CRITICAL,
                conditions={"threshold": 3, "window_minutes": 10},
                channels=[AlertChannel.DASHBOARD, AlertChannel.LOG],
                cooldown_minutes=15
            ),
            AlertRule(
                id="mission_completed",
                name="Mission Completed",
                description="Notification when a mission is successfully completed",
                event_types=["mission_completed"],
                severity=AlertSeverity.INFO,
                conditions={},
                channels=[AlertChannel.DASHBOARD],
                cooldown_minutes=0
            ),
            AlertRule(
                id="handoff_rejected",
                name="Handoff Rejected",
                description="Alert when an agent rejects a handoff request",
                event_types=["handoff_reject"],
                severity=AlertSeverity.WARNING,
                conditions={},
                channels=[AlertChannel.DASHBOARD, AlertChannel.LOG],
                cooldown_minutes=0
            ),
            AlertRule(
                id="agent_error",
                name="Agent Error State",
                description="Alert when an agent enters error state",
                event_types=["agent_status"],
                severity=AlertSeverity.ERROR,
                conditions={"status": "error"},
                channels=[AlertChannel.DASHBOARD, AlertChannel.LOG],
                cooldown_minutes=5
            ),
        ]
        
        for rule in default_rules:
            self.rules[rule.id] = rule
    
    def _setup_subscriptions(self):
        """Subscribe to message bus events"""
        for event_type in MessageType:
            self.bus.subscribe(event_type, self._on_event)
    
    def _on_event(self, message: Message):
        """Handle incoming events and check alert rules"""
        event_type = message.type
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            if event_type not in rule.event_types:
                continue
            
            # Check cooldown
            if rule.last_triggered:
                last = datetime.fromisoformat(rule.last_triggered)
                elapsed = (datetime.now() - last).total_seconds() / 60
                if elapsed < rule.cooldown_minutes:
                    continue
            
            # Check conditions
            if self._check_conditions(rule.conditions, message):
                self._trigger_alert(rule, message)
                rule.last_triggered = datetime.now().isoformat()
    
    def _check_conditions(self, conditions: Dict[str, Any], message: Message) -> bool:
        """Check if message meets alert rule conditions"""
        if not conditions:
            return True
        
        payload = message.payload
        
        for key, value in conditions.items():
            if key == "threshold":
                # Special handling for threshold conditions
                continue  # Handled separately
            
            if key in payload:
                if payload[key] != value:
                    return False
        
        return True
    
    def _trigger_alert(self, rule: AlertRule, message: Message):
        """Trigger an alert"""
        import uuid
        
        alert = Alert(
            id=str(uuid.uuid4())[:8],
            rule_id=rule.id,
            severity=rule.severity,
            title=rule.name,
            message=self._build_alert_message(rule, message),
            timestamp=datetime.now().isoformat(),
            source=message.sender,
            metadata={
                "event_type": message.type,
                "payload": message.payload,
                "correlation_id": message.correlation_id
            }
        )
        
        self.alerts.append(alert)
        
        # Trim old alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Send through configured channels
        for channel in rule.channels:
            if channel in self.channel_handlers:
                try:
                    self.channel_handlers[channel](alert)
                except Exception as e:
                    logger.error(f"Failed to send alert via {channel}: {e}")
        
        logger.info(f"Alert triggered: {rule.name} ({rule.severity.value})")
    
    def _build_alert_message(self, rule: AlertRule, message: Message) -> str:
        """Build human-readable alert message"""
        event_type = message.type
        sender = message.sender
        
        if event_type == "agent_offline":
            return f"Agent {message.payload.get('name', sender)} has gone offline"
        
        elif event_type == "task_failed":
            return f"Task failed for {sender}: {message.payload.get('error', 'Unknown error')}"
        
        elif event_type == "mission_completed":
            return f"Mission '{message.payload.get('title', 'Unknown')}' completed successfully"
        
        elif event_type == "handoff_reject":
            return f"Handoff rejected: {message.payload.get('reason', 'No reason given')}"
        
        else:
            return f"{rule.name}: Event from {sender}"
    
    def _send_dashboard_alert(self, alert: Alert):
        """Send alert to dashboard (in-app)"""
        # This will be picked up by the dashboard
        self.bus.publish(Message.create(
            MessageType.SYSTEM_MESSAGE,
            sender="alert_manager",
            recipient=None,  # Broadcast
            payload={
                "alert_id": alert.id,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp
            }
        ))
    
    def _send_log_alert(self, alert: Alert):
        """Send alert to log file"""
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }.get(alert.severity, logging.WARNING)
        
        logger.log(log_level, f"[ALERT] {alert.title}: {alert.message}")
    
    def _send_webhook_alert(self, alert: Alert):
        """Send alert via HTTP webhook (placeholder)"""
        # TODO: Implement webhook call
        logger.debug(f"Would send webhook alert: {alert.title}")
    
    def add_rule(self, rule: AlertRule) -> str:
        """Add a custom alert rule"""
        self.rules[rule.id] = rule
        return rule.id
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now().isoformat()
                return True
        return False
    
    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get active (unacknowledged) alerts"""
        alerts = [a for a in self.alerts if not a.acknowledged]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        alerts = sorted(alerts, key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                "id": a.id,
                "severity": a.severity.value,
                "title": a.title,
                "message": a.message,
                "timestamp": a.timestamp,
                "source": a.source,
                "rule_id": a.rule_id
            }
            for a in alerts[:limit]
        ]
    
    def get_alert_history(
        self,
        include_acknowledged: bool = True,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get alert history"""
        alerts = self.alerts if include_acknowledged else [a for a in self.alerts if not a.acknowledged]
        alerts = sorted(alerts, key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                "id": a.id,
                "severity": a.severity.value,
                "title": a.title,
                "message": a.message,
                "timestamp": a.timestamp,
                "source": a.source,
                "acknowledged": a.acknowledged,
                "acknowledged_by": a.acknowledged_by
            }
            for a in alerts[:limit]
        ]
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all alert rules"""
        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "event_types": r.event_types,
                "severity": r.severity.value,
                "channels": [c.value for c in r.channels],
                "enabled": r.enabled,
                "cooldown_minutes": r.cooldown_minutes
            }
            for r in self.rules.values()
        ]

# Global instance
alert_manager = AlertManager()
