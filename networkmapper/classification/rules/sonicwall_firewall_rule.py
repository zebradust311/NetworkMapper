from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


FIREWALL_MANAGEMENT_PORTS = {443, 8443}
FIREWALL_MANAGEMENT_SERVICES = {"https", "ssl/http"}


class SonicWallFirewallRule(ClassificationRule):
    """Match SonicWall vendors as high-confidence firewall devices."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for SonicWall vendor matching evidence."""
        raw_vendor = device.vendor
        raw_hostname = device.hostname
        vendor = (device.vendor or "").strip().lower()
        if vendor == "sonicwall":
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Vendor {raw_vendor!r} matched known firewall vendor.",
                suggested_device_type=DeviceType.FIREWALL,
            )

        hostname = (device.hostname or "").strip().lower()
        matched_port = next(
            (port for port in device.open_ports if port in FIREWALL_MANAGEMENT_PORTS),
            None,
        )
        matched_service = next(
            (
                service.strip().lower()
                for service in device.detected_services
                if service.strip().lower() in FIREWALL_MANAGEMENT_SERVICES
            ),
            None,
        )
        hostname_looks_like_sonicwall = "sonicwall" in hostname or hostname.startswith(
            ("tz", "nsa", "soho")
        )
        has_management_signal = matched_port is not None or matched_service is not None

        if hostname_looks_like_sonicwall and has_management_signal:
            if matched_port is not None and matched_service is not None:
                reason = (
                    f"Hostname {raw_hostname!r} with open port {matched_port} and "
                    f"service {matched_service!r} matched known firewall management evidence."
                )
            elif matched_port is not None:
                reason = (
                    f"Hostname {raw_hostname!r} with open port {matched_port} matched "
                    "known firewall management evidence."
                )
            else:
                reason = (
                    f"Hostname {raw_hostname!r} with service {matched_service!r} matched "
                    "known firewall management evidence."
                )

            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=reason,
                suggested_device_type=DeviceType.FIREWALL,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=f"Vendor {raw_vendor!r} is not a known firewall vendor.",
            suggested_device_type=None,
        )
