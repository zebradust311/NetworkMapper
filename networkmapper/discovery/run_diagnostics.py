from __future__ import annotations

from dataclasses import dataclass, field

from networkmapper.discovery.scan_profile import ScanProfile

# OBS-001: human-readable explanations of what each scan profile actually
# does today, so an operator can see profile behavior without reading
# NmapProvider. DEEP's message reflects DISC-001's finding that it is
# currently non-differentiated from FAST rather than describing aspirational
# behavior.
PROFILE_MESSAGES: dict[ScanProfile, str] = {
    ScanProfile.FAST: (
        "FAST profile:\n"
        "Host discovery only.\n"
        "Service enrichment disabled by design."
    ),
    ScanProfile.STANDARD: (
        "STANDARD profile:\n"
        "Host discovery, then service enrichment on a curated port set.\n"
        "Enrichment scripts: http-title, ssl-cert, vmware-version, http-auth, "
        "rdp-ntlm-info, smb-os-discovery, smb-security-mode."
    ),
    ScanProfile.DEEP: (
        "DEEP profile:\n"
        "Host discovery, then expanded service enrichment: top 1000 TCP "
        "ports, maximum version-detection intensity, one additional safe "
        "NSE script (sip-methods), and increased retry/timeout patience.\n"
        "Higher runtime and network visibility than STANDARD. Still "
        "unauthenticated — per ARCH-010, intended for a focused scope "
        "(a subnet, a device cluster), not a full enterprise sweep."
    ),
}


def profile_message(scan_profile: ScanProfile) -> str:
    """Return the operator-facing description of what a scan profile does."""
    return PROFILE_MESSAGES[scan_profile]


@dataclass
class ScanPhase:
    """Represents one Nmap invocation within a discovery run.

    Attributes:
        name: A human-readable phase label (e.g. "Host Discovery").
        arguments: The exact Nmap argument string used for this phase.
        elapsed_seconds: The phase's reported scan duration, if Nmap
            returned it. `None` when unavailable (e.g. the phase was
            skipped, or scanstats were absent from the scan result).
    """

    name: str
    arguments: str
    elapsed_seconds: float | None = None


@dataclass
class HostDiagnostics:
    """Represents what STANDARD enrichment did and didn't find for one host.

    Attributes:
        enriched: Whether enrichment produced any evidence at all (service
            evidence, SMB identity, or RDP identity) for this host.
        has_service_evidence: Whether any curated port was observed open.
        has_smb_identity: Whether smb-os-discovery/smb-security-mode
            returned any identity field, evaluated before SMB/RDP merge so
            it reflects SMB specifically rather than the merged result.
        has_rdp_identity: Whether rdp-ntlm-info returned any identity
            field, evaluated before SMB/RDP merge for the same reason.
        has_http_title: Whether any service carried an HTTP title.
        has_tls_certificate: Whether any service carried a TLS subject.
        has_http_auth_realm: Whether any service carried an HTTP auth realm.
        missing_evidence_reasons: Conditions determined directly from this
            host's scan results that explain absent or partial evidence.
    """

    enriched: bool
    has_service_evidence: bool
    has_smb_identity: bool
    has_rdp_identity: bool
    has_http_title: bool
    has_tls_certificate: bool
    has_http_auth_realm: bool
    missing_evidence_reasons: list[str] = field(default_factory=list)


@dataclass
class RunDiagnostics:
    """Represents run-level observability data for one discovery pass.

    Attributes:
        scan_profile: The scan profile selected for this run.
        hosts_discovered: The number of hosts found during host discovery.
        enrichment_enabled: Whether this profile performs service
            enrichment at all.
        enrichment_arguments: The exact enrichment argument string used
            (or that would be used), if enrichment is enabled for this
            profile.
        phases: The Nmap invocations actually executed, in order.
        host_diagnostics: Per-host diagnostics, keyed by IP address. Empty
            when enrichment did not run (profile-disabled or zero hosts
            discovered).
        expanded_capabilities: Human-readable descriptions of what this
            profile does beyond STANDARD's baseline (FEAT-004). Empty for
            FAST/STANDARD; populated for DEEP so an operator can see what
            "expanded" concretely means without reading `NmapProvider`.
    """

    scan_profile: ScanProfile
    hosts_discovered: int
    enrichment_enabled: bool
    enrichment_arguments: str | None = None
    phases: list[ScanPhase] = field(default_factory=list)
    host_diagnostics: dict[str, HostDiagnostics] = field(default_factory=dict)
    expanded_capabilities: list[str] = field(default_factory=list)


def diagnose_host(
    services: list,
    smb_identity: dict[str, str | None],
    rdp_identity: dict[str, str | None],
) -> HostDiagnostics:
    """Derive per-host diagnostics from already-collected enrichment evidence.

    Reasons are limited to conditions directly observable in this host's own
    scan results (which curated ports were open, which service names were
    resolved, which script fields were populated) — no inference about
    causes that scan results can't confirm (e.g. firewalling vs. the
    service simply being absent).
    """
    open_ports = {entry.port for entry in services}
    named_services = any(entry.service for entry in services)
    http_like_services = [
        entry for entry in services if entry.service and "http" in entry.service.lower()
    ]
    tls_like_services = [
        entry
        for entry in services
        if entry.service and ("https" in entry.service.lower() or "ssl" in entry.service.lower())
    ]

    reasons: list[str] = []

    if not open_ports:
        reasons.append("No curated ports open.")
    elif not named_services:
        reasons.append("Open ports detected, but no supported services identified.")

    if 445 not in open_ports:
        reasons.append("SMB unreachable (port 445 not open).")

    if 3389 not in open_ports:
        reasons.append("RDP unreachable (port 3389 not open).")

    if not http_like_services:
        reasons.append("HTTP service not present.")
    elif not any(entry.tls_subject for entry in tls_like_services):
        if tls_like_services:
            reasons.append("TLS certificate not presented.")

    has_smb_identity = any(smb_identity.values())
    has_rdp_identity = any(rdp_identity.values())
    has_service_evidence = bool(services)

    return HostDiagnostics(
        enriched=has_service_evidence or has_smb_identity or has_rdp_identity,
        has_service_evidence=has_service_evidence,
        has_smb_identity=has_smb_identity,
        has_rdp_identity=has_rdp_identity,
        has_http_title=any(entry.http_title for entry in services),
        has_tls_certificate=any(entry.tls_subject for entry in services),
        has_http_auth_realm=any(entry.http_auth_realm for entry in services),
        missing_evidence_reasons=reasons,
    )
