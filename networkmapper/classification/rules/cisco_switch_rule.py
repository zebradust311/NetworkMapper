from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


class CiscoSwitchRule(ClassificationRule):
    """Match Cisco vendors as switch devices."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for Cisco switch vendor matching evidence."""
        raw_vendor = device.vendor
        vendor = (device.vendor or "").lower()
        if "cisco" in vendor:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Vendor {raw_vendor!r} matched known switch vendor.",
                suggested_device_type=DeviceType.SWITCH,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=f"Vendor {raw_vendor!r} is not a known switch vendor.",
            suggested_device_type=None,
        )
