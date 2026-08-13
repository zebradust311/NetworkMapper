from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SnmpHostDiagnostics:
    """Represents what an SNMP query did and didn't find for one host.

    Attributes:
        responded: Whether the host returned any system-group field at all.
        fields_returned: Which system-group field names (e.g. "sysDescr")
            came back in the response. SNMPv2c can return a subset of
            requested fields inside an otherwise-successful PDU (a
            per-varbind noSuchObject/noSuchInstance exception on the
            others), so a host can respond without every field being
            present.
        failure_reason: A short, fixed diagnostic string when the host
            did not respond or the response could not be used, or `None`
            for a fully successful query. Deliberately never derived from
            a caught exception's raw message — see ARCH-012 Security
            Considerations on not propagating library exception text
            verbatim.
    """

    responded: bool
    fields_returned: list[str] = field(default_factory=list)
    failure_reason: str | None = None


@dataclass
class SnmpRunDiagnostics:
    """Represents run-level observability data for one SNMP enrichment pass.

    Attributes:
        hosts_eligible: The number of devices SNMP enrichment was asked
            to query (the already-discovered device set at phase start).
        hosts_queried: The number of devices actually queried (equal to
            `hosts_eligible` unless the run was interrupted).
        hosts_responded: The number of devices that returned at least one
            system-group field.
        hosts_timed_out: The number of devices that did not respond
            within the configured timeout/retry budget.
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
    host_diagnostics: dict[str, SnmpHostDiagnostics] = field(default_factory=dict)
