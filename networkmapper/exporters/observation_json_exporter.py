from __future__ import annotations

from networkmapper.observations.replay_format import serialize_observations
from networkmapper.project.models import Project


class ObservationJsonExporter:
    """Export a run's retained observations to its replay artifact
    (ADR-011 Amendment 1; PLAN-029)."""

    def export(self, project: Project, output_path: str) -> None:
        """Write every retained observation in the project to the given
        output path, in the versioned replay format.

        A read-only consumer (ADR-005): only `project.observations` is
        read, and nothing on the project is modified. Canonical identities
        and relationships are interpretations and are never written. The
        file is written once per application run with plain overwrite,
        matching the other report artifacts (PLAN-029 D9), and as bytes so
        its content is identical on every platform.

        Args:
            project: The NetworkMapper project whose retained observations
                should be exported.
            output_path: The destination file path for the JSON output.
        """
        payload = serialize_observations(project.observations)

        with open(output_path, "wb") as json_file:
            json_file.write(payload)
