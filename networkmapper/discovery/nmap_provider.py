from __future__ import annotations

import nmap

from networkmapper.core.models import Device
from networkmapper.discovery.provider import DiscoveryProvider
from networkmapper.discovery.scan_profile import ScanProfile


class NmapProvider(DiscoveryProvider):
    """Discover network hosts using an Nmap ping scan."""

    def __init__(
        self,
        subnet_cidr: str,
        scan_profile: ScanProfile = ScanProfile.FAST,
    ) -> None:
        """Initialize the provider for a specific subnet CIDR and profile."""
        self._subnet_cidr = subnet_cidr
        self._scan_profile = scan_profile
        self._scanner = nmap.PortScanner()

    def discover(self) -> list[Device]:
        """Run an Nmap scan based on the selected profile and return devices."""

        scan_result = self._scanner.scan(
            hosts=self._subnet_cidr,
            arguments=self._scan_arguments(),
        )

        devices: list[Device] = []

        for ip_address, host_data in scan_result.get("scan", {}).items():
            device = Device(
                ip_address=ip_address,
                hostname=self._extract_hostname(host_data),
                mac_address=self._extract_mac_address(host_data),
                vendor=self._extract_vendor(host_data),
                open_ports=self._extract_open_ports(host_data),
                detected_services=self._extract_detected_services(host_data),
                discovery_sources=["nmap"],
            )

            devices.append(device)

        return devices

    def _scan_arguments(self) -> str:
        """Translate the configured scan profile to Nmap command arguments."""
        profile_arguments = {
            ScanProfile.FAST: "-sn",
            ScanProfile.STANDARD: "-sV",
            ScanProfile.DEEP: "-sn",
        }

        return profile_arguments[self._scan_profile]

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

    def _extract_open_ports(self, host_data: dict) -> list[int]:
        """Extract open port numbers from Nmap host data."""
        open_ports: set[int] = set()

        for protocol in ("tcp", "udp"):
            protocol_data = host_data.get(protocol, {})
            for port, service_data in protocol_data.items():
                if service_data.get("state") == "open":
                    open_ports.add(int(port))

        return sorted(open_ports)

    def _extract_detected_services(self, host_data: dict) -> list[str]:
        """Extract detected service names from Nmap host data."""
        detected_services: set[str] = set()

        for protocol in ("tcp", "udp"):
            protocol_data = host_data.get(protocol, {})
            for service_data in protocol_data.values():
                if service_data.get("state") != "open":
                    continue

                service_name = (service_data.get("name") or "").strip()
                if service_name:
                    detected_services.add(service_name)

        return sorted(detected_services)