from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.core.models import Device, DeviceType


class PrinterVendorRule(ClassificationRule):
    """Match vendors that indicate a printer device."""

    def classify(self, device: Device) -> DeviceType | None:
        """Return PRINTER when the vendor matches one of the printer brands."""
        vendor = (device.vendor or "").lower()
        if any(
            keyword in vendor
            for keyword in ("brother", "canon", "hewlett packard", "hp")
        ):
            return DeviceType.PRINTER
        return None
