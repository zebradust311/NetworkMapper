from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import (
    first_matching_port,
    first_matching_product,
    first_matching_service,
    format_hostname_evidence_reason,
    normalize_hostname,
    normalize_vendor,
    service_names,
    service_ports,
)
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

# Cisco IOS/IOS-XE SSH daemons are commonly identified distinctly by Nmap's
# banner-based service detection (e.g. "Cisco SSH"). Treated as additional
# corroboration text only, never as an independent match trigger, so the
# existing hostname-plus-management-signal gate is unchanged.
SWITCH_PRODUCT_KEYWORDS = {"cisco"}


class CiscoSwitchRule(ClassificationRule):
    """Match Cisco vendors as switch devices."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for Cisco switch vendor matching evidence."""
        raw_vendor = device.vendor
        raw_hostname = device.hostname
        vendor = normalize_vendor(raw_vendor, strip=False)
        if "cisco" in vendor:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Vendor {raw_vendor!r} matched known switch vendor.",
                suggested_device_type=DeviceType.SWITCH,
            )

        hostname = normalize_hostname(raw_hostname, strip=False)
        matched_port = first_matching_port(
            service_ports(device.services),
            SWITCH_MANAGEMENT_PORTS,
        )
        matched_service = first_matching_service(
            service_names(device.services),
            SWITCH_MANAGEMENT_SERVICES,
            return_lower=True,
        )
        matched_product = first_matching_product(device.services, SWITCH_PRODUCT_KEYWORDS)
        hostname_looks_like_switch = any(hint in hostname for hint in SWITCH_HOSTNAME_HINTS)
        has_management_signal = matched_port is not None or matched_service is not None

        if hostname_looks_like_switch and has_management_signal:
            reason = format_hostname_evidence_reason(
                raw_hostname,
                matched_port,
                matched_service,
                "switch management",
            )
            if matched_product is not None:
                reason += (
                    f" Detected service product {matched_product!r} matched known "
                    "Cisco product identifier."
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
