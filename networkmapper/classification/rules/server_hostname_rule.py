from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.core.models import Device, DeviceType


class ServerHostnameRule(ClassificationRule):
    """Match hostnames that indicate a server, such as those containing 'dc' or 'cam'."""

    def classify(self, device: Device) -> DeviceType | None:
        """Return SERVER when the hostname contains a recognized server signal."""
        hostname = (device.hostname or "").lower()
        if "dc" in hostname or "cam" in hostname:
            return DeviceType.SERVER
        return None
