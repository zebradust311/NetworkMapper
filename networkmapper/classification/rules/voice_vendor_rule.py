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

VOICE_HOSTNAME_KEYWORDS = (
    "phone",
    "voip",
    "handset",
)

VOICE_SIGNAL_PORTS = {5060, 5061}
VOICE_SIGNAL_SERVICES = (
    "sip",
    "sips",
)


class VoiceVendorRule(ClassificationRule):
    """Match common enterprise VoIP phone vendors as phone devices."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for voice vendor matching evidence."""
        raw_vendor = device.vendor
        raw_hostname = device.hostname
        vendor = (device.vendor or "").strip().lower()
        hostname = (device.hostname or "").strip().lower()
        if not vendor:
            return self._match_by_hostname_and_signals(raw_hostname, hostname, device)

        if any(keyword in vendor for keyword in SUPPORTED_VOICE_VENDOR_KEYWORDS):
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Vendor {raw_vendor!r} matched known voice device vendor.",
                suggested_device_type=DeviceType.PHONE,
            )

        return self._match_by_hostname_and_signals(raw_hostname, hostname, device)

    def _match_by_hostname_and_signals(
        self,
        raw_hostname: str | None,
        hostname: str,
        device: Device,
    ) -> RuleResult:
        if not any(keyword in hostname for keyword in VOICE_HOSTNAME_KEYWORDS):
            return RuleResult(
                matched=False,
                confidence_contribution=0,
                reason=f"Vendor {device.vendor!r} is not a known voice device vendor.",
                suggested_device_type=None,
            )

        matched_port = next(
            (port for port in device.open_ports if port in VOICE_SIGNAL_PORTS),
            None,
        )
        matched_service = next(
            (
                service.strip()
                for service in device.detected_services
                if service.strip().lower() in VOICE_SIGNAL_SERVICES
            ),
            None,
        )

        if matched_port is None and matched_service is None:
            return RuleResult(
                matched=False,
                confidence_contribution=0,
                reason=f"Vendor {device.vendor!r} is not a known voice device vendor.",
                suggested_device_type=None,
            )

        if matched_port is not None and matched_service is not None:
            reason = (
                f"Hostname {raw_hostname!r} with open port {matched_port} and service "
                f"{matched_service!r} matched known voice device evidence."
            )
        elif matched_port is not None:
            reason = (
                f"Hostname {raw_hostname!r} with open port {matched_port} matched known "
                "voice device evidence."
            )
        else:
            reason = (
                f"Hostname {raw_hostname!r} with service {matched_service!r} matched known "
                "voice device evidence."
            )

        return RuleResult(
            matched=True,
            confidence_contribution=0,
            reason=reason,
            suggested_device_type=DeviceType.PHONE,
        )
