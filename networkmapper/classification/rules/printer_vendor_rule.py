from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.core.models import Device, DeviceType


SUPPORTED_PRINTER_VENDOR_KEYWORDS = (
    "brother",
    "hp",
    "hewlett-packard",
    "hewlett packard",
    "canon",
    "ricoh",
    "konica minolta",
    "epson",
    "xerox",
    "lexmark",
    "kyocera",
    "sharp",
    "toshiba",
    "zebra",
    "datamax",
    "fujifilm business innovation",
)


class PrinterVendorRule(ClassificationRule):
    """Match vendors that indicate a printer device."""

    def classify(self, device: Device) -> DeviceType | None:
        """Return PRINTER when the vendor matches one of the printer brands."""
        vendor = (device.vendor or "").strip().lower()
        if not vendor:
            return None

        if any(keyword in vendor for keyword in SUPPORTED_PRINTER_VENDOR_KEYWORDS):
            return DeviceType.PRINTER
        return None
