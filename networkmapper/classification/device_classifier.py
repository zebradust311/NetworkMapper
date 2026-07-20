from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.rules.cisco_switch_rule import CiscoSwitchRule
from networkmapper.classification.rules.dell_workstation_rule import DellWorkstationRule
from networkmapper.classification.rules.hypervisor_hostname_rule import HypervisorHostnameRule
from networkmapper.classification.rules.printer_vendor_rule import PrinterVendorRule
from networkmapper.classification.rules.server_hostname_rule import ServerHostnameRule
from networkmapper.classification.rules.ubiquiti_access_point_rule import UbiquitiAccessPointRule
from networkmapper.core.models import Device, DeviceType


class DeviceClassifier:
    """Classify a device using an ordered list of small, composable rules."""

    def __init__(self) -> None:
        """Initialize the classifier with the current rule ordering."""
        self._rules: list[ClassificationRule] = [
            ServerHostnameRule(),
            HypervisorHostnameRule(),
            UbiquitiAccessPointRule(),
            PrinterVendorRule(),
            CiscoSwitchRule(),
            DellWorkstationRule(),
        ]

    def classify(self, device: Device) -> Device:
        """Classify a device by applying the ordered rule list.

        Args:
            device: The discovered device to classify.

        Returns:
            The same device instance with its normalized device type assigned.
        """
        for rule in self._rules:
            result = rule.classify(device)
            if result is not None:
                device.device_type = result
                return device

        device.device_type = DeviceType.UNKNOWN
        return device
