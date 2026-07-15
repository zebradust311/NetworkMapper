"""
Main application controller for NetworkMapper.
"""

from networkmapper.discovery.discovery_engine import DiscoveryEngine
from networkmapper.discovery.nmap_provider import NmapProvider


class Application:
    """Coordinates the execution of the NetworkMapper application."""

    def __init__(self) -> None:
        """Initialize the application."""
        print("Application initialized.")

    def run(self) -> None:
        """Run the application."""
        print("NetworkMapper is starting...")

        # Temporary test subnet
        provider = NmapProvider("172.16.100.0/24")

        engine = DiscoveryEngine([provider])

        graph = engine.discover()

        print(f"\nDiscovered {graph.device_count()} devices:\n")

        for device in graph.all_devices():
            hostname = device.hostname or "Unknown"
            print(f"{device.ip_address:<15} {hostname}")