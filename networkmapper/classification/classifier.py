from __future__ import annotations

from networkmapper.core.models import Device, DeviceType


class DeviceClassifier:
    """
    Applies deterministic rules to classify discovered devices.

    The classifier intentionally uses simple, explainable heuristics.
    Additional discovery sources (SNMP, LLDP, SSH, etc.) may improve
    classification accuracy over time.
    """

    def _classify_by_hostname(self, hostname: str) -> DeviceType:
        """Evaluate hostname evidence independently and return the best match.

        Hostname-derived rules are considered first because they provide more
        specific evidence for server and hypervisor devices.
        """
        if "dc" in hostname:
            return DeviceType.SERVER
        if "vsh" in hostname:
            return DeviceType.HYPERVISOR
        if "cam" in hostname:
            return DeviceType.SERVER
        return DeviceType.UNKNOWN

    def _classify_by_vendor(self, vendor: str) -> DeviceType:
        """Evaluate vendor evidence independently and return the best match.

        Vendor rules are used as a fallback when hostname evidence is missing or
        inconclusive.
        """
        if "cisco" in vendor:
            return DeviceType.SWITCH
        if any(
            keyword in vendor
            for keyword in ("brother", "canon", "hewlett packard", "hp")
        ):
            return DeviceType.PRINTER
        if "dell" in vendor:
            return DeviceType.WORKSTATION
        return DeviceType.UNKNOWN

    def classify(self, device: Device) -> Device:
        """Inspect a device and assign a device type when a rule matches."""
        vendor = (device.vendor or "").lower()
        hostname = (device.hostname or "").lower()

        hostname_device_type = self._classify_by_hostname(hostname)
        vendor_device_type = self._classify_by_vendor(vendor)

        if hostname_device_type != DeviceType.UNKNOWN:
            device.device_type = hostname_device_type
        elif vendor_device_type != DeviceType.UNKNOWN:
            device.device_type = vendor_device_type
        else:
            device.device_type = DeviceType.UNKNOWN

        return device
