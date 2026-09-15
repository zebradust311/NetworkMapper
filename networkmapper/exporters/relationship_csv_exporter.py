from __future__ import annotations

import csv

from networkmapper.core.models import Device
from networkmapper.project.models import Project
from networkmapper.reporting.canonical_presentation import CanonicalPresentation, RelatedSubjectPresentation


class RelationshipCsvExporter:
    """Export canonical relationships to a dedicated CSV artifact."""

    def export(self, project: Project, output_path: str) -> None:
        """Write one CSV row per distinct (subject, category, related_subject)
        claim to the given output path.

        Args:
            project: The NetworkMapper project whose canonical relationships
                should be exported.
            output_path: The destination file path for the CSV output.
        """
        presentation = CanonicalPresentation.from_project(project)

        with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                [
                    "Subject",
                    "Subject Hostname",
                    "Category",
                    "Related Subject",
                    "Related Subject Hostname",
                    "Corroboration State",
                    "Provenance",
                ]
            )

            for relationship in presentation.relationships:
                for related in relationship.related:
                    writer.writerow(
                        [
                            relationship.subject,
                            _hostname(relationship.device),
                            relationship.category,
                            related.related_subject,
                            _hostname(related.device),
                            relationship.state.value,
                            _provenance_cell(related),
                        ]
                    )


def _hostname(device: Device | None) -> str:
    """Return the enriched device's hostname, or blank if there is no
    matching device or it has no hostname (PLAN-027 Section 4)."""
    if device is not None and device.hostname:
        return device.hostname
    return ""


def _provenance_cell(related: RelatedSubjectPresentation) -> str:
    """Return comma-joined provider/collection_method tokens, deduplicated
    by exact (provider, collection_method) pair, in first-seen
    `related.observations` tuple order — no independent re-sort
    (PLAN-027 Section 5.1).

    Presentation-level compression only: this never recomputes, explains,
    validates, or derives the canonical relationship's Corroboration
    State. Each row's tokens describe only this related subject's own
    observations, never the complete evidence behind the group's state.
    """
    seen: set[tuple[str, str]] = set()
    tokens: list[str] = []
    for observation in related.observations:
        key = (observation.provenance.provider, observation.provenance.collection_method)
        if key not in seen:
            seen.add(key)
            tokens.append(f"{key[0]}/{key[1]}")
    return ",".join(tokens)
