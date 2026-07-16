from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

from networkmapper.core.models import Device, DeviceType
from networkmapper.project.models import Project
from networkmapper.reporting.project_summary import ProjectSummary


class MarkdownExporter:
    """Export a project snapshot as a Markdown document."""

    def export(self, project: Project, output_path: str) -> None:
        """Write a Markdown report for a project to the given output path.

        Args:
            project: The project snapshot to export.
            output_path: The output file path for the Markdown report.
        """
        summary = ProjectSummary.from_project(project)
        markdown_lines = self._render_markdown(project, summary)

        with open(output_path, "w", encoding="utf-8") as markdown_file:
            markdown_file.write("\n".join(markdown_lines) + "\n")

    def _render_markdown(self, project: Project, summary: ProjectSummary) -> list[str]:
        """Render a project summary and inventory into Markdown lines."""
        lines: list[str] = []
        lines.append("# Customer")
        lines.append("")
        lines.append(f"- Customer Name: {self._display_value(summary.customer_name)}")
        lines.append(f"- Created: {self._display_value(summary.created_at)}")
        lines.append(f"- Last Updated: {self._display_value(summary.updated_at)}")
        lines.append("")
        lines.append("# Executive Summary")
        lines.append("")
        lines.append(f"- Total Devices: {summary.total_devices}")
        lines.append("")
        lines.append("## Device Types")
        lines.append("")
        for device_type, count in sorted(
            summary.device_type_counts.items(),
            key=lambda item: item[0].value,
        ):
            lines.append(f"- {self._display_title(device_type)}: {count}")
        lines.append("")
        lines.append("# Device Inventory")
        lines.append("")

        inventory = self._group_devices_by_type(project)
        for device_type, devices in sorted(
            inventory.items(),
            key=lambda item: self._plural_title(item[0]),
        ):
            lines.append(f"## {self._plural_title(device_type)}")
            lines.append("")
            lines.append(f"Total: {len(devices)}")
            lines.append("")
            lines.extend(self._render_section_manufacturers(devices))
            lines.append("---")
            lines.append("")
            for device in devices:
                lines.append(
                    f"### {self._display_title(device.hostname or device.ip_address or 'Unknown')}"
                )
                lines.append(f"- IP Address: {self._display_value(device.ip_address)}")
                lines.append(f"- Hostname: {self._display_value(device.hostname)}")
                lines.append(f"- Vendor: {self._display_value(device.vendor)}")
                lines.append(
                    f"- Discovery Sources: {self._display_value(','.join(device.discovery_sources or []))}"
                )
                lines.append("")

        return lines

    def _group_devices_by_type(self, project: Project) -> dict[DeviceType, list[Device]]:
        """Group inventory devices by their device type for Markdown rendering."""
        grouped_devices: dict[DeviceType, list[Device]] = defaultdict(list)

        for device in sorted(
            project.network_graph.all_devices(),
            key=lambda device: (
                device.hostname or "",
                device.ip_address or "",
            ),
        ):
            grouped_devices[device.device_type].append(device)

        return grouped_devices

    def _render_section_manufacturers(self, devices: list[Device]) -> list[str]:
        """Render a section summary for manufacturer distribution in a device type group."""
        lines: list[str] = []
        manufacturer_counts = Counter(
            self._display_value(device.vendor) for device in devices
        )
        unique_manufacturers = set(manufacturer_counts)

        if len(unique_manufacturers) == 1:
            lines.append("Manufacturer")
            lines.append("")
            lines.append(f"{next(iter(unique_manufacturers))}")
            lines.append("")
            return lines

        lines.append("Manufacturers")
        lines.append("")
        for manufacturer, count in sorted(manufacturer_counts.items()):
            lines.append(f"- {manufacturer}: {count}")
        lines.append("")
        return lines

    def _display_value(self, value: object) -> str:
        """Return a user-friendly string for values that may be missing."""
        if value is None:
            return "Unknown"
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str) and not value.strip():
            return "Unknown"
        return str(value)

    def _display_title(self, value: object) -> str:
        """Return a display-friendly title for headings and labels."""
        if value is None:
            return "Unknown"
        if isinstance(value, DeviceType):
            return value.value.replace("_", " ").title()
        if isinstance(value, str) and not value.strip():
            return "Unknown"
        return str(value)

    def _plural_title(self, value: object) -> str:
        """Return the pluralized heading form for a given device type."""
        if isinstance(value, DeviceType):
            device_title = self._display_title(value)
            return {
                "Server": "Servers",
                "Workstation": "Workstations",
                "Printer": "Printers",
                "Switch": "Switches",
                "Router": "Routers",
                "Firewall": "Firewalls",
                "Access Point": "Access Points",
                "Hypervisor": "Hypervisors",
                "Unknown": "Unknown",
            }.get(device_title, device_title)
        return self._display_title(value)
