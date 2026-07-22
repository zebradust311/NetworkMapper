from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
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

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for printer vendor matching evidence."""
        vendor = (device.vendor or "").strip().lower()
        if not vendor:
            return RuleResult(
                matched=False,
                confidence_contribution=0,
                reason="Printer vendor rule: vendor is empty",
                suggested_device_type=None,
            )

        if any(keyword in vendor for keyword in SUPPORTED_PRINTER_VENDOR_KEYWORDS):
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason="Printer vendor rule: vendor keyword matched",
                suggested_device_type=DeviceType.PRINTER,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason="Printer vendor rule: no keyword match",
            suggested_device_type=None,
        )
