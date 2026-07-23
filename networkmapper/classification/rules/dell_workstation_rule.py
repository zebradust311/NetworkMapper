from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


class DellWorkstationRule(ClassificationRule):
    """Match Dell vendors as workstation devices."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for workstation vendor matching evidence."""
        raw_vendor = device.vendor
        vendor = (device.vendor or "").lower()
        if "dell" in vendor:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Vendor {raw_vendor!r} matched known workstation vendor.",
                suggested_device_type=DeviceType.WORKSTATION,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=f"Vendor {raw_vendor!r} is not a known workstation vendor.",
            suggested_device_type=None,
        )
