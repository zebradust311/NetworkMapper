from __future__ import annotations

from dataclasses import dataclass, field

from networkmapper.core.models import Device
from networkmapper.project.models import Project


@dataclass
class ComparisonResult:
    """Stores the output of comparing two project snapshots."""

    added_devices: list[Device] = field(default_factory=list)
    removed_devices: list[Device] = field(default_factory=list)
    hostname_changed_devices: list[tuple[Device, Device]] = field(default_factory=list)
    ip_changed_devices: list[tuple[Device, Device]] = field(default_factory=list)
    summary_counts: dict[str, int] = field(default_factory=dict)


class ProjectComparator:
    """Compare two project snapshots and report device-level changes."""

    def compare(self, old_project: Project, new_project: Project) -> ComparisonResult:
        """Compare device inventories between two projects and return a result object.

        The comparison prefers MAC address identity when available, and falls
        back to IP address when MAC address data is unavailable.

        Args:
            old_project: The earlier project snapshot to compare against.
            new_project: The later project snapshot to compare against.

        Returns:
            A comparison result containing added devices, removed devices, and
            any hostname or IP changes observed between the two snapshots.
        """
        old_devices = self._index_devices(old_project)
        new_devices = self._index_devices(new_project)

        added_devices: list[Device] = []
        removed_devices: list[Device] = []
        hostname_changed_devices: list[tuple[Device, Device]] = []
        ip_changed_devices: list[tuple[Device, Device]] = []

        for identity, old_device in old_devices.items():
            if identity not in new_devices:
                removed_devices.append(old_device)
                continue

            new_device = new_devices[identity]

            if old_device.hostname != new_device.hostname:
                hostname_changed_devices.append((old_device, new_device))

            if old_device.ip_address != new_device.ip_address:
                ip_changed_devices.append((old_device, new_device))

        for identity, new_device in new_devices.items():
            if identity not in old_devices:
                added_devices.append(new_device)

        return ComparisonResult(
            added_devices=added_devices,
            removed_devices=removed_devices,
            hostname_changed_devices=hostname_changed_devices,
            ip_changed_devices=ip_changed_devices,
            summary_counts={
                "added": len(added_devices),
                "removed": len(removed_devices),
                "hostname_changed": len(hostname_changed_devices),
                "ip_changed": len(ip_changed_devices),
            },
        )

    def _index_devices(self, project: Project) -> dict[str, Device]:
        """Build a lookup keyed by MAC address when available, otherwise IP address.

        Args:
            project: The project snapshot to index.

        Returns:
            A mapping of stable device identity to the corresponding device.
        """
        indexed_devices: dict[str, Device] = {}

        for device in project.network_graph.all_devices():
            identity = self._device_identity(device)
            indexed_devices[identity] = device

        return indexed_devices

    def _device_identity(self, device: Device) -> str:
        """Return the stable device identity for comparison purposes.

        MAC address is preferred because it is usually more stable than IP
        address. If no MAC is present, the device IP address is used.
        """
        mac_address = (device.mac_address or "").strip().lower()
        if mac_address:
            return mac_address

        return (device.ip_address or "").strip().lower()
