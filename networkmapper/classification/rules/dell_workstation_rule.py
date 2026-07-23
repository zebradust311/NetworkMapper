from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


DELL_WORKSTATION_HOSTNAME_KEYWORDS = (
    "optiplex",
    "latitude",
    "precision",
    "xps",
    "vostro",
    "inspiron",
)


class DellWorkstationRule(ClassificationRule):
    """Match Dell vendors as workstation devices."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for workstation vendor matching evidence."""
        raw_vendor = device.vendor
        raw_hostname = device.hostname
        vendor = (device.vendor or "").lower()
        hostname = (device.hostname or "").lower()
        if "dell" in vendor:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Vendor {raw_vendor!r} matched known workstation vendor.",
                suggested_device_type=DeviceType.WORKSTATION,
            )

        if any(keyword in hostname for keyword in DELL_WORKSTATION_HOSTNAME_KEYWORDS):
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=(
                    f"Hostname {raw_hostname!r} matched known Dell workstation naming pattern."
                ),
                suggested_device_type=DeviceType.WORKSTATION,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=(
                f"Vendor {raw_vendor!r} and hostname {raw_hostname!r} did not match "
                "known workstation indicators."
            ),
            suggested_device_type=None,
        )
