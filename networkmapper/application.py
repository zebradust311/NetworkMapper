"""
Main application controller for NetworkMapper.
"""


from networkmapper.discovery.discovery_engine import DiscoveryEngine
from networkmapper.discovery.nmap_provider import NmapProvider
from networkmapper.project.models import Project
from networkmapper.project.serializer import ProjectSerializer
from networkmapper.exporters.csv_exporter import CsvExporter
from networkmapper.exporters.markdown_exporter import MarkdownExporter


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
        print("\nClassification Summary")
        print("-" * 40)

        classification_counts = {}

        for device in graph.all_devices():
            device_type = device.device_type.name

            if device_type not in classification_counts:
                classification_counts[device_type] = 0

            classification_counts[device_type] += 1

        for device_type in sorted(classification_counts):
            print(f"{device_type:<15} {classification_counts[device_type]}")

        print("\nSample Classifications")
        print("-" * 80)
        print(f"{'IP Address':<16} {'Hostname':<30} {'Vendor':<20} {'Type'}")

        for device in list(graph.all_devices())[:20]:
            print(
                f"{device.ip_address:<16} "
                f"{(device.hostname or 'Unknown'):<30} "
                f"{(device.vendor or 'Unknown'):<20} "
                f"{device.device_type.name}"
            )

        print()

        project = Project(
            customer_name="Test Network",
            network_graph=graph,
        )

        CsvExporter().export(
            project,
            "output/Test Network.csv",
        )

        MarkdownExporter().export(
            project,
            "output/Test Network.md"
        )

        print("✓ CSV exported to output/Test Network.csv")
        print("✓ Markdown exported to output/Test Network.md")

        ProjectSerializer.save(project, "output/Test Network.nmproj")

        loaded_project = ProjectSerializer.load(
            "output/Test Network.nmproj"
        )

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