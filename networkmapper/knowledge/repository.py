from __future__ import annotations

import re
from pathlib import Path

from networkmapper.knowledge.models import Observation
from networkmapper.knowledge.serializer import ObservationSerializer

DEFAULT_OBSERVATIONS_ROOT = Path("knowledge/observations")

_FILENAME_PATTERN = re.compile(r"^observation-(\d{6})\.json$")


class ObservationNotFoundError(LookupError):
    """Raised when no observation file exists for a requested ID."""


class ObservationRepository:
    """Reads and writes one JSON file per observation under a directory.

    KNOW-003: this is storage only. Nothing here reads observations back
    into runtime classification, promotes an observation automatically,
    or changes an observation's status on its own — every write is an
    explicit call from a caller (a capture step, or a human review tool).
    """

    def __init__(self, root: Path | str = DEFAULT_OBSERVATIONS_ROOT) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def path_for(self, observation_id: int) -> Path:
        """Return the stable filename for an observation ID.

        Never derived from vendor, hostname, IP, or device type, so the
        filename stays valid even if later review changes what the
        observation is understood to be.
        """
        return self._root / f"observation-{observation_id:06d}.json"

    def next_observation_id(self) -> int:
        """Return the next stable, sequential observation ID.

        Always one greater than the highest ID currently present on disk
        — including ARCHIVED observations, which are never deleted — so
        IDs are never reused even after review changes an observation's
        status.
        """
        existing_ids = self._existing_ids()
        return max(existing_ids, default=0) + 1

    def save(self, observation: Observation) -> Path:
        """Write an observation to its stable path, creating the
        repository directory if needed. Overwrites any existing file for
        the same ID — the caller (e.g. a review tool) is responsible for
        deciding when that's appropriate."""
        self._root.mkdir(parents=True, exist_ok=True)
        path = self.path_for(observation.observation_id)
        path.write_text(ObservationSerializer.to_json(observation), encoding="utf-8")
        return path

    def load(self, observation_id: int) -> Observation:
        """Load one observation by ID."""
        path = self.path_for(observation_id)
        if not path.is_file():
            raise ObservationNotFoundError(f"No observation found for ID {observation_id}")
        return ObservationSerializer.from_json(path.read_text(encoding="utf-8"))

    def list_observation_ids(self) -> tuple[int, ...]:
        """Return every observation ID currently on disk, ascending."""
        return tuple(sorted(self._existing_ids()))

    def _existing_ids(self) -> list[int]:
        if not self._root.is_dir():
            return []

        observation_ids = []
        for entry in self._root.iterdir():
            match = _FILENAME_PATTERN.match(entry.name)
            if match:
                observation_ids.append(int(match.group(1)))

        return observation_ids
