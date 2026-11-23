from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi import HTTPException

from dropsy.api.server import UniversalScanRequest, audit_config, run_universal_scan
from dropsy.core.audit import Snapshot, build_snapshot, compare_snapshots, sample_audit
from dropsy.core.universal_scanner import UniversalOSINTScanner


class TestAuditSnapshots(TestCase):
    def setUp(self):
        self.baseline = sample_audit("baseline")["snapshot"]
        self.current = sample_audit("current")["snapshot"]

    def test_roundtrip_and_comparison(self):
        current = Snapshot.model_validate_json(self.current.model_dump_json())
        comparison = compare_snapshots(self.baseline, current)
        self.assertEqual(comparison["summary"], {"added": 3, "changed": 2, "missing": 1})
        self.assertFalse(comparison["partial"])
        page = next(x for x in comparison["changes"] if x["state"] == "changed" and x["key"].endswith("/help"))
        self.assertEqual((page["before"]["status"], page["after"]["status"]), (200, 404))

    def test_integrity_rejects_modified_snapshot(self):
        modified = deepcopy(self.current)
        modified.records[0].fields["address"] = "192.0.2.99"
        with self.assertRaisesRegex(ValueError, "Контрольная сумма"):
            compare_snapshots(self.baseline, modified)

    def test_comparison_preserves_scope_and_provenance(self):
        data = sample_audit("current")
        data["source"] = "observed"
        with self.assertRaisesRegex(ValueError, "одинаковую область"):
            compare_snapshots(self.baseline, build_snapshot(data))

    def test_partial_collection_is_carried_into_diff(self):
        data = sample_audit("current")
        data["limit_reached"] = True
        current = build_snapshot(data)
        self.assertTrue(current.partial)
        self.assertTrue(compare_snapshots(self.baseline, current)["partial"])


class TestAuditAccess(TestCase):
    def test_explicit_origin_list_still_restricts_web_audit(self):
        with patch.dict("os.environ", {"DROPSY_AUDIT_ORIGINS": "https://owned.example"}), \
             patch.object(UniversalOSINTScanner, "scan_web") as scan:
            with self.assertRaises(HTTPException) as raised:
                run_universal_scan(UniversalScanRequest(target="http://owned.example/"))
            self.assertEqual(raised.exception.status_code, 403)
            self.assertEqual(audit_config()["web_mode"], "restricted")
            scan.assert_not_called()

    def test_invalid_explicit_origin_list_does_not_enable_public_mode(self):
        with patch.dict("os.environ", {"DROPSY_AUDIT_ORIGINS": "not an origin"}):
            config = audit_config()
            self.assertEqual(config["web_mode"], "restricted")
            self.assertEqual(config["origins"], [])
            with self.assertRaises(HTTPException) as raised:
                run_universal_scan(UniversalScanRequest(target="https://example.org"))
            self.assertEqual(raised.exception.status_code, 403)

    def test_local_inventory_returns_hash_and_no_file_contents(self):
        with TemporaryDirectory() as tmp, patch.dict("os.environ", {"DROPSY_SCAN_ROOT": tmp}):
            root = Path(tmp)
            folder = root / "docs"
            folder.mkdir()
            (folder / "note.md").write_text("Example artifact", encoding="utf-8")
            response = run_universal_scan(UniversalScanRequest(target="./docs"))
            self.assertEqual(response["snapshot"].scope, "directory:docs")
            record = response["snapshot"].records[0]
            self.assertEqual(record.fields["sample_bytes"], 16)
            self.assertEqual(len(record.fields["sha256"]), 64)
            self.assertNotIn("code", response["files_data"]["note.md"])

    def test_local_inventory_disabled_without_config(self):
        with patch.dict("os.environ", {"DROPSY_SCAN_ROOT": ""}):
            with self.assertRaises(HTTPException) as raised:
                run_universal_scan(UniversalScanRequest(target="  ./  "))
            self.assertEqual(raised.exception.status_code, 403)

    def test_web_collection_keeps_observations_on_exact_origin(self):
        fetched = []
        def fake_fetch(url, host, ip, max_bytes=65536):
            fetched.append((url, ip))
            return {
                "status": 200, "content_type": "text/html", "truncated": False, "headers": {},
                "body": b'<a href="/about">About</a><a href="http://owned.example">HTTP</a>'
                        b'<a href="https://other.example">Offsite</a><a href="/search?q=secret">Query</a>',
            }
        with patch.dict("os.environ", {}, clear=True), \
             patch.object(UniversalOSINTScanner, "_resolve", return_value=["192.0.2.10"]) as resolve, \
             patch.object(UniversalOSINTScanner, "_safe_fetch", side_effect=fake_fetch):
            self.assertEqual(audit_config()["web_mode"], "public")
            response = run_universal_scan(UniversalScanRequest(target="https://owned.example"))
        resolve.assert_called_once_with("owned.example")
        self.assertEqual(fetched, [("https://owned.example/", "192.0.2.10"), ("https://owned.example/about", "192.0.2.10")])
        self.assertEqual(response["snapshot"].source, "observed")
        self.assertEqual(response["confidence"], None)
