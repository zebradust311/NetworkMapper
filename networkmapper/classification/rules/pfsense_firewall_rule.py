from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import first_matching_identifier
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


# RULE-010: a real production device self-identifies as a Netgate pfSense
# firewall/router via an HTTP title ("Netgate pfSense Plus - Login") and a
# self-signed TLS certificate whose subject/issuer common name begins
# "pfSense-<hex>" with organizationName "Netgate pfSense Plus GUI default
# Self-Signed Certificate" -- "pfsense" appears in both, and does not appear
# anywhere else across the 244-device production dataset (PLAN-RULE-010).
#
# Deliberately does NOT include a bare "netgate" keyword (rejected during
# final implementation review, PLAN-RULE-010 Section 16): "Netgate" is
# manufacturer/product-family identity, not pfSense-specific identity --
# Netgate also manufactures TNSR, a separate, distinct router product line,
# so a bare "netgate" match could not reliably distinguish a pfSense
# appliance from a TNSR one. "pfsense" alone is the approved identifier;
# it is pfSense-software-specific regardless of which Netgate hardware (or
# non-Netgate hardware -- pfSense also runs on self-built and third-party
# appliances) it happens to be running on.
#
# pfSense is treated as FIREWALL, not ROUTER: unlike EdgeRouterRule's
# "ubiquitirouterui" (which contains the literal word "Router", Ubiquiti's
# own self-declaration of function), nothing in this device's retained
# evidence self-declares a routing function, and pfSense's own product
# lineage (a stateful-packet-filter distribution) matches the
# SonicWallFirewallRule precedent -- a firewall-appliance vendor identifier
# -- more closely than the EdgeRouterRule one.
#
# Deliberately no bare vendor tier and no hostname tier: the device's own
# vendor field is a NIC/hardware OEM ("Silicom"), not "Netgate" or
# "pfSense", so a vendor-based trigger is not even available here, and the
# device carries no hostname at all.
PFSENSE_IDENTIFIER_KEYWORDS = {"pfsense"}


class PfSenseFirewallRule(ClassificationRule):
    """Match explicit pfSense firewall identity evidence."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for pfSense firewall identifier matching evidence."""
        matched_identifier = first_matching_identifier(
            device.services,
            PFSENSE_IDENTIFIER_KEYWORDS,
            snmp_sys_descr=device.snmp_sys_descr,
        )

        if matched_identifier is None:
            return RuleResult(
                matched=False,
                confidence_contribution=0,
                reason="No known pfSense firewall identifier evidence was detected.",
                suggested_device_type=None,
            )

        label, value = matched_identifier
        return RuleResult(
            matched=True,
            confidence_contribution=0,
            reason=f"Detected {label} {value!r} matched known pfSense firewall identifier.",
            suggested_device_type=DeviceType.FIREWALL,
        )
