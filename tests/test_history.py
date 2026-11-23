from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from dropsy.core.audit import build_snapshot, compare_snapshots, sample_audit
from dropsy.core.history import list_assets, list_snapshots, read_snapshot, save_snapshot


class TestHistory(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        settings = patch.dict("os.environ", {"DROPSY_HISTORY_DB": str(Path(temporary.name) / "history.sqlite")})
        settings.start()
        self.addCleanup(settings.stop)

    def observed(self, variant, captured_at):
        data = sample_audit(variant)
        data["source"] = "observed"
        return build_snapshot(data, captured_at=captured_at)

    def test_persist_and_compare_saved_versions(self):
        early = self.observed("baseline", datetime(2026, 10, 15, 8, tzinfo=UTC))
        late = self.observed("current", datetime(2026, 10, 15, 10, tzinfo=timezone(timedelta(hours=1))))
        self.assertTrue(save_snapshot(late))
        self.assertTrue(save_snapshot(early))
        self.assertFalse(save_snapshot(early))
        self.assertEqual(list_assets()[0]["snapshot_count"], 2)
        self.assertEqual([row["fingerprint"] for row in list_snapshots(early.scope, early.mode)["snapshots"]],
                         [late.fingerprint, early.fingerprint])
        self.assertEqual(compare_snapshots(read_snapshot(early.fingerprint), read_snapshot(late.fingerprint))["summary"],
                         {"added": 3, "changed": 2, "missing": 1})
        self.assertIsNone(read_snapshot("0" * 64))
        self.assertEqual(list_snapshots(early.scope, "directory")["snapshots"], [])

    def test_rejects_synthetic_and_invalid_history(self):
        sample = sample_audit("baseline")["snapshot"]
        with self.assertRaisesRegex(ValueError, "Учебные"):
            save_snapshot(sample)
        sample.source = "observed"
        with self.assertRaisesRegex(ValueError, "Контрольная сумма"):
            save_snapshot(sample)
        self.assertEqual(list_assets(), [])

    def test_recovered_sample_shows_repair(self):
        broken = sample_audit("current")["snapshot"]
        recovered = sample_audit("recovered")["snapshot"]
        diff = compare_snapshots(broken, recovered)
        self.assertEqual(diff["summary"], {"added": 0, "changed": 2, "missing": 0})
        repair = next(row for row in diff["changes"] if row["key"].endswith("/help"))
        self.assertEqual((repair["before"]["status"], repair["after"]["status"]), (404, 200))
