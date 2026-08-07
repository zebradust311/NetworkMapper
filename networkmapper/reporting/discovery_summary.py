from __future__ import annotations

from dataclasses import dataclass

from networkmapper.discovery.run_diagnostics import RunDiagnostics


@dataclass
class DiscoverySummary:
    """Represents aggregate discovery-run statistics generated from
    already-collected per-host diagnostics — no estimation, no fields not
    already present on `HostDiagnostics`.

    Attributes:
        hosts_discovered: The number of hosts found during host discovery.
        hosts_enriched: The number of hosts for which enrichment produced
            any evidence at all.
        hosts_with_service_evidence: The number of hosts with at least one
            open curated port.
        hosts_with_smb_identity: The number of hosts with SMB-sourced
            identity evidence.
        hosts_with_rdp_identity: The number of hosts with RDP-sourced
            identity evidence.
        hosts_with_http_titles: The number of hosts with at least one
            HTTP title observed.
        hosts_with_tls_certificates: The number of hosts with at least one
            TLS certificate subject observed.
        hosts_with_http_auth_realms: The number of hosts with at least one
            HTTP authentication realm observed.
    """

    hosts_discovered: int
    hosts_enriched: int = 0
    hosts_with_service_evidence: int = 0
    hosts_with_smb_identity: int = 0
    hosts_with_rdp_identity: int = 0
    hosts_with_http_titles: int = 0
    hosts_with_tls_certificates: int = 0
    hosts_with_http_auth_realms: int = 0

    @classmethod
    def from_run_diagnostics(cls, run_diagnostics: RunDiagnostics) -> DiscoverySummary:
        """Aggregate per-host diagnostics from one discovery run into summary counts.

        Args:
            run_diagnostics: The run-level diagnostics produced by discovery,
                including per-host diagnostics when enrichment ran.

        Returns:
            A summary of discovery-run statistics. All enrichment-derived
            counts are zero when `run_diagnostics.host_diagnostics` is
            empty (enrichment disabled by profile, or zero hosts found).
        """
        host_diagnostics = run_diagnostics.host_diagnostics.values()

        return cls(
            hosts_discovered=run_diagnostics.hosts_discovered,
            hosts_enriched=sum(1 for host in host_diagnostics if host.enriched),
            hosts_with_service_evidence=sum(
                1 for host in host_diagnostics if host.has_service_evidence
            ),
            hosts_with_smb_identity=sum(
                1 for host in host_diagnostics if host.has_smb_identity
            ),
            hosts_with_rdp_identity=sum(
                1 for host in host_diagnostics if host.has_rdp_identity
            ),
            hosts_with_http_titles=sum(
                1 for host in host_diagnostics if host.has_http_title
            ),
            hosts_with_tls_certificates=sum(
                1 for host in host_diagnostics if host.has_tls_certificate
            ),
            hosts_with_http_auth_realms=sum(
                1 for host in host_diagnostics if host.has_http_auth_realm
            ),
        )
