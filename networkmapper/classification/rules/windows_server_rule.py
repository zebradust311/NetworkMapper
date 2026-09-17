from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import normalize_operating_system
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


WINDOWS_SERVER_CAPTION_KEYWORD = "windows server"

# Windows Server 2022's build number. Unlike 6.3.9600 (Windows 8.1 /
# Server 2012 R2) or 10.0.26100 (Windows 11 24H2 / Server 2025), this
# build is never shared with any Windows client release, so it is the
# one raw build number this rule treats as high-confidence evidence on
# its own -- an exact value match, never a substring or range check, and
# never generalized to "nearby" builds (PLAN-RULE-006 Section 1.3).
WINDOWS_SERVER_2022_BUILD = "10.0.20348"


class WindowsServerRule(ClassificationRule):
    """Match high-confidence Windows Server evidence from SMB/RDP OS negotiation.

    Reads only `device.operating_system` -- populated exclusively by
    SMB/RDP-based OS negotiation (never a generic OS guess), so no
    additional port/service corroboration is required. Two independent
    branches, both producing SERVER: an explicit "Windows Server" caption
    already fully resolved by smb-os-discovery, or the exact Windows
    Server 2022 build number. Deliberately does not fall back to
    WORKSTATION for any other Windows-flavored evidence, and never reads
    `product` or any other field -- a ranged/ambiguous product string
    (e.g. "Windows Server 2008 R2 - 2012") never qualifies, only an
    `operating_system` value smb-os-discovery has already fully resolved.
    """

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for high-confidence Windows Server evidence."""
        raw_operating_system = device.operating_system
        operating_system = normalize_operating_system(raw_operating_system)

        if WINDOWS_SERVER_CAPTION_KEYWORD in operating_system:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=(
                    f"Operating system {raw_operating_system!r} matched known "
                    "Windows Server caption."
                ),
                suggested_device_type=DeviceType.SERVER,
            )

        if operating_system == WINDOWS_SERVER_2022_BUILD:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=(
                    f"Operating system build {raw_operating_system!r} matched the "
                    "unambiguous Windows Server 2022 build number."
                ),
                suggested_device_type=DeviceType.SERVER,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=(
                f"Operating system {raw_operating_system!r} did not match known "
                "high-confidence Windows Server evidence."
            ),
            suggested_device_type=None,
        )
