from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SnmpVersion(StrEnum):
    """SNMP protocol versions FEAT-005 supports.

    ARCH-012/ADR-010: v2c is the only version implemented. SNMPv1's
    GetRequest semantics fail the entire PDU if any one requested OID is
    unavailable on the agent (unlike v2c, which returns a per-varbind
    noSuchObject/noSuchInstance sentinel instead) — incompatible with
    this provider's single, six-OID system-group GET, so v1 was dropped
    at implementation time per ARCH-012's own "if the library makes it
    meaningfully more code than a flag, drop it" guidance. SNMPv3 is
    deferred to its own follow-on sprint (ARCH-012 Implementation
    Sequence item 3).
    """

    V2C = "v2c"


@dataclass(repr=False)
class SnmpCredentials:
    """Runtime-only SNMP credentials.

    Never a field of, or input to constructing, `Device`, `RunMetadata`,
    or any `Observation` model — see ARCH-012 Credential Strategy. Never
    persisted, logged, or included in any `RuntimeEvent.activity` string.

    `repr=False` with a custom `__repr__` is deliberate: a dataclass's
    default `repr` prints every field value, and this object will
    inevitably end up in a debugger session or traceback during
    development if nothing prevents the community string from being
    printed.
    """

    version: SnmpVersion
    community: str

    def __repr__(self) -> str:
        return f"SnmpCredentials(version={self.version!r}, community='***')"
