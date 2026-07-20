from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.core.models import Device, DeviceType


SUPPORTED_VOICE_VENDOR_KEYWORDS = (
    "yealink",
    "poly",
    "polycom",
    "grandstream",
    "mitel",
    "avaya",
    "cisco ip phone",
)


class VoiceVendorRule(ClassificationRule):
    """Match common enterprise VoIP phone vendors as phone devices."""

    def classify(self, device: Device) -> DeviceType | None:
        """Return PHONE when the vendor matches a supported voice manufacturer."""
        vendor = (device.vendor or "").strip().lower()
        if not vendor:
            return None

        if any(keyword in vendor for keyword in SUPPORTED_VOICE_VENDOR_KEYWORDS):
            return DeviceType.PHONE
        return None
