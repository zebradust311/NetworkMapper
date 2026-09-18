from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import normalize_operating_system
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


# "enterprise" and "professional" are the two client-edition captions
# actually observed in real production evidence (PLAN-RULE-007 Section
# 6/12); neither is a Windows Server edition name, and both are safe as
# bare words. Deliberately excludes bare "pro" -- a three-letter
# substring is exactly the collision risk RULE-005 already found and
# fixed for PrinterVendorRule's bare "hp" keyword.
#
# "windows 10 home"/"windows 11 home" (PLAN-RULE-007 Section 21) were
# added prospectively for MSP fleets, not in response to any device in
# this project's captured evidence -- none exists. Version-qualified
# rather than bare "home" or "windows home", specifically because
# "Windows Home Server" is a real, shipped Microsoft product (2007-2013)
# a bare "home" substring would also match; "windows 10 home"/
# "windows 11 home" are disjoint from "windows home server" by word
# order while still matching real OEM/regional Home variants (e.g.
# "Windows 10 Home Single Language").
WINDOWS_CLIENT_EDITION_KEYWORDS = (
    "enterprise",
    "professional",
    "windows 10 home",
    "windows 11 home",
)


class WindowsWorkstationRule(ClassificationRule):
    """Match an explicit Windows client-edition caption in `operating_system`.

    Reads only `device.operating_system` -- the same single-field
    discipline WindowsServerRule (RULE-006) already established for the
    server side. This is fallback-only, additive evidence: it never
    reads vendor, hostname, services, or any bare/ambiguous build
    number, and it never falls back to WORKSTATION for generic
    Windows-flavored evidence that lacks an explicit client edition
    name. "enterprise"/"professional" were confirmed against real
    production evidence (PLAN-RULE-007's original investigation: exactly
    two real devices, zero Windows Server/Hyper-V/domain-controller
    false positives); "windows 10 home"/"windows 11 home" were added
    prospectively for MSP fleets by later architect-approved amendment
    (PLAN-RULE-007 Section 21), with no corresponding device observed in
    this project's evidence to date -- see `WINDOWS_CLIENT_EDITION_KEYWORDS`
    above for why each keyword takes the exact form it does.
    """

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for explicit Windows client-edition evidence."""
        raw_operating_system = device.operating_system
        operating_system = normalize_operating_system(raw_operating_system)

        if any(keyword in operating_system for keyword in WINDOWS_CLIENT_EDITION_KEYWORDS):
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=(
                    f"Operating system {raw_operating_system!r} matched known "
                    "Windows client edition caption."
                ),
                suggested_device_type=DeviceType.WORKSTATION,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=(
                f"Operating system {raw_operating_system!r} did not match known "
                "Windows client edition evidence."
            ),
            suggested_device_type=None,
        )
