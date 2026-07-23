from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


SERVER_HOSTNAME_KEYWORDS = (
    "srv",
    "server",
)


class ServerHostnameRule(ClassificationRule):
    """Match hostnames that indicate a server, such as those containing 'dc' or 'cam'."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for server hostname matching evidence."""
        raw_hostname = device.hostname
        hostname = (device.hostname or "").lower()
        if "dc" in hostname or "cam" in hostname:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Hostname {raw_hostname!r} matched known server naming convention.",
                suggested_device_type=DeviceType.SERVER,
            )

        if any(keyword in hostname for keyword in SERVER_HOSTNAME_KEYWORDS):
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=(
                    f"Hostname {raw_hostname!r} matched known server naming pattern."
                ),
                suggested_device_type=DeviceType.SERVER,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=f"Hostname {raw_hostname!r} did not match known server naming patterns.",
            suggested_device_type=None,
        )
