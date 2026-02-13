"""Cost anomaly detection — statistical and ML-based baseline analysis."""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AnomalyMethod(Enum):
    """Anomaly detection method."""
    Z_SCORE = "z_score"
    IQR = "iqr"
    EWMA = "ewma"


class AnomalySeverity(Enum):
    """Severity of a detected anomaly."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CostDataPoint:
    """A single cost data point for analysis."""
    value: float
    timestamp: float = field(default_factory=time.time)
    agent_id: str = ""
    task_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
        }


@dataclass
class AnomalyResult:
    """Result of anomaly detection analysis."""
    is_anomaly: bool
    severity: AnomalySeverity
    method: AnomalyMethod
    value: float
    expected_range: tuple[float, float]
    score: float  # Z-score, IQR ratio, or EWMA deviation
    message: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_anomaly": self.is_anomaly,
            "severity": self.severity.value,
            "method": self.method.value,
            "value": round(self.value, 4),
            "expected_range": [round(self.expected_range[0], 4), round(self.expected_range[1], 4)],
            "score": round(self.score, 2),
            "message": self.message,
        }


@dataclass
class BaselineStats:
    """Statistical baseline for cost analysis."""
    mean: float = 0.0
    std_dev: float = 0.0
    median: float = 0.0
    q1: float = 0.0
    q3: float = 0.0
    iqr: float = 0.0
    sample_count: int = 0
    ewma: float = 0.0
    ewma_var: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "mean": round(self.mean, 4),
            "std_dev": round(self.std_dev, 4),
            "median": round(self.median, 4),
            "q1": round(self.q1, 4),
            "q3": round(self.q3, 4),
            "iqr": round(self.iqr, 4),
            "sample_count": self.sample_count,
            "ewma": round(self.ewma, 4),
        }


class CostAnomalyDetector:
    """ML-based cost anomaly detection using statistical methods.

    Supports multiple detection methods:
    - Z-Score: Standard deviation from mean
    - IQR: Interquartile range outlier detection
    - EWMA: Exponentially Weighted Moving Average for trend detection
    """

    def __init__(
        self,
        z_threshold: float = 2.5,
        iqr_multiplier: float = 1.5,
        ewma_alpha: float = 0.3,
        min_samples: int = 10,
        window_size: int = 1000,
    ) -> None:
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier
        self.ewma_alpha = ewma_alpha
        self.min_samples = min_samples
        self._data: deque[CostDataPoint] = deque(maxlen=window_size)
        self._ewma: float = 0.0
        self._ewma_var: float = 0.0
        self._initialized = False
        self._anomalies: list[AnomalyResult] = []

    @property
    def baseline(self) -> BaselineStats:
        """Compute current baseline statistics."""
        values = [d.value for d in self._data]
        if not values:
            return BaselineStats()

        n = len(values)
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n if n > 1 else 0.0
        std_dev = math.sqrt(variance)

        sorted_vals = sorted(values)
        median = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        q1 = sorted_vals[n // 4] if n >= 4 else sorted_vals[0]
        q3 = sorted_vals[3 * n // 4] if n >= 4 else sorted_vals[-1]
        iqr = q3 - q1

        return BaselineStats(
            mean=mean,
            std_dev=std_dev,
            median=median,
            q1=q1,
            q3=q3,
            iqr=iqr,
            sample_count=n,
            ewma=self._ewma,
            ewma_var=self._ewma_var,
        )

    def ingest(self, value: float, agent_id: str = "", task_id: str = "") -> AnomalyResult | None:
        """Ingest a cost data point and check for anomalies.

        Returns AnomalyResult if anomaly detected, None otherwise.
        """
        point = CostDataPoint(value=value, agent_id=agent_id, task_id=task_id)
        self._data.append(point)
        self._update_ewma(value)

        if len(self._data) < self.min_samples:
            return None

        results = [
            self._check_zscore(value),
            self._check_iqr(value),
            self._check_ewma(value),
        ]

        # Take the highest severity anomaly
        anomalies = [r for r in results if r is not None and r.is_anomaly]
        if not anomalies:
            return None

        worst = max(anomalies, key=lambda r: list(AnomalySeverity).index(r.severity))
        self._anomalies.append(worst)
        return worst

    def _update_ewma(self, value: float) -> None:
        """Update EWMA and EWMA variance."""
        if not self._initialized:
            self._ewma = value
            self._ewma_var = 0.0
            self._initialized = True
        else:
            diff = value - self._ewma
            self._ewma = self.ewma_alpha * value + (1 - self.ewma_alpha) * self._ewma
            self._ewma_var = (1 - self.ewma_alpha) * (self._ewma_var + self.ewma_alpha * diff * diff)

    def _check_zscore(self, value: float) -> AnomalyResult | None:
        """Check for anomaly using Z-score method."""
        stats = self.baseline
        if stats.std_dev == 0:
            return None

        z = abs(value - stats.mean) / stats.std_dev
        lower = stats.mean - self.z_threshold * stats.std_dev
        upper = stats.mean + self.z_threshold * stats.std_dev

        if z > self.z_threshold:
            severity = self._zscore_severity(z)
            return AnomalyResult(
                is_anomaly=True,
                severity=severity,
                method=AnomalyMethod.Z_SCORE,
                value=value,
                expected_range=(max(0, lower), upper),
                score=z,
                message=f"Z-score {z:.1f} exceeds threshold {self.z_threshold}",
            )
        return None

    def _check_iqr(self, value: float) -> AnomalyResult | None:
        """Check for anomaly using IQR method."""
        stats = self.baseline
        if stats.iqr == 0:
            return None

        lower = stats.q1 - self.iqr_multiplier * stats.iqr
        upper = stats.q3 + self.iqr_multiplier * stats.iqr

        if value < lower or value > upper:
            distance = max(abs(value - lower), abs(value - upper)) / stats.iqr
            severity = self._iqr_severity(distance)
            return AnomalyResult(
                is_anomaly=True,
                severity=severity,
                method=AnomalyMethod.IQR,
                value=value,
                expected_range=(max(0, lower), upper),
                score=distance,
                message=f"Value outside IQR bounds [{lower:.4f}, {upper:.4f}]",
            )
        return None

    def _check_ewma(self, value: float) -> AnomalyResult | None:
        """Check for anomaly using EWMA method."""
        if self._ewma_var <= 0:
            return None

        ewma_std = math.sqrt(self._ewma_var)
        if ewma_std == 0:
            return None

        deviation = abs(value - self._ewma) / ewma_std
        lower = self._ewma - self.z_threshold * ewma_std
        upper = self._ewma + self.z_threshold * ewma_std

        if deviation > self.z_threshold:
            return AnomalyResult(
                is_anomaly=True,
                severity=self._zscore_severity(deviation),
                method=AnomalyMethod.EWMA,
                value=value,
                expected_range=(max(0, lower), upper),
                score=deviation,
                message=f"EWMA deviation {deviation:.1f} exceeds threshold",
            )
        return None

    @staticmethod
    def _zscore_severity(z: float) -> AnomalySeverity:
        if z > 4.0:
            return AnomalySeverity.CRITICAL
        if z > 3.0:
            return AnomalySeverity.HIGH
        if z > 2.5:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW

    @staticmethod
    def _iqr_severity(distance: float) -> AnomalySeverity:
        if distance > 3.0:
            return AnomalySeverity.CRITICAL
        if distance > 2.0:
            return AnomalySeverity.HIGH
        if distance > 1.5:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW

    @property
    def anomalies(self) -> list[AnomalyResult]:
        return self._anomalies

    def summary(self) -> dict[str, Any]:
        return {
            "baseline": self.baseline.to_dict(),
            "total_anomalies": len(self._anomalies),
            "by_method": {
                m.value: sum(1 for a in self._anomalies if a.method == m)
                for m in AnomalyMethod
            },
            "by_severity": {
                s.value: sum(1 for a in self._anomalies if a.severity == s)
                for s in AnomalySeverity
            },
        }
