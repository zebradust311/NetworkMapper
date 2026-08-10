from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.dell_workstation_rule import DellWorkstationRule
from networkmapper.classification.rules.hypervisor_hostname_rule import HypervisorHostnameRule
from networkmapper.classification.rules.printer_vendor_rule import PrinterVendorRule
from networkmapper.classification.rules.server_hostname_rule import ServerHostnameRule
from networkmapper.classification.rules.sonicwall_firewall_rule import SonicWallFirewallRule
from networkmapper.classification.rules.switch_vendor_rule import SwitchVendorRule
from networkmapper.classification.rules.ubiquiti_access_point_rule import UbiquitiAccessPointRule
from networkmapper.classification.rules.voice_vendor_rule import VoiceVendorRule
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
        """
        self._rules: list[ClassificationRule] = [
            ServerHostnameRule(),
            HypervisorHostnameRule(),
            UbiquitiAccessPointRule(),
            SonicWallFirewallRule(),
            VoiceVendorRule(),
            SwitchVendorRule(),
            PrinterVendorRule(),
            DellWorkstationRule(),
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
