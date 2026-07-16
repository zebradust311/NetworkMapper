from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.core.models import Device, DeviceType


class DellWorkstationRule(ClassificationRule):
    """Match Dell vendors as workstation devices."""

    def classify(self, device: Device) -> DeviceType | None:
        """Return WORKSTATION when the device vendor contains Dell."""
        vendor = (device.vendor or "").lower()
        if "dell" in vendor:
            return DeviceType.WORKSTATION
        return None
