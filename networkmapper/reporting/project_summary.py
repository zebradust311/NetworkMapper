from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from networkmapper.core.models import DeviceType
from networkmapper.project.models import Project


@dataclass
class ProjectSummary:
    """Represents a reusable, high-level summary of a project snapshot."""

    customer_name: str
    created_at: datetime
    updated_at: datetime
    total_devices: int
    device_type_counts: dict[DeviceType, int] = field(default_factory=dict)
    vendor_counts: dict[str, int] = field(default_factory=dict)
    discovered_networks: list[str] = field(default_factory=list)

    @classmethod
    def from_project(cls, project: Project) -> ProjectSummary:
        """Create a project summary from a project snapshot.

        Args:
            project: The project whose device inventory should be summarized.

        Returns:
            A reusable summary object containing high-level counts for the
            project without any presentation-specific behavior.
        """
        device_type_counts: dict[DeviceType, int] = {}
        vendor_counts: dict[str, int] = {}

        for device in project.network_graph.all_devices():
            device_type = device.device_type
            device_type_counts[device_type] = (
                 device_type_counts.get(device_type, 0) + 1
            )

            vendor = (device.vendor or "").strip()
            if vendor:
                vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1

        return cls(
            customer_name=project.customer_name,
            created_at=project.created_date,
            updated_at=project.modified_date,
            total_devices=project.network_graph.device_count(),
            device_type_counts=device_type_counts,
            vendor_counts=vendor_counts,
            discovered_networks=[],
        )
