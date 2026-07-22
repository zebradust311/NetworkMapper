from __future__ import annotations

from dataclasses import dataclass

from networkmapper.core.models import DeviceType


@dataclass(frozen=True)
class RuleResult:
    """Represent the outcome of evaluating a single classification rule."""

    matched: bool
    confidence_contribution: int
    reason: str
    suggested_device_type: DeviceType | None
