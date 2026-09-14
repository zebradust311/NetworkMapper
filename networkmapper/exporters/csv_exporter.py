from __future__ import annotations

import csv

from networkmapper.core.models import Device
from networkmapper.identity.models import IdentityCorroborationState
from networkmapper.project.models import Project
from networkmapper.reporting.canonical_presentation import CanonicalPresentation, IdentityPresentation


class CsvExporter:
    """Export discovered project devices to CSV format."""

    def export(self, project: Project, output_path: str) -> None:
        """Write one CSV row per discovered device to the given output path.

        Args:
            project: The NetworkMapper project whose graph should be exported.
            output_path: The destination file path for the CSV output.
        """
        # FEAT-026 Slice 1: canonical identity summary columns are sourced
        # exclusively from CanonicalPresentation (never re-resolved) and
        # matched to device rows by subject == ip_address only (PLAN-026
        # Section 3.3) — this is the sole matching path, not a heuristic.
        presentation = CanonicalPresentation.from_project(project)
        identity_by_subject = {identity.subject: identity for identity in presentation.identities}

        with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                [
                    "IP Address",
                    "Hostname",
                    "Vendor",
                    "Device Type",
                    "Discovery Sources",
                    # REPORT-003: appended after the original five columns
                    # (rather than interleaved) so any existing tooling
                    # reading these columns by position is unaffected.
                    "SNMP Description",
                    "SNMP Location",
                    "SNMP Contact",
                    "SNMP Uptime",
                    # FEAT-026 Slice 1: appended after the existing nine
                    # columns per the same append-only precedent.
                    "Canonical Identity State",
                    "Conflicting Identity Properties",
                ]
            )

            for device in project.network_graph.all_devices():
                identity = identity_by_subject.get(device.ip_address)
                writer.writerow(
                    [
                        device.ip_address or "",
                        device.hostname or "",
                        device.vendor or "",
                        # .value (e.g. "server"), not .name ("SERVER") — matches
                        # MarkdownExporter's DeviceType display convention (STAB-001).
                        device.device_type.value if device.device_type else "",
                        ",".join(device.discovery_sources or []),
                        device.snmp_sys_descr or "",
                        device.snmp_sys_location or "",
                        device.snmp_sys_contact or "",
                        device.snmp_sys_uptime or "",
                        _canonical_identity_state(identity),
                        _conflicting_identity_properties(identity),
                    ]
                )


def _canonical_identity_state(identity: IdentityPresentation | None) -> str:
    """Return the identity-level corroboration state, unmodified, or blank
    if no canonical identity matched this device's IP (PLAN-026 Section 3.1)."""
    if identity is None:
        return ""
    return identity.state.value


def _conflicting_identity_properties(identity: IdentityPresentation | None) -> str:
    """Return comma-joined property names in CONFLICTING state, in
    `identity.properties` tuple order — no independent sort (PLAN-026 Section 3.3)."""
    if identity is None:
        return ""
    return ",".join(
        property_presentation.property_name
        for property_presentation in identity.properties
        if property_presentation.state == IdentityCorroborationState.CONFLICTING
    )


def _stringify_value(value: object) -> str:
    """Return a blank string for missing values, otherwise stringify the value."""
    if value is None:
        return ""
    return str(value)
