from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from networkmapper.core.models import Device, DeviceType
from networkmapper.core.network_graph import NetworkGraph
from networkmapper.project.models import Project


class ProjectSerializer:
    """Serialize and deserialize Project objects using JSON."""

    @staticmethod
    def save(project: Project, file_path: str) -> None:
        """Persist a Project instance to a JSON file."""
        payload = {
            "customer_name": project.customer_name,
            "created_date": project.created_date.isoformat(),
            "modified_date": project.modified_date.isoformat(),
            "devices": [
                {
                    "ip_address": device.ip_address,
                    "hostname": device.hostname,
                    "mac_address": device.mac_address,
                    "vendor": device.vendor,
                    "operating_system": device.operating_system,
                    "device_type": device.device_type.value,
                    "discovery_sources": device.discovery_sources,
                }
                for device in project.network_graph.all_devices()
            ],
        }

        with open(file_path, "w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2)

    @staticmethod
    def load(file_path: str) -> Project:
        """Load a Project instance from a JSON file."""
        with open(file_path, "r", encoding="utf-8") as file_handle:
            payload: dict[str, Any] = json.load(file_handle)

        project = Project(
            customer_name=payload["customer_name"],
            created_date=datetime.fromisoformat(payload["created_date"]),
            modified_date=datetime.fromisoformat(payload["modified_date"]),
            network_graph=NetworkGraph(),
        )

        for device_payload in payload.get("devices", []):
            device = Device(
                ip_address=device_payload["ip_address"],
                hostname=device_payload.get("hostname"),
                mac_address=device_payload.get("mac_address"),
                vendor=device_payload.get("vendor"),
                operating_system=device_payload.get("operating_system"),
                device_type=DeviceType(device_payload.get("device_type", DeviceType.UNKNOWN.value)),
                discovery_sources=device_payload.get("discovery_sources", []),
            )
            project.network_graph.add_device(device)

        return project
