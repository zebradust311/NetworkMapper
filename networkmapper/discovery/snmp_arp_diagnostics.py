from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SnmpArpHostDiagnostics:
    """Represents what an SNMP ARP-table walk did and didn't find for one host.

    Attributes:
        responded: Whether the host's ARP table walk completed
            successfully. `True` even when the table has zero entries — an
            empty ARP table is a legitimate result for a real, responding
            device, not a sign of non-response (unlike the MIB-2
            system-group query, where zero fields does indicate
            non-response — see `SnmpArpTableResult`'s own docstring).
        entries_returned: The number of ARP-table entries returned by this
            host, regardless of `entry_type`.
        failure_reason: A short, fixed diagnostic string when the walk did
            not complete, or `None` for a fully successful walk.
            Deliberately never derived from a caught exception's raw
            message — see ARCH-012 Security Considerations.
    """

    responded: bool
    entries_returned: int = 0
    failure_reason: str | None = None


@dataclass
class SnmpArpRunDiagnostics:
    """Represents run-level observability data for one ARP-neighbor enrichment pass.

    Attributes:
        hosts_eligible: The number of devices ARP-neighbor enrichment was
            asked to query (the already-discovered device set at phase
            start).
        hosts_queried: The number of devices actually queried (equal to
            `hosts_eligible` unless the run was interrupted).
        hosts_responded: The number of devices whose ARP-table walk
            completed successfully (including a walk that returned zero
            entries).
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
    host_diagnostics: dict[str, SnmpArpHostDiagnostics] = field(default_factory=dict)
