from abc import ABC, abstractmethod

from networkmapper.core.models import Device


class DiscoveryProvider(ABC):
    """
    Base class for all network discovery providers.

    Discovery providers are responsible for collecting information
    from a specific source (Nmap, SNMP, LLDP, etc.) and returning
    Device objects to the DiscoveryEngine.
    """

    @abstractmethod
    def discover(self) -> list[Device]:
        """Return discovered devices."""
        raise NotImplementedError