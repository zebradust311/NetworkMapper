from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import (
    first_matching_identifier,
    normalize_hostname,
    normalize_vendor,
)
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


# RULE-003: BENCH-002 directly observed a Netgear ReadyNAS device (the
# synthetic "netgear-nas-01" host) whose HTTP Authentication Realm
# evidence ("NETGEAR ReadyNAS", read from the http-auth NSE script
# already run against an already-scanned port under STANDARD/DEEP)
# unambiguously identifies it as network-attached storage, but the
# device stayed UNKNOWN across all three scan profiles because no rule
# consumed that evidence. "ReadyNAS" is Netgear's dedicated NAS product
# line name -- a specific, brand-committed identifier, not a generic
# word -- so, exactly like RULE-002's "procurve"/"edgeswitch" identifier
# keywords, it is treated as an independent match trigger on its own,
# consistent with "strong evidence outweighs weak evidence."
#
# DeviceType has no dedicated NAS/storage category; SERVER is the
# closest existing fit (a NAS is, functionally, a dedicated file/storage
# server), and RULE-003 does not expand the shared DeviceType model for
# one BENCH-002-observed device family.
#
# Deliberately narrow: this is the one product-line keyword directly
# tied to the one corroborated case BENCH-002 found. A bare vendor
# match ("netgear" alone) is deliberately NOT used as an independent
# trigger, and never will be added as one -- Netgear also makes
# routers, switches, and access points, so the vendor string alone is
# exactly the "single weak indicator" RULE-003 warns against relying
# on. Vendor and hostname are used only as corroboration text once the
# identifier itself has already matched (below), never as an
# alternative trigger.
#
# RULE-004: also checked against SNMP `sysDescr` (via `first_matching_
# identifier`'s optional `snmp_sys_descr` parameter) -- a ReadyNAS
# device's own SNMP self-description plausibly names the same product
# line its HTTP evidence already does; this is the same identifier
# evidence BENCH-002 corroborated, just from a second source.
NETWORK_APPLIANCE_IDENTIFIER_KEYWORDS = {"readynas"}

NETWORK_APPLIANCE_VENDOR_KEYWORDS = {"netgear"}
NETWORK_APPLIANCE_HOSTNAME_HINTS = ("nas",)


class NetworkApplianceRule(ClassificationRule):
    """Match dedicated NAS/network-appliance identity evidence as SERVER.

    Named for the broader "web-manageable network appliance" evidence
    family RULE-003 was chartered to investigate, not just NAS -- but,
    per RULE-002's naming lesson (don't claim scope the keyword lists
    don't actually cover yet), only NAS identifiers are populated today
    because that is the only case BENCH-002 produced corroborated
    evidence for. Future evidence-backed appliance families should
    extend this rule rather than spawning a new one, per RULE-003's
    "prefer extending existing rules" principle.
    """

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for NAS/network-appliance identifier matching evidence."""
        matched_identifier = first_matching_identifier(
            device.services,
            NETWORK_APPLIANCE_IDENTIFIER_KEYWORDS,
            snmp_sys_descr=device.snmp_sys_descr,
        )

        if matched_identifier is None:
            return RuleResult(
                matched=False,
                confidence_contribution=0,
                reason="No known NAS/network appliance identifier evidence was detected.",
                suggested_device_type=None,
            )

        label, value = matched_identifier
        reason = f"Detected {label} {value!r} matched known NAS/network appliance identifier."

        raw_vendor = device.vendor
        vendor = normalize_vendor(raw_vendor, strip=True)
        if vendor and any(keyword in vendor for keyword in NETWORK_APPLIANCE_VENDOR_KEYWORDS):
            reason += f" Vendor {raw_vendor!r} corroborates known NAS/network appliance vendor."

        raw_hostname = device.hostname
        hostname = normalize_hostname(raw_hostname, strip=True)
        if hostname and any(hint in hostname for hint in NETWORK_APPLIANCE_HOSTNAME_HINTS):
            reason += f" Hostname {raw_hostname!r} corroborates known NAS naming convention."

        return RuleResult(
            matched=True,
            confidence_contribution=0,
            reason=reason,
            suggested_device_type=DeviceType.SERVER,
        )
