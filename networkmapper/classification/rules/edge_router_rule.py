from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import first_matching_identifier
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


# RULE-008: Ubiquiti's EdgeMAX routing line (EdgeRouter/USG) self-identifies
# via its own management UI, surfaced by nmap's http-title and ssl-cert NSE
# scripts (FEAT-003F) as an HTTP title of exactly "EdgeOS" and a self-signed
# TLS certificate whose subject/issuer common name is "UbiquitiRouterUI" --
# Ubiquiti's own name for this exact interface, which contains the word
# "Router" itself. Both are treated as independent identifier-tier triggers,
# consistent with the existing identifier-tier precedent (SwitchVendorRule's
# "procurve"/"edgeswitch", SonicWallFirewallRule's "sonicwall",
# NetworkApplianceRule's "readynas"): a specific, self-branded product
# identifier outweighs a bare vendor match.
#
# Deliberately no bare "ubiquiti" vendor tier and no hostname tier: Ubiquiti
# also makes access points and switches (already handled by
# UbiquitiAccessPointRule and SwitchVendorRule's "edgeswitch" keyword), so
# vendor alone is not router-specific, and no EdgeOS device in the
# production evidence this rule was built from carries a hostname to
# design a hostname signal from.
EDGE_ROUTER_IDENTIFIER_KEYWORDS = {"edgeos", "ubiquitirouterui"}


class EdgeRouterRule(ClassificationRule):
    """Match explicit Ubiquiti EdgeOS router identity evidence."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for EdgeOS router identifier matching evidence."""
        matched_identifier = first_matching_identifier(
            device.services,
            EDGE_ROUTER_IDENTIFIER_KEYWORDS,
            snmp_sys_descr=device.snmp_sys_descr,
        )

        if matched_identifier is None:
            return RuleResult(
                matched=False,
                confidence_contribution=0,
                reason="No known EdgeOS router identifier evidence was detected.",
                suggested_device_type=None,
            )

        label, value = matched_identifier
        return RuleResult(
            matched=True,
            confidence_contribution=0,
            reason=f"Detected {label} {value!r} matched known EdgeOS router identifier.",
            suggested_device_type=DeviceType.ROUTER,
        )
