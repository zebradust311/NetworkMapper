"""
Main application controller for NetworkMapper.
"""

from networkmapper.discovery.discovery_engine import DiscoveryEngine
from networkmapper.discovery.nmap_provider import NmapProvider
from networkmapper.project.models import Project
from networkmapper.project.serializer import ProjectSerializer


class Application:
    """Coordinates the execution of the NetworkMapper application."""

    def __init__(self) -> None:
        """Initialize the application."""
        print("Application initialized.")

    def run(self) -> None:
        """Run the temporary persistence validation harness."""
        print("NetworkMapper is starting...\n")

        provider = NmapProvider("172.16.100.0/24")
        engine = DiscoveryEngine([provider])

        graph = engine.discover()
        before_save_count = graph.device_count()

        project = Project(
            customer_name="Test Network",
            network_graph=graph,
        )

        ProjectSerializer.save(project, "test.nmproj")

        loaded_project = ProjectSerializer.load("test.nmproj")

        after_save_count = loaded_project.network_graph.device_count()

        print(f"Customer Name          : {loaded_project.customer_name}")
        print(f"Device Count (Before)  : {before_save_count}")
        print(f"Device Count (After)   : {after_save_count}")

        if before_save_count == after_save_count:
            print("\n✓ Persistence validation successful.")
        else:
            print("\n✗ Persistence validation FAILED.")

            raise RuntimeError(
                "Loaded project device count does not match saved project."
            )