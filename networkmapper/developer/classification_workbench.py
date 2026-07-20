from __future__ import annotations

from networkmapper.core.models import Device, DeviceType
from networkmapper.project.models import Project


class ClassificationWorkbench:
    """Generate a developer-only evidence report for devices classified as UNKNOWN."""

    def generate(self, project: Project) -> str:
        """Create a plain-text report that exposes evidence for UNKNOWN devices.

        Args:
            project: The project snapshot to inspect for unknown-device evidence.

        Returns:
            A deterministic plain-text report intended for developer use.
        """
        unknown_devices = [
            device
            for device in project.network_graph.all_devices()
            if device.device_type == DeviceType.UNKNOWN
        ]

        if not unknown_devices:
            return "No UNKNOWN devices found."

        sections: list[str] = []
        for device in unknown_devices:
            sections.append(self._render_device_section(device))

        return "\n\n".join(sections)

    def _render_device_section(self, device: Device) -> str:
        """Render a single UNKNOWN-device evidence section for developer inspection."""
        return (
            "=" * 50
            + "\n"
            + "UNKNOWN DEVICE\n"
            + "=" * 50
            + "\n\n"
            + f"IP Address:\n{self._display_value(device.ip_address)}\n\n"
            + f"Hostname:\n{self._display_value(device.hostname)}\n\n"
            + f"Vendor:\n{self._display_value(device.vendor)}\n\n"
            + f"MAC Address:\n{self._display_value(device.mac_address)}\n\n"
            + f"Operating System:\n{self._display_value(device.operating_system)}\n\n"
            + "Open Ports:\n"
            + f"{self._display_value(None)}\n\n"
            + "Detected Services:\n"
            + f"{self._display_value(None)}\n\n"
            + f"Current DeviceType:\n{self._display_value(device.device_type)}\n"
            + "\n"
            + "=" * 50
        )

    def _display_value(self, value: object) -> str:
        """Return a clean display string for missing values in the report."""
        if value is None:
            return "Unknown"
        if isinstance(value, str) and not value.strip():
            return "Unknown"
        return str(value)
