from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SnmpBridgeFdbHostDiagnostics:
    """Represents what an SNMP Bridge-MIB forwarding-table walk did and
    didn't find for one host.

    Attributes:
        responded: Whether the host's `dot1dTpFdbTable` walk completed
            successfully. `True` even when the table has zero entries, or
            the device has no Bridge-MIB support at all — both are
            legitimate results (ARCH-024 Section 7), not signs of
            non-response, mirroring `SnmpArpHostDiagnostics`'s own
            docstring for its own table.
        entries_returned: The number of `dot1dTpFdbTable` rows returned
            by this host, regardless of `status` or whether any resolved
            to a `RelationshipObservation`.
        failure_reason: A short, fixed diagnostic string when the walk did
            not complete, or `None` for a fully successful walk.
            Deliberately never derived from a caught exception's raw
            message — see ARCH-012 Security Considerations.
    """

    responded: bool
    entries_returned: int = 0
    failure_reason: str | None = None


@dataclass
class SnmpBridgeFdbRunDiagnostics:
    """Represents run-level observability data for one Bridge-FDB enrichment pass.

    Attributes:
        hosts_eligible: The number of devices Bridge-FDB enrichment was
            asked to query (the already-discovered device set at phase
            start).
        hosts_queried: The number of devices actually queried (equal to
            `hosts_eligible` unless the run was interrupted).
        hosts_responded: The number of devices whose `dot1dTpFdbTable`
            walk completed successfully (including a walk that returned
            zero rows).
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
    host_diagnostics: dict[str, SnmpBridgeFdbHostDiagnostics] = field(default_factory=dict)
