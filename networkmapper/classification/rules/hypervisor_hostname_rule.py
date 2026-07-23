from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


HYPERVISOR_HOSTNAME_KEYWORDS = (
    "esx",
    "esxi",
    "hyperv",
    "vcenter",
    "vmhost",
)


class HypervisorHostnameRule(ClassificationRule):
    """Match hostnames that indicate a hypervisor, such as those containing 'vsh'."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for hypervisor hostname matching evidence."""
        raw_hostname = device.hostname
        hostname = (device.hostname or "").lower()
        if "vsh" in hostname:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Hostname {raw_hostname!r} matched known hypervisor naming convention.",
                suggested_device_type=DeviceType.HYPERVISOR,
            )

        if any(keyword in hostname for keyword in HYPERVISOR_HOSTNAME_KEYWORDS):
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=(
                    f"Hostname {raw_hostname!r} matched known hypervisor naming convention."
                ),
                suggested_device_type=DeviceType.HYPERVISOR,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=f"Hostname {raw_hostname!r} did not match known hypervisor naming conventions.",
            suggested_device_type=None,
        )
