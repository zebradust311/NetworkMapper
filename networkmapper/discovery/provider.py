from abc import ABC, abstractmethod

from networkmapper.core.models import Device
from networkmapper.observations.models import IdentityObservation, RelationshipObservation


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

    def collect_observations(self) -> list[IdentityObservation | RelationshipObservation]:
        """Return retained observations gathered during the most recent discover() call.

        FEAT-007A/ARCH-017 Stage 2: additive and optional. The default
        implementation returns an empty list, so every existing and
        future `DiscoveryProvider` that does not override this method
        remains fully valid without any change — the same "safe no-op
        when nothing is wired up" pattern already proven for
        `RuntimeEventBus` (OBS-002). Never influences `discover()`'s own
        return value or any Device it produces.
        """
        return []