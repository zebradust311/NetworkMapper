from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ObservationProvenance:
    """Per-observation provenance required by ADR-011.

    Preserves enough context to determine the originating provider, how
    the value was collected, when it was observed, and which run it
    belongs to — the minimum ADR-011's Provenance section requires so a
    future resolver can judge observation independence (ARCH-015
    Section 7, ADR-012's Observation Independence) rather than merely
    counting matching fields. Deliberately richer than
    `Device.discovery_sources` (`networkmapper/core/models.py`), a flat,
    unattributed list of provider names ADR-011 found insufficient for
    this purpose.

    Attributes:
        provider: The evidence source that produced the value (e.g.
            "nmap", "snmp").
        collection_method: How the value was obtained (e.g.
            "smb-os-discovery", "sysDescr"). Distinguishing this from
            `provider` is required for the same-source double-counting
            trap ADR-011/ADR-012 both name — two values from the same
            provider via different collection methods are not
            automatically the same underlying claim.
        observed_at: When the value was observed.
        source_run: An opaque identifier for the run/scan this
            observation belongs to. Intentionally a plain string rather
            than a reference to `RunMetadata`
            (`networkmapper/reporting/report_run.py`) — this package has
            no dependency on the reporting layer, and ADR-011 defers the
            concrete run-identity mechanism.
    """

    provider: str
    collection_method: str
    observed_at: datetime
    source_run: str
