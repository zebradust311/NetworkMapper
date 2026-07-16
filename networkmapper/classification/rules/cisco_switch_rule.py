from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.core.models import Device, DeviceType


class CiscoSwitchRule(ClassificationRule):
    """Match Cisco vendors as switch devices."""

    def classify(self, device: Device) -> DeviceType | None:
        """Return SWITCH when the device vendor contains Cisco."""
        vendor = (device.vendor or "").lower()
        if "cisco" in vendor:
            return DeviceType.SWITCH
        return None
