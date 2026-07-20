from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.core.models import Device, DeviceType


class SonicWallFirewallRule(ClassificationRule):
    """Match SonicWall vendors as high-confidence firewall devices."""

    def classify(self, device: Device) -> DeviceType | None:
        """Return FIREWALL when the vendor is SonicWall, case-insensitively."""
        vendor = (device.vendor or "").strip().lower()
        if vendor == "sonicwall":
            return DeviceType.FIREWALL
        return None
