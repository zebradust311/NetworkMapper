from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import (
    first_matching_identifier,
    first_matching_port,
    first_matching_service,
    format_hostname_evidence_reason,
    normalize_hostname,
    normalize_vendor,
    service_names,
    service_ports,
)
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


FIREWALL_MANAGEMENT_PORTS = {443, 8443}
FIREWALL_MANAGEMENT_SERVICES = {"https", "ssl/http"}

# SonicWall's HTTPS management interface commonly self-identifies its own
# brand in its page title or self-signed certificate subject/issuer
# (FEAT-003F) — a device serving content that names its own vendor is at
# least as strong an identifier as the MAC-OUI-derived vendor field, so
# this is treated as an independent match tier rather than mere
# corroboration, consistent with PrinterVendorRule's product-tier
# precedent (FEAT-003D).
FIREWALL_IDENTIFIER_KEYWORDS = {"sonicwall"}


class SonicWallFirewallRule(ClassificationRule):
    """Match SonicWall vendors as high-confidence firewall devices."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for SonicWall vendor matching evidence."""
        raw_vendor = device.vendor
        raw_hostname = device.hostname
        vendor = normalize_vendor(raw_vendor, strip=True)
        if vendor == "sonicwall":
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Vendor {raw_vendor!r} matched known firewall vendor.",
                suggested_device_type=DeviceType.FIREWALL,
            )

        matched_identifier = first_matching_identifier(device.services, FIREWALL_IDENTIFIER_KEYWORDS)
        if matched_identifier is not None:
            label, value = matched_identifier
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=(
                    f"Detected {label} {value!r} matched known firewall vendor "
                    "identifier."
                ),
                suggested_device_type=DeviceType.FIREWALL,
            )

        hostname = normalize_hostname(raw_hostname, strip=True)
        matched_port = first_matching_port(
            service_ports(device.services),
            FIREWALL_MANAGEMENT_PORTS,
        )
        matched_service = first_matching_service(
            service_names(device.services),
            FIREWALL_MANAGEMENT_SERVICES,
            return_lower=True,
        )
        hostname_looks_like_sonicwall = "sonicwall" in hostname or hostname.startswith(
            ("tz", "nsa", "soho")
        )
        has_management_signal = matched_port is not None or matched_service is not None

        if hostname_looks_like_sonicwall and has_management_signal:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=format_hostname_evidence_reason(
                    raw_hostname,
                    matched_port,
                    matched_service,
                    "firewall management",
                ),
                suggested_device_type=DeviceType.FIREWALL,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=f"Vendor {raw_vendor!r} is not a known firewall vendor.",
            suggested_device_type=None,
        )
