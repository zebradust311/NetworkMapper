from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional


class DeviceType(StrEnum):
    """Supported network device categories."""

    UNKNOWN = "unknown"
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    SERVER = "server"
    WORKSTATION = "workstation"
    PRINTER = "printer"
    PHONE = "phone"
    ACCESS_POINT = "access_point"
    HYPERVISOR = "hypervisor"


@dataclass
class Device:
    """Represents a discovered network device.

    Attributes:
        ip_address: The device's IP address.
        hostname: The device hostname, if available.
        mac_address: The device MAC address, if available.
        vendor: The vendor or manufacturer, if known.
        operating_system: The operating system, if identified.
        open_ports: The list of known open ports, if identified.
        detected_services: The list of known detected services, if identified.
        device_type: The inferred device type, if known.
        discovery_sources: The discovery methods or providers that found the device.
    """

    ip_address: str
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    vendor: Optional[str] = None
    operating_system: Optional[str] = None
    open_ports: list[int] = field(default_factory=list)
    detected_services: list[str] = field(default_factory=list)
    device_type: DeviceType = DeviceType.UNKNOWN
    discovery_sources: list[str] = field(default_factory=list)
