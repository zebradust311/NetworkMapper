from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from networkmapper.core.network_graph import NetworkGraph


@dataclass
class Project:
    """Represents the root object for a NetworkMapper project.

    Attributes:
        customer_name: The customer or organization associated with the project.
        created_date: The date and time when the project was created.
        modified_date: The date and time when the project was last modified.
        network_graph: The in-memory graph of discovered devices for the project.
    """

    customer_name: str
    created_date: datetime = field(default_factory=datetime.now)
    modified_date: datetime = field(default_factory=datetime.now)
    network_graph: NetworkGraph = field(default_factory=NetworkGraph)
