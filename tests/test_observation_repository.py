import tempfile
import unittest
from pathlib import Path

from networkmapper.knowledge.models import (
    Observation,
    ObservationClassification,
    ObservationDevice,
    ObservationEvidence,
    ObservationNetwork,
    ObservationScan,
)
from networkmapper.knowledge.repository import ObservationNotFoundError, ObservationRepository


def _build_observation(observation_id: int) -> Observation:
    return Observation(
        observation_id=observation_id,
        captured_at="2026-07-18T09:42:11",
        network=ObservationNetwork(name="Riverside Manufacturing"),
        scan=ObservationScan(profile="standard"),
        device=ObservationDevice(ip="192.168.10.55", vendor="APC"),
        evidence=ObservationEvidence(),
        classification=ObservationClassification(type="unknown", reason="No rule matched."),
    )


class ObservationRepositoryTest(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.repository = ObservationRepository(root=Path(self._temp_dir.name) / "observations")

    def test_next_observation_id_starts_at_one_for_an_empty_repository(self):
        self.assertEqual(self.repository.next_observation_id(), 1)

    def test_save_and_load_round_trips_an_observation(self):
        observation = _build_observation(1)

        self.repository.save(observation)
        loaded = self.repository.load(1)

        self.assertEqual(loaded, observation)

    def test_next_observation_id_increments_after_a_save(self):
        self.repository.save(_build_observation(1))

        self.assertEqual(self.repository.next_observation_id(), 2)

    def test_next_observation_id_never_reuses_a_gap(self):
        """IDs stay stable even if an earlier observation is later removed —
        the filename must remain valid regardless of review outcome, so IDs
        are never recycled."""
        self.repository.save(_build_observation(1))
        self.repository.save(_build_observation(2))
        self.repository.path_for(1).unlink()

        self.assertEqual(self.repository.next_observation_id(), 3)

    def test_filename_does_not_encode_vendor_hostname_ip_or_device_type(self):
        observation = _build_observation(1)

        path = self.repository.save(observation)

        self.assertEqual(path.name, "observation-000001.json")
        self.assertNotIn("APC", path.name)
        self.assertNotIn("192.168.10.55", path.name)
        self.assertNotIn("unknown", path.name)

    def test_filenames_are_stable_six_digit_sequential_ids(self):
        for observation_id in (1, 2, 3):
            self.repository.save(_build_observation(observation_id))

        self.assertEqual(
            self.repository.list_observation_ids(),
            (1, 2, 3),
        )
        for observation_id in (1, 2, 3):
            self.assertTrue(self.repository.path_for(observation_id).is_file())

    def test_load_missing_observation_raises(self):
        with self.assertRaises(ObservationNotFoundError):
            self.repository.load(999)

    def test_list_observation_ids_is_empty_for_a_repository_that_does_not_exist_yet(self):
        self.assertEqual(self.repository.list_observation_ids(), ())


class ShippedSampleObservationTest(unittest.TestCase):
    """Validates the real, committed sample observation (KNOW-003 Deliverable:
    Sample Observation) rather than a synthetic fixture, so a future schema
    change that breaks the shipped example is caught here."""

    def test_sample_observation_loads_and_remains_unknown(self):
        repository = ObservationRepository(root=Path("knowledge/observations"))

        observation = repository.load(1)

        self.assertEqual(observation.classification.type, "unknown")
        self.assertEqual(observation.classification.reason, "No rule matched.")
        self.assertEqual(observation.device.vendor, "APC")
        self.assertGreaterEqual(len(observation.evidence.services), 2)


if __name__ == "__main__":
    unittest.main()
