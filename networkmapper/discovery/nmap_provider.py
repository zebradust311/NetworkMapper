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

# FEAT-003F/FEAT-003G: narrowly-scoped NSE scripts, each targeting ports
# already in CLASSIFICATION_PORTS with data already exchanged during the
# existing -sV probe, TLS handshake, or a single unauthenticated HTTP
# request. http-title, ssl-cert, and http-auth run against any HTTP/HTTPS
# port already being scanned; vmware-version's own portrule limits it to
# ports -sV already identifies as VMware-related, so no per-host gating
# is needed here.
STANDARD_ENRICHMENT_SCRIPTS = ["http-title", "ssl-cert", "vmware-version", "http-auth"]


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
        """Return the curated service-detection arguments for STANDARD enrichment.

        The NSE scripts are deliberately narrow (FEAT-003F/FEAT-003G): each
        reuses data already exchanged during the -sV probe, handshake, or a
        single unauthenticated request on a port already in
        CLASSIFICATION_PORTS, adds no new scan target, and matches
        ADR-009's per-service evidence model directly.
        """
        classification_ports = ",".join(str(port) for port in CLASSIFICATION_PORTS)
        scripts = ",".join(STANDARD_ENRICHMENT_SCRIPTS)
        return f"-Pn -sV --version-light --script {scripts} -p {classification_ports}"

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

    def _extract_http_auth_realm(self, http_auth_output: str | None) -> str | None:
        """Extract the authentication realm from http-auth NSE script output.

        http-auth's output isn't a fixed "Label: value" line like ssl-cert's
        (FEAT-003F's `_extract_cert_field` pattern) — it reports the raw
        challenge line (e.g. "Basic realm=NETGEAR R7000"), so this searches
        for the "realm=" marker rather than a line prefix.
        """
        if not http_auth_output:
            return None

        for line in http_auth_output.splitlines():
            stripped = line.strip()
            realm_index = stripped.lower().find("realm=")
            if realm_index == -1:
                continue

            value = stripped[realm_index + len("realm="):].strip().strip('"')
            return value or None

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

                scripts = service_data.get("script", {})

                services.append(
                    ServiceEvidence(
                        port=int(port),
                        protocol=protocol,
                        service=(service_data.get("name") or "").strip() or None,
                        product=(service_data.get("product") or "").strip() or None,
                        version=self._extract_version(service_data, scripts),
                        http_title=self._clean_script_output(scripts.get("http-title")),
                        tls_subject=self._extract_cert_field(scripts.get("ssl-cert"), "Subject"),
                        tls_issuer=self._extract_cert_field(scripts.get("ssl-cert"), "Issuer"),
                        http_auth_realm=self._extract_http_auth_realm(scripts.get("http-auth")),
                    )
                )

        return sorted(services, key=lambda entry: (entry.port, entry.protocol))

    def _extract_version(self, service_data: dict, scripts: dict) -> str | None:
        """Return the product version for a port, preferring vmware-version's
        script output over -sV's own guess when both are available, since
        vmware-version queries the ESXi/vCenter API directly rather than
        inferring version from a generic service banner."""
        vmware_version = self._clean_script_output(scripts.get("vmware-version"))
        if vmware_version:
            return vmware_version

        return (service_data.get("version") or "").strip() or None

    def _clean_script_output(self, raw_output: str | None) -> str | None:
        """Collapse multi-line NSE script output into one cleaned string."""
        if not raw_output:
            return None

        cleaned = " ".join(raw_output.strip().splitlines()).strip()
        return cleaned or None

    def _extract_cert_field(self, ssl_cert_output: str | None, field_label: str) -> str | None:
        """Extract a labeled field (e.g. "Subject") from ssl-cert NSE script output."""
        if not ssl_cert_output:
            return None

        prefix = f"{field_label}:"
        for line in ssl_cert_output.splitlines():
            stripped = line.strip()
            if stripped.startswith(prefix):
                value = stripped[len(prefix):].strip()
                return value or None

        return None