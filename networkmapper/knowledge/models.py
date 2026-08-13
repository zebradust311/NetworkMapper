from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional


class ObservationStatus(StrEnum):
    """Human-controlled lifecycle state of a field observation.

    KNOW-003: state transitions never occur automatically — an observation
    only changes status when a human reviewer records a review-history
    entry. An observation existing, or being read, never influences
    runtime classification.
    """

    NEW = "NEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    VALIDATED = "VALIDATED"
    IMPLEMENTED = "IMPLEMENTED"
    ARCHIVED = "ARCHIVED"


@dataclass
class ObservationNetwork:
    """Identifies the network/customer environment an observation came from."""

    name: str


@dataclass
class ObservationScan:
    """Identifies the run that produced an observation.

    Mirrors networkmapper.reporting.report_run.RunMetadata's scan_profile
    and version fields rather than inventing parallel ones.
    """

    profile: str
    networkmapper_version: Optional[str] = None


@dataclass
class ObservationDevice:
    """Stable device-identity fields, mirroring networkmapper.core.models.Device.

    Deliberately limited to the fields used to recognize the device
    (ip/hostname/vendor/mac). Anything discovery observed *about* the
    device, rather than identifying it, belongs in ObservationEvidence.
    """

    ip: Optional[str] = None
    hostname: Optional[str] = None
    vendor: Optional[str] = None
    mac_address: Optional[str] = None


@dataclass
class ObservationServiceEvidence:
    """Mirrors networkmapper.core.models.ServiceEvidence field-for-field.

    Per ADR-009, per-service evidence is a correlated record, not
    independent parallel lists — that shape is preserved here rather than
    flattened.
    """

    port: int
    protocol: str
    service: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    http_title: Optional[str] = None
    tls_subject: Optional[str] = None
    tls_issuer: Optional[str] = None
    http_auth_realm: Optional[str] = None


@dataclass
class ObservationEvidence:
    """Everything discovery observed about the device beyond its stable identity.

    operating_system/computer_name/domain/smb_signing mirror the
    equivalent Device fields; services mirrors Device.services.
    """

    operating_system: Optional[str] = None
    computer_name: Optional[str] = None
    domain: Optional[str] = None
    smb_signing: Optional[str] = None
    discovery_sources: list[str] = field(default_factory=list)
    services: list[ObservationServiceEvidence] = field(default_factory=list)


@dataclass
class ObservationClassification:
    """The classification result at capture time — a fact about that run,
    not a live link. Re-running classification later does not update this."""

    type: str
    reason: str
    matched_rule: Optional[str] = None


@dataclass
class ObservationReviewEntry:
    """One structured entry in an observation's review history.

    `reference` names the rule or sprint that incorporated the
    observation once action is IMPLEMENTED (e.g. "RULE-004" or a rule
    class name), kept structured and separate from free-form `notes`.
    """

    reviewed_at: str
    action: ObservationStatus
    notes: str = ""
    reference: Optional[str] = None


@dataclass
class Observation:
    """A single field observation: one device's discovery/classification
    evidence from one run, preserved for future human review.

    Recording an observation, or changing its status, never affects
    runtime classification — see ObservationStatus.
    """

    observation_id: int
    captured_at: str
    network: ObservationNetwork
    scan: ObservationScan
    device: ObservationDevice
    evidence: ObservationEvidence
    classification: ObservationClassification
    status: ObservationStatus = ObservationStatus.NEW
    schema_version: int = 1
    technician_notes: str = ""
    review_history: list[ObservationReviewEntry] = field(default_factory=list)
