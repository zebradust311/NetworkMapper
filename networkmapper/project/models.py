from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from networkmapper.core.network_graph import NetworkGraph
from networkmapper.observations.models import IdentityObservation, RelationshipObservation


@dataclass
class Project:
    """Represents the root object for a NetworkMapper project.

    Attributes:
        customer_name: The customer or organization associated with the project.
        created_date: The date and time when the project was created.
        modified_date: The date and time when the project was last modified.
        network_graph: The in-memory graph of discovered devices for the project.
        observations: Retained observations collected during the run that
            produced this Project (FEAT-007A/ARCH-017 Stage 2). Run-scoped
            only — ProjectSerializer does not persist this field (ADR-011
            defers observation persistence), so it does not survive a
            save/load round-trip. Not consumed by classification,
            reporting, or any existing subsystem.
    """

    customer_name: str
    created_date: datetime = field(default_factory=datetime.now)
    modified_date: datetime = field(default_factory=datetime.now)
    network_graph: NetworkGraph = field(default_factory=NetworkGraph)
    observations: list[IdentityObservation | RelationshipObservation] = field(default_factory=list)
