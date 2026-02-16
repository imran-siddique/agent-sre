"""
Webhook Alerting for Agent-SRE.

Send alerts to external systems when SLO breaches, incidents,
or cost anomalies are detected. Supports multiple channels.

No external dependencies — uses urllib for HTTP calls.
Includes formatters for Slack, PagerDuty, and generic webhooks.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class AlertChannel(Enum):
    """Supported alert channel types."""

    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    GENERIC_WEBHOOK = "generic_webhook"
    CALLBACK = "callback"  # In-process callback (for testing)


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """An alert to be sent to external systems."""

    title: str
    message: str
    severity: AlertSeverity = AlertSeverity.WARNING
    source: str = "agent-sre"
    agent_id: str = ""
    slo_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    dedup_key: str = ""  # For PagerDuty deduplication

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "source": self.source,
            "agent_id": self.agent_id,
            "slo_name": self.slo_name,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ChannelConfig:
    """Configuration for an alert channel."""

    channel_type: AlertChannel
    name: str
    url: str = ""  # Webhook URL
    token: str = ""  # Auth token (for PagerDuty routing key, etc.)
    callback: Optional[Callable[[Alert], None]] = None  # For CALLBACK type
    min_severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True


@dataclass
class DeliveryResult:
    """Result of attempting to deliver an alert."""

    channel_name: str
    success: bool
    status_code: int = 0
    error: str = ""
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def format_slack(alert: Alert) -> Dict[str, Any]:
    """Format alert as Slack incoming webhook payload."""
    severity_emoji = {
        AlertSeverity.INFO: "ℹ️",
        AlertSeverity.WARNING: "⚠️",
        AlertSeverity.CRITICAL: "🚨",
        AlertSeverity.RESOLVED: "✅",
    }
    emoji = severity_emoji.get(alert.severity, "📋")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} {alert.title}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": alert.message},
        },
    ]

    fields = []
    if alert.agent_id:
        fields.append({"type": "mrkdwn", "text": f"*Agent:* {alert.agent_id}"})
    if alert.slo_name:
        fields.append({"type": "mrkdwn", "text": f"*SLO:* {alert.slo_name}"})
    fields.append({"type": "mrkdwn", "text": f"*Severity:* {alert.severity.value}"})

    if fields:
        blocks.append({"type": "section", "fields": fields})

    return {"blocks": blocks}


def format_pagerduty(alert: Alert) -> Dict[str, Any]:
    """Format alert as PagerDuty Events API v2 payload."""
    pd_severity = {
        AlertSeverity.INFO: "info",
        AlertSeverity.WARNING: "warning",
        AlertSeverity.CRITICAL: "critical",
        AlertSeverity.RESOLVED: "info",
    }

    event_action = "resolve" if alert.severity == AlertSeverity.RESOLVED else "trigger"

    payload: Dict[str, Any] = {
        "event_action": event_action,
        "payload": {
            "summary": f"{alert.title}: {alert.message}",
            "severity": pd_severity.get(alert.severity, "warning"),
            "source": alert.source,
            "component": alert.agent_id or "agent-sre",
            "group": alert.slo_name or "default",
            "custom_details": alert.metadata,
        },
    }

    if alert.dedup_key:
        payload["dedup_key"] = alert.dedup_key

    return payload


def format_generic(alert: Alert) -> Dict[str, Any]:
    """Format alert as generic JSON webhook payload."""
    return alert.to_dict()


# ---------------------------------------------------------------------------
# AlertManager
# ---------------------------------------------------------------------------


class AlertManager:
    """
    Manages alert channels and dispatches alerts.

    Usage:
        manager = AlertManager()
        manager.add_channel(ChannelConfig(
            channel_type=AlertChannel.SLACK,
            name="ops-slack",
            url="https://hooks.slack.com/services/...",
        ))

        manager.send(Alert(
            title="SLO Breach",
            message="Error budget exhausted for agent-1",
            severity=AlertSeverity.CRITICAL,
        ))
    """

    def __init__(self) -> None:
        self._channels: Dict[str, ChannelConfig] = {}
        self._history: List[DeliveryResult] = []
        self._formatters = {
            AlertChannel.SLACK: format_slack,
            AlertChannel.PAGERDUTY: format_pagerduty,
            AlertChannel.GENERIC_WEBHOOK: format_generic,
            AlertChannel.CALLBACK: format_generic,
        }

    def add_channel(self, config: ChannelConfig) -> None:
        self._channels[config.name] = config

    def remove_channel(self, name: str) -> None:
        self._channels.pop(name, None)

    def list_channels(self) -> List[str]:
        return list(self._channels.keys())

    def send(self, alert: Alert) -> List[DeliveryResult]:
        """Send alert to all matching channels."""
        results: List[DeliveryResult] = []
        severity_order = [AlertSeverity.INFO, AlertSeverity.WARNING,
                          AlertSeverity.CRITICAL, AlertSeverity.RESOLVED]

        for name, config in self._channels.items():
            if not config.enabled:
                continue

            # Check minimum severity
            alert_idx = severity_order.index(alert.severity) if alert.severity in severity_order else 0
            min_idx = severity_order.index(config.min_severity) if config.min_severity in severity_order else 0
            if alert_idx < min_idx:
                continue

            result = self._deliver(config, alert)
            results.append(result)
            self._history.append(result)

        return results

    def _deliver(self, config: ChannelConfig, alert: Alert) -> DeliveryResult:
        """Deliver alert to a single channel."""
        try:
            if config.channel_type == AlertChannel.CALLBACK:
                if config.callback:
                    config.callback(alert)
                return DeliveryResult(channel_name=config.name, success=True)

            formatter = self._formatters.get(config.channel_type, format_generic)
            payload = formatter(alert)

            # Add auth token for PagerDuty
            if config.channel_type == AlertChannel.PAGERDUTY and config.token:
                payload["routing_key"] = config.token

            return self._http_post(config.name, config.url, payload)

        except Exception as e:
            return DeliveryResult(
                channel_name=config.name,
                success=False,
                error=str(e),
            )

    def _http_post(self, channel_name: str, url: str, payload: Dict) -> DeliveryResult:
        """Send HTTP POST. Isolated for testability."""
        if not url:
            return DeliveryResult(
                channel_name=channel_name,
                success=False,
                error="No URL configured",
            )

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return DeliveryResult(
                    channel_name=channel_name,
                    success=True,
                    status_code=resp.status,
                )
        except urllib.error.HTTPError as e:
            return DeliveryResult(
                channel_name=channel_name,
                success=False,
                status_code=e.code,
                error=str(e),
            )
        except Exception as e:
            return DeliveryResult(
                channel_name=channel_name,
                success=False,
                error=str(e),
            )

    @property
    def history(self) -> List[DeliveryResult]:
        return list(self._history)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "channels": len(self._channels),
            "total_sent": len(self._history),
            "successful": sum(1 for r in self._history if r.success),
            "failed": sum(1 for r in self._history if not r.success),
        }

    def clear_history(self) -> None:
        self._history.clear()
