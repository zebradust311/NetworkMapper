from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import (
    first_matching_identifier,
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

# Model/product identity strings that name a switch explicitly, surfaced via
# Nmap's product detection or the http-title/ssl-cert NSE scripts (FEAT-003D/
# FEAT-003F). This is an independent match trigger, not corroboration only,
# because an explicit switch identity is at least as strong as the bare
# vendor match above -- the same match-tier precedent PrinterVendorRule
# established for its own identifier tier. RULE-002 added this tier because
# HP ProCurve switches self-identify as "ProCurve" in their management UI
# title/product string, and Ubiquiti EdgeSwitch devices self-identify as
# "EdgeSwitch" the same way, but neither vendor string alone is an
# unambiguous switch indicator (HP also makes printers; Ubiquiti also makes
# access points), so a plain vendor keyword can't safely cover them.
#
# RULE-004: also checked against SNMP `sysDescr` (via `first_matching_
# identifier`'s optional `snmp_sys_descr` parameter), since both keywords
# are literal product-line names a switch's own SNMP self-description
# would plausibly contain (e.g. a ProCurve switch's sysDescr commonly
# starts with "ProCurve..."). Deliberately not extended with a bare
# "cisco" keyword here even though ARCH-012 cites "Cisco IOS Software,
# C2960..." as a realistic sysDescr example: unlike "procurve"/
# "edgeswitch", "cisco" alone is not switch-specific text (Cisco also
# makes phones, APs, and firewalls) and VoiceVendorRule does not consume
# sysDescr for its own phone identification, so a bare substring match
# here could misclassify a Cisco device of another type before a more
# specific rule ever sees it. The existing vendor-field "cisco" check
# below carries the same ambiguity but is pre-existing, evidence-accepted
# behavior; RULE-004 does not extend that same risk into a second field.
SWITCH_IDENTIFIER_KEYWORDS = {"procurve", "edgeswitch"}


class SwitchVendorRule(ClassificationRule):
    """Match vendors and product identifiers that indicate a network switch."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for switch vendor/identifier matching evidence."""
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

        matched_identifier = first_matching_identifier(
            device.services,
            SWITCH_IDENTIFIER_KEYWORDS,
            snmp_sys_descr=device.snmp_sys_descr,
        )
        if matched_identifier is not None:
            label, value = matched_identifier
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Detected {label} {value!r} matched known switch identifier.",
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
