from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.core.models import Device, DeviceType


class HypervisorHostnameRule(ClassificationRule):
    """Match hostnames that indicate a hypervisor, such as those containing 'vsh'."""

    def classify(self, device: Device) -> DeviceType | None:
        """Return HYPERVISOR when the hostname contains the hypervisor signal."""
        hostname = (device.hostname or "").lower()
        if "vsh" in hostname:
            return DeviceType.HYPERVISOR
        return None
