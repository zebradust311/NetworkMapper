from __future__ import annotations

import json
from typing import Any

from networkmapper.knowledge.models import (
    Observation,
    ObservationClassification,
    ObservationDevice,
    ObservationEvidence,
    ObservationNetwork,
    ObservationReviewEntry,
    ObservationScan,
    ObservationServiceEvidence,
    ObservationStatus,
)

CURRENT_SCHEMA_VERSION = 1


class ObservationSchemaError(ValueError):
    """Raised when an observation payload is missing a required field or
    uses a value KNOW-003's schema does not accept (e.g. an unknown
    lifecycle status)."""


class ObservationSerializer:
    """Serialize and deserialize Observation records using JSON.

    Follows the same explicit-dict-mapping style as
    networkmapper.project.serializer.ProjectSerializer rather than adding
    to_dict/from_dict methods onto the dataclasses themselves.
    """

    @staticmethod
    def to_dict(observation: Observation) -> dict[str, Any]:
        """Convert an Observation into a plain, JSON-serializable dict."""
        return {
            "schema_version": observation.schema_version,
            "observation_id": observation.observation_id,
            "status": observation.status.value,
            "captured_at": observation.captured_at,
            "network": {
                "name": observation.network.name,
            },
            "scan": {
                "profile": observation.scan.profile,
                "networkmapper_version": observation.scan.networkmapper_version,
            },
            "device": {
                "ip": observation.device.ip,
                "hostname": observation.device.hostname,
                "vendor": observation.device.vendor,
                "mac_address": observation.device.mac_address,
            },
            "evidence": {
                "operating_system": observation.evidence.operating_system,
                "computer_name": observation.evidence.computer_name,
                "domain": observation.evidence.domain,
                "smb_signing": observation.evidence.smb_signing,
                "discovery_sources": list(observation.evidence.discovery_sources),
                "services": [
                    {
                        "port": entry.port,
                        "protocol": entry.protocol,
                        "service": entry.service,
                        "product": entry.product,
                        "version": entry.version,
                        "http_title": entry.http_title,
                        "tls_subject": entry.tls_subject,
                        "tls_issuer": entry.tls_issuer,
                        "http_auth_realm": entry.http_auth_realm,
                    }
                    for entry in observation.evidence.services
                ],
            },
            "classification": {
                "type": observation.classification.type,
                "reason": observation.classification.reason,
                "matched_rule": observation.classification.matched_rule,
            },
            "technician_notes": observation.technician_notes,
            "review_history": [
                {
                    "reviewed_at": entry.reviewed_at,
                    "action": entry.action.value,
                    "notes": entry.notes,
                    "reference": entry.reference,
                }
                for entry in observation.review_history
            ],
        }

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> Observation:
        """Reconstruct an Observation from a decoded JSON dict.

        Raises ObservationSchemaError for a missing required field or an
        invalid lifecycle status/action — StrEnum's constructor already
        rejects any value outside ObservationStatus, so no separate
        allow-list check is needed.
        """
        try:
            schema_version = payload["schema_version"]
            observation_id = payload["observation_id"]
            captured_at = payload["captured_at"]
            network_payload = payload["network"]
            scan_payload = payload["scan"]
            device_payload = payload["device"]
            evidence_payload = payload["evidence"]
            classification_payload = payload["classification"]
        except KeyError as missing_field:
            raise ObservationSchemaError(
                f"Observation payload missing required field: {missing_field}"
            ) from missing_field

        try:
            status = ObservationStatus(payload.get("status", ObservationStatus.NEW.value))
        except ValueError as invalid_status:
            raise ObservationSchemaError(
                f"Observation payload has an invalid status: {payload.get('status')!r}"
            ) from invalid_status

        review_history = []
        for entry_payload in payload.get("review_history", []):
            try:
                action = ObservationStatus(entry_payload["action"])
            except (KeyError, ValueError) as invalid_action:
                raise ObservationSchemaError(
                    f"Review history entry has an invalid action: "
                    f"{entry_payload.get('action')!r}"
                ) from invalid_action

            review_history.append(
                ObservationReviewEntry(
                    reviewed_at=entry_payload["reviewed_at"],
                    action=action,
                    notes=entry_payload.get("notes", ""),
                    reference=entry_payload.get("reference"),
                )
            )

        return Observation(
            schema_version=schema_version,
            observation_id=observation_id,
            status=status,
            captured_at=captured_at,
            network=ObservationNetwork(name=network_payload["name"]),
            scan=ObservationScan(
                profile=scan_payload["profile"],
                networkmapper_version=scan_payload.get("networkmapper_version"),
            ),
            device=ObservationDevice(
                ip=device_payload.get("ip"),
                hostname=device_payload.get("hostname"),
                vendor=device_payload.get("vendor"),
                mac_address=device_payload.get("mac_address"),
            ),
            evidence=ObservationEvidence(
                operating_system=evidence_payload.get("operating_system"),
                computer_name=evidence_payload.get("computer_name"),
                domain=evidence_payload.get("domain"),
                smb_signing=evidence_payload.get("smb_signing"),
                discovery_sources=list(evidence_payload.get("discovery_sources", [])),
                services=[
                    ObservationServiceEvidence(
                        port=entry["port"],
                        protocol=entry["protocol"],
                        service=entry.get("service"),
                        product=entry.get("product"),
                        version=entry.get("version"),
                        http_title=entry.get("http_title"),
                        tls_subject=entry.get("tls_subject"),
                        tls_issuer=entry.get("tls_issuer"),
                        http_auth_realm=entry.get("http_auth_realm"),
                    )
                    for entry in evidence_payload.get("services", [])
                ],
            ),
            classification=ObservationClassification(
                type=classification_payload["type"],
                reason=classification_payload["reason"],
                matched_rule=classification_payload.get("matched_rule"),
            ),
            technician_notes=payload.get("technician_notes", ""),
            review_history=review_history,
        )

    @staticmethod
    def to_json(observation: Observation) -> str:
        """Render an Observation as an indented JSON string."""
        return json.dumps(ObservationSerializer.to_dict(observation), indent=2)

    @staticmethod
    def from_json(text: str) -> Observation:
        """Parse an Observation from a JSON string."""
        return ObservationSerializer.from_dict(json.loads(text))
