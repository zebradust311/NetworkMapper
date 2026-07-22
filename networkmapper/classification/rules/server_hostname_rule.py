from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


class ServerHostnameRule(ClassificationRule):
    """Match hostnames that indicate a server, such as those containing 'dc' or 'cam'."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for server hostname matching evidence."""
        raw_hostname = device.hostname or ""
        hostname = (device.hostname or "").lower()
        if "dc" in hostname or "cam" in hostname:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=(
                    f"Hostname '{raw_hostname}' matched known server naming convention."
                ),
                suggested_device_type=DeviceType.SERVER,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason="Hostname did not match known server naming conventions.",
            suggested_device_type=None,
        )
