from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.camera_vendor_rule import CameraVendorRule
from networkmapper.classification.rules.dell_workstation_rule import DellWorkstationRule
from networkmapper.classification.rules.edge_router_rule import EdgeRouterRule
from networkmapper.classification.rules.hypervisor_hostname_rule import HypervisorHostnameRule
from networkmapper.classification.rules.network_appliance_rule import NetworkApplianceRule
from networkmapper.classification.rules.printer_vendor_rule import PrinterVendorRule
from networkmapper.classification.rules.server_hostname_rule import ServerHostnameRule
from networkmapper.classification.rules.sonicwall_firewall_rule import SonicWallFirewallRule
from networkmapper.classification.rules.switch_vendor_rule import SwitchVendorRule
from networkmapper.classification.rules.ubiquiti_access_point_rule import UbiquitiAccessPointRule
from networkmapper.classification.rules.voice_vendor_rule import VoiceVendorRule
from networkmapper.classification.rules.windows_server_rule import WindowsServerRule
from networkmapper.classification.rules.windows_workstation_rule import WindowsWorkstationRule
from networkmapper.core.models import Device, DeviceType


class DeviceClassifier:
    """Classify a device using an ordered list of small, composable rules."""

    def __init__(self) -> None:
        """Initialize the classifier with the current rule ordering.

        SwitchVendorRule and VoiceVendorRule run before PrinterVendorRule
        (RULE-002): a switch or phone's explicit product identity or vendor
        is stronger evidence than PrinterVendorRule's bare vendor-keyword
        match, which otherwise intercepts ambiguous vendors shared with
        printers (e.g. HP ProCurve switches, whose "hp" vendor string
        previously matched PrinterVendorRule before switch-specific
        evidence was ever evaluated). VoiceVendorRule stays ahead of
        SwitchVendorRule so a Cisco IP Phone's more specific vendor match
        continues to win over SwitchVendorRule's bare "cisco" vendor
        substring match.

        NetworkApplianceRule runs immediately after ServerHostnameRule
        (RULE-003): both suggest SERVER, so there is no precedence
        conflict to resolve between them, and grouping them keeps the
        two SERVER-producing rules adjacent. Its identifier keyword
        ("readynas") doesn't overlap with any other rule's vendor or
        identifier keywords, so its exact position among the other,
        differently-typed rules is not safety-relevant.

        CameraVendorRule (RULE-005) runs between SwitchVendorRule and
        PrinterVendorRule. Its vendor keyword ("axis communications") and
        product-identifier keyword ("axis camera station") don't overlap
        with any other rule's vendor or identifier keywords (confirmed
        directly, including against every PrinterVendorRule printer-vendor
        keyword), so — like NetworkApplianceRule above — its exact
        position among the other, differently-typed rules is not
        safety-relevant; it is grouped here only to keep the vendor-based
        rules adjacent.

        WindowsServerRule (RULE-006) runs immediately after CameraVendorRule
        and immediately before PrinterVendorRule — this exact position is
        safety-relevant in both directions, unlike the rules named above:

        It must run after HypervisorHostnameRule: a real Hyper-V host
        (hostname matching the "vsh" convention) can carry the exact
        Windows Server 2022 build (10.0.20348) this rule also treats as
        high-confidence evidence, and must remain HYPERVISOR, not be
        reclassified SERVER. Confirmed against real production evidence
        (three "vsh"-hostname hosts, one on that exact build).

        It must run before PrinterVendorRule and DellWorkstationRule: a
        Dell-vendor or Microsoft-vendor host with explicit Windows Server
        evidence must be claimed here, not by DellWorkstationRule's bare
        "dell" vendor match or PrinterVendorRule's networking tier.
        DellWorkstationRule itself needs no defensive code for this — its
        bare-vendor match can only ever be reached by a device this rule
        has already declined, so ordering alone resolves the precedence.
        (PrinterVendorRule additionally excludes Microsoft-branded
        printer-networking evidence on its own, since one confirmed case
        has no operating_system evidence for this rule to match at all —
        see PrinterVendorRule's own docstring.)

        WindowsWorkstationRule (RULE-007) runs last, after
        DellWorkstationRule — unlike WindowsServerRule above, this
        position carries no "must precede X" requirement in either
        direction, because this rule corrects no existing rule's
        over-broad match; it only ever assigns a type to a device every
        other rule has already declined (PLAN-RULE-007 Section 13/14).
        It cannot preempt ServerHostnameRule, HypervisorHostnameRule,
        WindowsServerRule, PrinterVendorRule, or DellWorkstationRule
        simply by virtue of running after all of them. Its one
        confirmed overlap — a Dell-vendor device whose operating_system
        also carries an explicit client-edition caption — is resolved
        by DellWorkstationRule winning first, exactly as it does today;
        DellWorkstationRule needs no defensive code for this, the same
        ordering-only precedent WindowsServerRule already established
        for its own overlap with DellWorkstationRule.

        EdgeRouterRule (RULE-008) runs immediately after
        UbiquitiAccessPointRule and immediately before
        SonicWallFirewallRule. This exact position is not safety-relevant
        in either direction — confirmed directly against real production
        evidence, every EdgeOS device fails every UbiquitiAccessPointRule
        check today (none carries an AP-shaped hostname or the UniFi
        guest-portal HTTP title UbiquitiAccessPointRule looks for), and
        EdgeRouterRule's own identifier keywords ("edgeos",
        "ubiquitirouterui") share no overlap with any other rule's vendor
        or identifier keywords, including SonicWallFirewallRule's
        "sonicwall" and SwitchVendorRule's "procurve"/"edgeswitch"/
        "tp-link switch". It is placed here only to keep the two
        vendor-scoped Ubiquiti rules adjacent, the same "grouped, not
        order-critical" precedent NetworkApplianceRule and
        CameraVendorRule already established above. Like
        WindowsServerRule, EdgeRouterRule deliberately has no bare-vendor
        ("ubiquiti") match tier and no hostname tier, so it can never
        preempt UbiquitiAccessPointRule's own hostname-based matches even
        if a future device happened to carry both kinds of evidence.

        SwitchVendorRule's own position is unchanged by RULE-008 — only
        its identifier keyword set gained "tp-link switch", the same
        product-identifier tier "procurve"/"edgeswitch" already use, so
        no new ordering question is introduced by that change.
        """
        self._rules: list[ClassificationRule] = [
            ServerHostnameRule(),
            NetworkApplianceRule(),
            HypervisorHostnameRule(),
            UbiquitiAccessPointRule(),
            EdgeRouterRule(),
            SonicWallFirewallRule(),
            VoiceVendorRule(),
            SwitchVendorRule(),
            CameraVendorRule(),
            WindowsServerRule(),
            PrinterVendorRule(),
            DellWorkstationRule(),
            WindowsWorkstationRule(),
        ]
        self._last_rule_results: list[RuleResult] = []

    def classify(self, device: Device) -> Device:
        """Classify a device by applying the ordered rule list.

        Args:
            device: The discovered device to classify.

        Returns:
            The same device instance with its normalized device type assigned.
        """
        self._last_rule_results = []

        for rule in self._rules:
            rule_result = rule.classify(device)
            self._last_rule_results.append(rule_result)

            if rule_result.matched and rule_result.suggested_device_type is not None:
                device.device_type = rule_result.suggested_device_type
                return device

        device.device_type = DeviceType.UNKNOWN
        return device

    def get_last_rule_results(self) -> tuple[RuleResult, ...]:
        """Return immutable evidence from the most recent classification."""
        return tuple(self._last_rule_results)
