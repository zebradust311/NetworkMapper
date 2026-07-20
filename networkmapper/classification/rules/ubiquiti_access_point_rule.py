from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.core.models import Device, DeviceType


class UbiquitiAccessPointRule(ClassificationRule):
    """Match Ubiquiti access points identified by UAP/U6/U7 hostname prefixes."""

    def classify(self, device: Device) -> DeviceType | None:
        """Return ACCESS_POINT when a Ubiquiti device matches the expected hostname patterns."""
        vendor = (device.vendor or "").lower()
        hostname = (device.hostname or "").strip()

        if vendor != "ubiquiti" or not hostname:
            return None

        hostname_prefix = hostname.lower().split("-", 1)[0]
        if hostname_prefix in {"uap", "u6", "u7"}:
            return DeviceType.ACCESS_POINT

        return None
