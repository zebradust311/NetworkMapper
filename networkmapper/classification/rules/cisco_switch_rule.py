from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


SWITCH_HOSTNAME_HINTS = (
    "switch",
    "sw-",
    "core-sw",
    "dist-sw",
    "access-sw",
)
SWITCH_MANAGEMENT_PORTS = {22, 23, 161}
SWITCH_MANAGEMENT_SERVICES = {"ssh", "telnet", "snmp"}


class CiscoSwitchRule(ClassificationRule):
    """Match Cisco vendors as switch devices."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for Cisco switch vendor matching evidence."""
        raw_vendor = device.vendor
        raw_hostname = device.hostname
        vendor = (device.vendor or "").lower()
        if "cisco" in vendor:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Vendor {raw_vendor!r} matched known switch vendor.",
                suggested_device_type=DeviceType.SWITCH,
            )

        hostname = (device.hostname or "").lower()
        matched_port = next(
            (port for port in device.open_ports if port in SWITCH_MANAGEMENT_PORTS),
            None,
        )
        matched_service = next(
            (
                service.strip().lower()
                for service in device.detected_services
                if service.strip().lower() in SWITCH_MANAGEMENT_SERVICES
            ),
            None,
        )
        hostname_looks_like_switch = any(hint in hostname for hint in SWITCH_HOSTNAME_HINTS)
        has_management_signal = matched_port is not None or matched_service is not None

        if hostname_looks_like_switch and has_management_signal:
            if matched_port is not None and matched_service is not None:
                reason = (
                    f"Hostname {raw_hostname!r} with open port {matched_port} and "
                    f"service {matched_service!r} matched known switch management evidence."
                )
            elif matched_port is not None:
                reason = (
                    f"Hostname {raw_hostname!r} with open port {matched_port} matched "
                    "known switch management evidence."
                )
            else:
                reason = (
                    f"Hostname {raw_hostname!r} with service {matched_service!r} matched "
                    "known switch management evidence."
                )

            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=reason,
                suggested_device_type=DeviceType.SWITCH,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=f"Vendor {raw_vendor!r} is not a known switch vendor.",
            suggested_device_type=None,
        )
