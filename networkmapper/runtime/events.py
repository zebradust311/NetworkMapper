from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RuntimePhase(StrEnum):
    """OBS-002's minimum supported set of runtime phases.

    Ordered as they occur in a normal run, so anything iterating
    `RuntimePhase` (e.g. a future GUI's fixed progress checklist) sees
    them in execution order.
    """

    APPLICATION_STARTUP = "Application Startup"
    HOST_DISCOVERY = "Host Discovery"
    SERVICE_ENRICHMENT = "Service Enrichment"
    CLASSIFICATION = "Classification"
    REPORT_GENERATION = "Report Generation"
    COMPLETION = "Completion"


class RuntimeEventKind(StrEnum):
    """What a RuntimeEvent represents about its phase."""

    PHASE_STARTED = "phase_started"
    PROGRESS = "progress"
    PHASE_COMPLETED = "phase_completed"


@dataclass(frozen=True)
class ProgressMeasurement:
    """A directly observed, measurable count — never an estimate.

    OBS-002 explicitly excludes guessed percentages and ETAs: `total` is
    only ever set when genuinely known in advance (e.g. the number of
    hosts entering Service Enrichment, already fixed by Host Discovery's
    result). It is left `None` when not knowable ahead of time (e.g. Host
    Discovery doesn't know how many hosts it will find until it finishes),
    so a consumer can render a bare count instead of a fraction rather
    than being handed a fabricated denominator.

    Attributes:
        completed: The number of units (hosts, devices, ...) completed
            so far.
        total: The known total, if any.
        unit_label: A human-readable label for what's being counted
            (e.g. "Hosts Found", "Hosts Completed", "Devices
            Classified"), supplied by the phase that knows what it's
            counting rather than guessed from the phase name by
            whichever component renders the event.
    """

    completed: int
    unit_label: str
    total: int | None = None


@dataclass(frozen=True)
class RuntimeEvent:
    """One runtime status event for a single phase.

    Carries only directly observed, measurable state. Producers
    (discovery, classification, report generation) publish these;
    consumers (the CLI today, a future GUI tomorrow) subscribe to the
    same stream without discovery logic changing to accommodate a new
    consumer.
    """

    phase: RuntimePhase
    kind: RuntimeEventKind
    timestamp: datetime
    activity: str | None = None
    progress: ProgressMeasurement | None = None


RuntimeEventSubscriber = Callable[[RuntimeEvent], None]


class RuntimeEventBus:
    """Publishes runtime events to any number of subscribers.

    Decouples event producers from consumers: a producer only ever calls
    `publish()` and never knows or cares who (if anyone) is listening.
    Publishing to a bus with zero subscribers — the default when no
    caller wires one up — is a safe no-op, so every producer can depend
    on a bus unconditionally rather than null-checking an optional one at
    every call site.
    """

    def __init__(self) -> None:
        """Initialize a bus with no subscribers."""
        self._subscribers: list[RuntimeEventSubscriber] = []

    def subscribe(self, subscriber: RuntimeEventSubscriber) -> None:
        """Register a subscriber to receive every subsequently published event."""
        self._subscribers.append(subscriber)

    def publish(self, event: RuntimeEvent) -> None:
        """Send an event to every current subscriber, in subscription order."""
        for subscriber in self._subscribers:
            subscriber(event)
