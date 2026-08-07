from __future__ import annotations

import nmap

from networkmapper.core.models import Device, ServiceEvidence
from networkmapper.discovery.provider import DiscoveryProvider
from networkmapper.discovery.run_diagnostics import (
    HostDiagnostics,
    RunDiagnostics,
    ScanPhase,
    diagnose_host,
)
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

# FEAT-003F/FEAT-003G/FEAT-003I: narrowly-scoped NSE scripts, each
# targeting ports already in CLASSIFICATION_PORTS with data already
# exchanged during the existing -sV probe, TLS handshake, or a single
# unauthenticated request. http-title, ssl-cert, and http-auth run
# against any HTTP/HTTPS port already being scanned; vmware-version's
# own portrule limits it to ports -sV already identifies as
# VMware-related; rdp-ntlm-info targets port 3389 (already scanned) and,
# like http-auth, discloses information during an incomplete
# authentication handshake without completing a login — no credentials
# are used and no authentication succeeds.
STANDARD_ENRICHMENT_SCRIPTS = ["http-title", "ssl-cert", "vmware-version", "http-auth", "rdp-ntlm-info"]

# FEAT-003H: smb-os-discovery and smb-security-mode are "hostrule" NSE
# scripts — they negotiate a session against the SMB port already in
# CLASSIFICATION_PORTS (445) but report their findings once per host
# (Nmap's "Host script results"), not per port, because the facts they
# reveal (OS, computer name, domain, signing policy) describe the host
# itself rather than any specific service. python-nmap surfaces this as
# host_data["hostscript"], separate from the per-port "script" dict used
# by http-title/ssl-cert/http-auth/vmware-version.
STANDARD_HOST_ENRICHMENT_SCRIPTS = ["smb-os-discovery", "smb-security-mode"]


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
        self.run_diagnostics: RunDiagnostics | None = None

    def discover(self) -> list[Device]:
        """Run an Nmap scan based on the selected profile and return devices."""

        if self._scan_profile == ScanProfile.STANDARD:
            return self._discover_with_standard_enrichment()

        return self._discover_single_pass()

    def _discover_single_pass(self) -> list[Device]:
        """Run a single scan and build device objects from scan results."""

        arguments = self._scan_arguments()
        scan_result = self._scanner.scan(
            hosts=self._subnet_cidr,
            arguments=arguments,
        )

        devices: list[Device] = []

        for ip_address, host_data in scan_result.get("scan", {}).items():
            devices.append(self._build_device(ip_address, host_data))

        self.run_diagnostics = RunDiagnostics(
            scan_profile=self._scan_profile,
            hosts_discovered=len(devices),
            enrichment_enabled=False,
            enrichment_arguments=None,
            phases=[
                ScanPhase(
                    name="Host Discovery",
                    arguments=arguments,
                    elapsed_seconds=self._extract_elapsed_seconds(scan_result),
                )
            ],
        )

        return devices

    def _discover_with_standard_enrichment(self) -> list[Device]:
        """Run host discovery first, then merge enrichment evidence by IP."""
        discovery_phase = ScanPhase(name="Host Discovery", arguments="-sn")
        discovery_result = self._scanner.scan(
            hosts=self._subnet_cidr,
            arguments=discovery_phase.arguments,
        )
        discovery_phase.elapsed_seconds = self._extract_elapsed_seconds(discovery_result)

        devices_by_ip: dict[str, Device] = {}

        for ip_address, host_data in discovery_result.get("scan", {}).items():
            devices_by_ip[ip_address] = self._build_device(ip_address, host_data)

        enrichment_arguments = self._standard_enrichment_arguments()

        if not devices_by_ip:
            self.run_diagnostics = RunDiagnostics(
                scan_profile=self._scan_profile,
                hosts_discovered=0,
                enrichment_enabled=True,
                enrichment_arguments=enrichment_arguments,
                phases=[discovery_phase],
            )
            return []

        enrichment_hosts = " ".join(devices_by_ip.keys())

        enrichment_result = self._scanner.scan(
            hosts=enrichment_hosts,
            arguments=enrichment_arguments,
        )
        enrichment_phase = ScanPhase(
            name="Service Enrichment",
            arguments=enrichment_arguments,
            elapsed_seconds=self._extract_elapsed_seconds(enrichment_result),
        )

        enriched_hosts = enrichment_result.get("scan", {})
        host_diagnostics: dict[str, HostDiagnostics] = {}

        for ip_address, device in devices_by_ip.items():
            host_data = enriched_hosts.get(ip_address, {})
            device.services = self._extract_services(host_data)

            # FEAT-003I: smb-os-discovery and rdp-ntlm-info can both
            # populate operating_system/computer_name/domain for the same
            # device (ARCH-003 Section 2.2 flagged this precedence
            # question; FEAT-003H deferred the decision here). SMB wins,
            # decided per field rather than per source (a host whose SMB
            # output only yields one of the three fields still takes the
            # other two from RDP rather than leaving them empty). SMB is
            # preferred wherever both are present because smb-os-discovery
            # reports a full OS caption (e.g. "Windows Server 2019
            # Standard 17763") while rdp-ntlm-info's Product_Version is a
            # bare build number (e.g. "10.0.14393") with no edition/vendor
            # text — strictly less informative for a human reading the
            # report or for keyword-based classification corroboration
            # (see ServerHostnameRule's SERVER_OPERATING_SYSTEM_KEYWORDS,
            # which a bare build number will never match). RDP only fills
            # in fields SMB left empty, which is exactly the scenario
            # ARCH-003 identified as RDP's value: SMB firewalled or
            # disabled while RDP remains reachable.
            smb_identity = self._extract_smb_identity(host_data)
            rdp_identity = self._extract_rdp_identity(host_data)
            device.operating_system = (
                smb_identity["operating_system"] or rdp_identity["operating_system"]
            )
            device.computer_name = smb_identity["computer_name"] or rdp_identity["computer_name"]
            device.domain = smb_identity["domain"] or rdp_identity["domain"]
            device.smb_signing = smb_identity["smb_signing"]

            host_diagnostics[ip_address] = diagnose_host(
                device.services, smb_identity, rdp_identity
            )

        self.run_diagnostics = RunDiagnostics(
            scan_profile=self._scan_profile,
            hosts_discovered=len(devices_by_ip),
            enrichment_enabled=True,
            enrichment_arguments=enrichment_arguments,
            phases=[discovery_phase, enrichment_phase],
            host_diagnostics=host_diagnostics,
        )

        return list(devices_by_ip.values())

    def _extract_elapsed_seconds(self, scan_result: dict) -> float | None:
        """Return a scan phase's reported elapsed time in seconds, if available."""
        elapsed = scan_result.get("nmap", {}).get("scanstats", {}).get("elapsed")
        if elapsed is None:
            return None

        try:
            return float(elapsed)
        except (TypeError, ValueError):
            return None

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
        scripts = ",".join(STANDARD_ENRICHMENT_SCRIPTS + STANDARD_HOST_ENRICHMENT_SCRIPTS)
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
        (see `_extract_labeled_field`) — it reports the raw challenge line
        (e.g. "Basic realm=NETGEAR R7000"), so this searches for the
        "realm=" marker rather than a line prefix.
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
                        tls_subject=self._extract_labeled_field(scripts.get("ssl-cert"), "Subject"),
                        tls_issuer=self._extract_labeled_field(scripts.get("ssl-cert"), "Issuer"),
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

    def _extract_labeled_field(self, script_output: str | None, field_label: str) -> str | None:
        """Extract a labeled field (e.g. "Subject", "Computer name") from
        multi-line NSE script output whose lines follow a "Label: value"
        convention. Originally written for ssl-cert (FEAT-003F); reused for
        smb-os-discovery/smb-security-mode host-script output (FEAT-003H)
        and rdp-ntlm-info port-script output (FEAT-003I) since all follow
        the same convention."""
        if not script_output:
            return None

        prefix = f"{field_label}:"
        for line in script_output.splitlines():
            stripped = line.strip()
            if stripped.startswith(prefix):
                value = stripped[len(prefix):].strip()
                return value or None

        return None

    def _host_script_output(self, host_data: dict, script_id: str) -> str | None:
        """Return the raw output of one host-level ("hostrule") NSE script, if present."""
        for entry in host_data.get("hostscript", []):
            if entry.get("id") == script_id:
                return entry.get("output")

        return None

    def _extract_smb_identity(self, host_data: dict) -> dict[str, str | None]:
        """Extract device-level SMB identity evidence from Nmap host-script results.

        Per ADR-009, evidence describing the host itself (not a specific
        service) belongs on Device rather than ServiceEvidence, even though
        the underlying SMB session is negotiated against port 445.
        """
        os_discovery_output = self._host_script_output(host_data, "smb-os-discovery")
        security_mode_output = self._host_script_output(host_data, "smb-security-mode")

        domain = self._extract_labeled_field(
            os_discovery_output, "Domain name"
        ) or self._extract_labeled_field(os_discovery_output, "Workgroup")

        return {
            "operating_system": self._extract_labeled_field(os_discovery_output, "OS"),
            "computer_name": self._extract_labeled_field(os_discovery_output, "Computer name"),
            "domain": domain,
            "smb_signing": self._extract_labeled_field(security_mode_output, "message_signing"),
        }

    def _extract_rdp_identity(self, host_data: dict) -> dict[str, str | None]:
        """Extract device-level RDP identity evidence from rdp-ntlm-info output.

        Unlike smb-os-discovery/smb-security-mode, rdp-ntlm-info is a
        "portrule" script scoped to port 3389 — its output lives in the
        normal per-port script dict (the same place http-title/ssl-cert
        live), not host_data["hostscript"]. It still produces
        Device-level identity facts (not ServiceEvidence), same as SMB,
        because NetBIOS computer/domain name and OS build describe the
        host rather than the RDP service itself.
        """
        rdp_output = host_data.get("tcp", {}).get(3389, {}).get("script", {}).get("rdp-ntlm-info")

        return {
            "operating_system": self._extract_labeled_field(rdp_output, "Product_Version"),
            "computer_name": self._extract_labeled_field(rdp_output, "NetBIOS_Computer_Name"),
            "domain": self._extract_labeled_field(rdp_output, "NetBIOS_Domain_Name"),
        }