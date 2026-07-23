from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


class UbiquitiAccessPointRule(ClassificationRule):
    """Match Ubiquiti access points identified by UAP/U6/U7 hostname prefixes."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for Ubiquiti wireless infrastructure evidence."""
        raw_vendor = device.vendor
        raw_hostname = device.hostname
        vendor = (device.vendor or "").lower()
        hostname = (device.hostname or "").strip()

        if vendor != "ubiquiti" or not hostname:
            return RuleResult(
                matched=False,
                confidence_contribution=0,
                reason=(
                    f"Vendor {raw_vendor!r} and hostname {raw_hostname!r} did not match "
                    "known wireless infrastructure vendor patterns."
                ),
                suggested_device_type=None,
            )

        hostname_prefix = hostname.lower().split("-", 1)[0]
        if hostname_prefix in {"uap", "u6", "u7"}:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=(
                    f"Vendor {raw_vendor!r} and hostname {raw_hostname!r} matched "
                    "known wireless infrastructure vendor."
                ),
                suggested_device_type=DeviceType.ACCESS_POINT,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=(
                f"Vendor {raw_vendor!r} and hostname {raw_hostname!r} did not match "
                "known wireless infrastructure vendor patterns."
            ),
            suggested_device_type=None,
        )
