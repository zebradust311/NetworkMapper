from __future__ import annotations

from networkmapper.core.models import Device, DeviceType


class DeviceClassifier:
    """
    Applies deterministic rules to classify discovered devices.

    The classifier intentionally uses simple, explainable heuristics.
    Additional discovery sources (SNMP, LLDP, SSH, etc.) may improve
    classification accuracy over time.
    """

    def classify(self, device: Device) -> Device:
        """Inspect a device and assign a device type when a rule matches."""
        vendor = (device.vendor or "").lower()
        hostname = (device.hostname or "").lower()

        if "cisco" in vendor:
            device.device_type = DeviceType.SWITCH
        elif "brother" in vendor or "canon" in vendor or "hewlett packard" in vendor or "hp" in vendor:
            device.device_type = DeviceType.PRINTER
        elif "dell" in vendor:
            device.device_type = DeviceType.WORKSTATION
        elif "dc" in hostname:
            device.device_type = DeviceType.SERVER
        elif "vsh" in hostname:
            device.device_type = DeviceType.HYPERVISOR
        elif "cam" in hostname:
            device.device_type = DeviceType.SERVER
        else:
            device.device_type = DeviceType.UNKNOWN

        return device
