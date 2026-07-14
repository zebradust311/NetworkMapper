from __future__ import annotations

from typing import Optional

from networkmapper.core.models import Device


class NetworkGraph:
    """Stores network devices keyed by IP address for simple graph-style access."""

    def __init__(self) -> None:
        """Initialize an empty graph of devices."""
        self._devices: dict[str, Device] = {}

    def add_device(self, device: Device) -> None:
        """Add a device to the graph if its IP address is not already present."""
        if device.ip_address in self._devices:
            return
        self._devices[device.ip_address] = device

    def get_device(self, ip_address: str) -> Optional[Device]:
        """Return the stored device for the given IP address, if present."""
        return self._devices.get(ip_address)

    def all_devices(self) -> list[Device]:
        """Return all stored devices as a list."""
        return list(self._devices.values())

    def device_count(self) -> int:
        """Return the number of stored devices."""
        return len(self._devices)
