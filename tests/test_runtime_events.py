import unittest
from datetime import datetime

from networkmapper.runtime.events import (
    ProgressMeasurement,
    RuntimeEvent,
    RuntimeEventBus,
    RuntimeEventKind,
    RuntimePhase,
)


class RuntimeEventBusTest(unittest.TestCase):
    def test_publish_with_no_subscribers_does_not_raise(self):
        bus = RuntimeEventBus()

        bus.publish(
            RuntimeEvent(
                phase=RuntimePhase.HOST_DISCOVERY,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime.now(),
            )
        )

    def test_single_subscriber_receives_published_event(self):
        bus = RuntimeEventBus()
        received: list[RuntimeEvent] = []
        bus.subscribe(received.append)

        event = RuntimeEvent(
            phase=RuntimePhase.HOST_DISCOVERY,
            kind=RuntimeEventKind.PHASE_STARTED,
            timestamp=datetime.now(),
            activity="Scanning...",
        )
        bus.publish(event)

        self.assertEqual(received, [event])

    def test_multiple_subscribers_all_receive_every_event(self):
        bus = RuntimeEventBus()
        first_received: list[RuntimeEvent] = []
        second_received: list[RuntimeEvent] = []
        bus.subscribe(first_received.append)
        bus.subscribe(second_received.append)

        event = RuntimeEvent(
            phase=RuntimePhase.CLASSIFICATION,
            kind=RuntimeEventKind.PHASE_COMPLETED,
            timestamp=datetime.now(),
        )
        bus.publish(event)

        self.assertEqual(first_received, [event])
        self.assertEqual(second_received, [event])

    def test_subscribers_receive_events_in_publish_order(self):
        bus = RuntimeEventBus()
        received: list[RuntimeEventKind] = []
        bus.subscribe(lambda event: received.append(event.kind))

        bus.publish(
            RuntimeEvent(
                phase=RuntimePhase.HOST_DISCOVERY,
                kind=RuntimeEventKind.PHASE_STARTED,
                timestamp=datetime.now(),
            )
        )
        bus.publish(
            RuntimeEvent(
                phase=RuntimePhase.HOST_DISCOVERY,
                kind=RuntimeEventKind.PHASE_COMPLETED,
                timestamp=datetime.now(),
            )
        )

        self.assertEqual(
            received, [RuntimeEventKind.PHASE_STARTED, RuntimeEventKind.PHASE_COMPLETED]
        )


class ProgressMeasurementTest(unittest.TestCase):
    def test_total_defaults_to_none_when_not_supplied(self):
        progress = ProgressMeasurement(completed=5, unit_label="Hosts Found")

        self.assertIsNone(progress.total)

    def test_total_can_be_supplied_when_known(self):
        progress = ProgressMeasurement(completed=5, unit_label="Hosts Completed", total=10)

        self.assertEqual(progress.total, 10)


if __name__ == "__main__":
    unittest.main()
