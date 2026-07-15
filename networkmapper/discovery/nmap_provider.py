from __future__ import annotations

import nmap

from networkmapper.core.models import Device
from networkmapper.discovery.provider import DiscoveryProvider


class NmapProvider(DiscoveryProvider):
    """Discover network hosts using an Nmap ping scan."""

    def __init__(self, subnet_cidr: str) -> None:
        """Initialize the provider for a specific subnet CIDR."""
        self._subnet_cidr = subnet_cidr
        self._scanner = nmap.PortScanner()

    def discover(self) -> list[Device]:
        """Run an Nmap ping scan and return discovered devices."""

        scan_result = self._scanner.scan(
            hosts=self._subnet_cidr,
            arguments="-sn",
        )

        devices: list[Device] = []

        for ip_address, host_data in scan_result.get("scan", {}).items():
            device = Device(
                ip_address=ip_address,
                hostname=self._extract_hostname(host_data),
                mac_address=self._extract_mac_address(host_data),
                vendor=self._extract_vendor(host_data),
                discovery_sources=["nmap"],
            )

            devices.append(device)

        return devices

    def _extract_hostname(self, host_data: dict) -> str | None:
        """Extract the primary hostname from Nmap host data when available."""

        hostnames = host_data.get("hostnames", [])

        for entry in hostnames:
            name = entry.get("name")
            if name:
                return name

        return None

    def _extract_mac_address(self, host_data: dict) -> str | None:
        """Extract the MAC address from Nmap host data when available."""

        return host_data.get("addresses", {}).get("mac")

    def _extract_vendor(self, host_data: dict) -> str | None:
        """Extract the vendor from Nmap host data when available."""

        vendors = host_data.get("vendor", {})

        if vendors:
            return next(iter(vendors.values()))

        return None