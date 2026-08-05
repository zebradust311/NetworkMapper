from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import (
    normalize_hostname,
    normalize_operating_system,
)
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


SERVER_HOSTNAME_KEYWORDS = (
    "srv",
    "server",
)

# smb-os-discovery (FEAT-003H) reports a Windows Server SKU's OS caption
# verbatim (e.g. "Windows Server 2019 Standard 17763") via unauthenticated
# SMB protocol negotiation. Unlike PrinterVendorRule/SonicWallFirewallRule's
# identifier tier (FEAT-003D/FEAT-003G), "runs Windows Server" is NOT
# treated as an independent match trigger here: many non-SERVER device
# types (Hyper-V hosts, domain controllers acting as hypervisor hosts,
# some appliances) also run Windows Server, and ServerHostnameRule runs
# first in DeviceClassifier's ordering — an independent OS-based trigger
# was tried during implementation and directly misclassified the
# `enterprise` benchmark's Hyper-V host as SERVER before HypervisorHostnameRule
# ever got a chance to evaluate it. Corroboration-only avoids this: it can
# only strengthen a hostname match that already occurred, never preempt a
# more specific rule. No dedicated Domain Controller device type exists in
# DeviceType, and smb-os-discovery's unauthenticated output does not
# reliably distinguish a domain controller from a member server, so this
# deliberately targets the existing SERVER type rather than inventing a
# new one.
SERVER_OPERATING_SYSTEM_KEYWORDS = {"server"}


class ServerHostnameRule(ClassificationRule):
    """Match hostnames that indicate a server, such as those containing 'dc' or 'cam'."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for server hostname matching evidence."""
        raw_hostname = device.hostname
        hostname = normalize_hostname(raw_hostname, strip=False)

        raw_operating_system = device.operating_system
        operating_system = normalize_operating_system(raw_operating_system)
        matched_operating_system = (
            raw_operating_system
            if operating_system
            and any(keyword in operating_system for keyword in SERVER_OPERATING_SYSTEM_KEYWORDS)
            else None
        )

        if "dc" in hostname or "cam" in hostname:
            reason = f"Hostname {raw_hostname!r} matched known server naming convention."
            if matched_operating_system is not None:
                reason += (
                    f" Detected operating system {matched_operating_system!r} "
                    "corroborates known server evidence."
                )
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=reason,
                suggested_device_type=DeviceType.SERVER,
            )

        if any(keyword in hostname for keyword in SERVER_HOSTNAME_KEYWORDS):
            reason = f"Hostname {raw_hostname!r} matched known server naming pattern."
            if matched_operating_system is not None:
                reason += (
                    f" Detected operating system {matched_operating_system!r} "
                    "corroborates known server evidence."
                )
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=reason,
                suggested_device_type=DeviceType.SERVER,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=f"Hostname {raw_hostname!r} did not match known server naming patterns.",
            suggested_device_type=None,
        )
