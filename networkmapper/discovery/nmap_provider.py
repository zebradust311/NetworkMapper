from __future__ import annotations

import nmap

from networkmapper.core.models import Device, ServiceEvidence
from networkmapper.discovery.provider import DiscoveryProvider
from networkmapper.discovery.scan_profile import ScanProfile


# 902/903 are VMware's core ESXi host management ports (vmware-authd
# authentication and the legacy MKS remote-console channel). They are
# present on every ESXi installation, unlike 5988/5989 (CIM/WBEM hardware
# management), which are optional, frequently disabled, and considered
# legacy on modern ESXi versions. 5988/5989 were evaluated for inclusion
# (FEAT-002B) and deliberately excluded: their lower universality doesn't
# justify the added scan surface without a specific classification need.
CLASSIFICATION_PORTS = [
    22,
    53,
    80,
    161,
    443,
    445,
    515,
    631,
    9100,
    3389,
    5060,
    5061,
    8080,
    8443,
    902,
    903,
]


class NmapProvider(DiscoveryProvider):
    """Discover network hosts using profile-driven Nmap scan settings."""

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

        if self._scan_profile == ScanProfile.STANDARD:
            return self._discover_with_standard_enrichment()

        return self._discover_single_pass()

    def _discover_single_pass(self) -> list[Device]:
        """Run a single scan and build device objects from scan results."""

        scan_result = self._scanner.scan(
            hosts=self._subnet_cidr,
            arguments=self._scan_arguments(),
        )

        devices: list[Device] = []

        for ip_address, host_data in scan_result.get("scan", {}).items():
            devices.append(self._build_device(ip_address, host_data))

        return devices

    def _discover_with_standard_enrichment(self) -> list[Device]:
        """Run host discovery first, then merge enrichment evidence by IP."""
        discovery_result = self._scanner.scan(
            hosts=self._subnet_cidr,
            arguments="-sn",
        )

        devices_by_ip: dict[str, Device] = {}

        for ip_address, host_data in discovery_result.get("scan", {}).items():
            devices_by_ip[ip_address] = self._build_device(ip_address, host_data)

        if not devices_by_ip:
            return []

        enrichment_hosts = " ".join(devices_by_ip.keys())
        enrichment_arguments = self._standard_enrichment_arguments()

        enrichment_result = self._scanner.scan(
            hosts=enrichment_hosts,
            arguments=enrichment_arguments,
        )

        enriched_hosts = enrichment_result.get("scan", {})

        for ip_address, host_data in enriched_hosts.items():
            if ip_address not in devices_by_ip:
                continue

            devices_by_ip[ip_address].services = self._extract_services(host_data)

        return list(devices_by_ip.values())

    def _build_device(self, ip_address: str, host_data: dict) -> Device:
        """Build a device instance from host data without enrichment evidence."""
        return Device(
            ip_address=ip_address,
            hostname=self._extract_hostname(host_data),
            mac_address=self._extract_mac_address(host_data),
            vendor=self._extract_vendor(host_data),
            services=[],
            discovery_sources=["nmap"],
        )

    def _scan_arguments(self) -> str:
        """Translate the configured scan profile to Nmap command arguments."""
        profile_arguments = {
            ScanProfile.FAST: "-sn",
            ScanProfile.DEEP: "-sn",
        }

        return profile_arguments[self._scan_profile]

    def _standard_enrichment_arguments(self) -> str:
        """Return the curated service-detection arguments for STANDARD enrichment."""
        classification_ports = ",".join(str(port) for port in CLASSIFICATION_PORTS)
        return f"-Pn -sV --version-light -p {classification_ports}"

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

    def _extract_services(self, host_data: dict) -> list[ServiceEvidence]:
        """Extract correlated per-port service evidence from Nmap host data.

        Per ADR-009, evidence for a port (service name, product, version) is
        kept on one record per port rather than split across independent
        lists, so a specific port and everything observed about it stay
        linked.
        """
        services: list[ServiceEvidence] = []

        for protocol in ("tcp", "udp"):
            protocol_data = host_data.get(protocol, {})
            for port, service_data in protocol_data.items():
                if service_data.get("state") != "open":
                    continue

                services.append(
                    ServiceEvidence(
                        port=int(port),
                        protocol=protocol,
                        service=(service_data.get("name") or "").strip() or None,
                        product=(service_data.get("product") or "").strip() or None,
                        version=(service_data.get("version") or "").strip() or None,
                    )
                )

        return sorted(services, key=lambda entry: (entry.port, entry.protocol))