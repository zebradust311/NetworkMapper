from __future__ import annotations

import csv

from networkmapper.core.models import Device
from networkmapper.project.models import Project


class CsvExporter:
    """Export discovered project devices to CSV format."""

    def export(self, project: Project, output_path: str) -> None:
        """Write one CSV row per discovered device to the given output path.

        Args:
            project: The NetworkMapper project whose graph should be exported.
            output_path: The destination file path for the CSV output.
        """
        with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                [
                    "IP Address",
                    "Hostname",
                    "Vendor",
                    "Device Type",
                    "Discovery Sources",
                    # REPORT-003: appended after the original five columns
                    # (rather than interleaved) so any existing tooling
                    # reading these columns by position is unaffected.
                    "SNMP Description",
                    "SNMP Location",
                    "SNMP Contact",
                    "SNMP Uptime",
                ]
            )

            for device in project.network_graph.all_devices():
                writer.writerow(
                    [
                        device.ip_address or "",
                        device.hostname or "",
                        device.vendor or "",
                        # .value (e.g. "server"), not .name ("SERVER") — matches
                        # MarkdownExporter's DeviceType display convention (STAB-001).
                        device.device_type.value if device.device_type else "",
                        ",".join(device.discovery_sources or []),
                        device.snmp_sys_descr or "",
                        device.snmp_sys_location or "",
                        device.snmp_sys_contact or "",
                        device.snmp_sys_uptime or "",
                    ]
                )


def _stringify_value(value: object) -> str:
    """Return a blank string for missing values, otherwise stringify the value."""
    if value is None:
        return ""
    return str(value)
