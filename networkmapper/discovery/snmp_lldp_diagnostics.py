from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SnmpLldpHostDiagnostics:
    """Represents what an SNMP LLDP neighbor-table walk did and didn't find for one host.

    Attributes:
        responded: Whether the host's LLDP walk completed successfully.
            `True` even when there are zero neighbor rows, or the device
            doesn't implement LLDP-MIB at all (ARCH-023 Section 7) — both
            are legitimate results, not signs of non-response (mirroring
            `SnmpArpTableResult`'s own docstring for its own table).
        entries_returned: The number of `lldpRemTable` rows returned by
            this host, regardless of whether any resolved to a
            `RelationshipObservation`.
        management_addresses_returned: The total number of management
            addresses returned across every row for this host — its own,
            separately-failable walk (ARCH-023 Section 7), tracked
            distinctly from `entries_returned`.
        failure_reason: A short, fixed diagnostic string when the walk did
            not complete, or `None` for a fully successful walk.
            Deliberately never derived from a caught exception's raw
            message — see ARCH-012 Security Considerations.
    """

    responded: bool
    entries_returned: int = 0
    management_addresses_returned: int = 0
    failure_reason: str | None = None


@dataclass
class SnmpLldpRunDiagnostics:
    """Represents run-level observability data for one LLDP-neighbor enrichment pass.

    Attributes:
        hosts_eligible: The number of devices LLDP-neighbor enrichment was
            asked to query (the already-discovered device set at phase
            start).
        hosts_queried: The number of devices actually queried (equal to
            `hosts_eligible` unless the run was interrupted).
        hosts_responded: The number of devices whose LLDP-table walk
            completed successfully (including a walk that returned zero
            rows).
        hosts_timed_out: The number of devices whose walk did not complete
            within the configured timeout/retry budget or otherwise
            failed.
        version: The SNMP protocol version used for this run (e.g.
            "v2c") — never the community string or any other credential
            value.
        host_diagnostics: Per-host diagnostics, keyed by IP address.
    """

    hosts_eligible: int
    hosts_queried: int
    hosts_responded: int
    hosts_timed_out: int
    version: str
    host_diagnostics: dict[str, SnmpLldpHostDiagnostics] = field(default_factory=dict)
