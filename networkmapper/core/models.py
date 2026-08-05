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
class ServiceEvidence:
    """Represents discovery evidence observed for a single open port.

    Per ADR-009, per-service discovery evidence is represented as a
    correlated record rather than independent parallel lists, so that a
    port and everything discovered about it stay linked.

    Attributes:
        port: The observed open port number.
        protocol: The transport protocol used to reach the port ("tcp" or "udp").
        service: The service name identified on the port, if known.
        product: The product name identified on the port, if known.
        version: The product version identified on the port, if known.
        http_title: The HTML page title observed on the port, if known.
        tls_subject: The TLS certificate subject observed on the port, if known.
        tls_issuer: The TLS certificate issuer observed on the port, if known.
    """

    port: int
    protocol: str
    service: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    http_title: Optional[str] = None
    tls_subject: Optional[str] = None
    tls_issuer: Optional[str] = None


@dataclass
class Device:
    """Represents a discovered network device.

    Attributes:
        ip_address: The device's IP address.
        hostname: The device hostname, if available.
        mac_address: The device MAC address, if available.
        vendor: The vendor or manufacturer, if known.
        operating_system: The operating system, if identified.
        services: The correlated per-port discovery evidence observed for the device.
        device_type: The inferred device type, if known.
        discovery_sources: The discovery methods or providers that found the device.
    """

    ip_address: str
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    vendor: Optional[str] = None
    operating_system: Optional[str] = None
    services: list[ServiceEvidence] = field(default_factory=list)
    device_type: DeviceType = DeviceType.UNKNOWN
    discovery_sources: list[str] = field(default_factory=list)
