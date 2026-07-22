from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


class SonicWallFirewallRule(ClassificationRule):
    """Match SonicWall vendors as high-confidence firewall devices."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for SonicWall vendor matching evidence."""
        raw_vendor = device.vendor or ""
        vendor = (device.vendor or "").strip().lower()
        if vendor == "sonicwall":
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Vendor '{raw_vendor}' matched known firewall vendor.",
                suggested_device_type=DeviceType.FIREWALL,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason="Vendor did not match SonicWall firewall rule.",
            suggested_device_type=None,
        )
