from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
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

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for voice vendor matching evidence."""
        raw_vendor = device.vendor
        vendor = (device.vendor or "").strip().lower()
        if not vendor:
            return RuleResult(
                matched=False,
                confidence_contribution=0,
                reason=f"Vendor {raw_vendor!r} is not a known voice device vendor.",
                suggested_device_type=None,
            )

        if any(keyword in vendor for keyword in SUPPORTED_VOICE_VENDOR_KEYWORDS):
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Vendor {raw_vendor!r} matched known voice device vendor.",
                suggested_device_type=DeviceType.PHONE,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=f"Vendor {raw_vendor!r} is not a known voice device vendor.",
            suggested_device_type=None,
        )
