from base64 import b64decode
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from pydantic import ValidationError

from dropsy.core.audit import build_snapshot, sample_audit
from dropsy.core.casebook import CaseInput, MaterialInput, add_material, create_case, list_cases, read_case, read_image
from dropsy.core.history import read_snapshot

PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg=="


class TestCasebook(TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        setting = patch.dict("os.environ", {"DROPSY_HISTORY_DB": str(Path(folder.name) / "dropsy.sqlite")})
        setting.start()
        self.addCleanup(setting.stop)
        self.case = create_case(CaseInput(title="A case"))

    def test_books_links_and_notes_without_running_audit(self):
        identifier = self.case["id"]
        link = add_material(identifier, MaterialInput(
            kind="link", title="Store", source_url="https://example.org/products?q=example",
            observed_on="2026-10-11",
        ))
        note = add_material(identifier, MaterialInput(kind="note", title="Observation", note="Same banner on two pages"))
        case = read_case(identifier)
        self.assertEqual([note["id"], link["id"]], [item["id"] for item in case["materials"]])
        self.assertEqual(case["materials"][1]["observed_on"], "2026-10-11")
        self.assertEqual(list_cases()[0]["material_count"], 2)

    def test_screenshot_is_scoped_to_case_and_kept_out_of_metadata(self):
        identifier = self.case["id"]
        item = add_material(identifier, MaterialInput(kind="image", title="Screenshot", image_base64=PNG))
        content, mime = read_image(identifier, item["id"])
        self.assertEqual((content, mime), (b64decode(PNG), "image/png"))
        self.assertEqual(item["image_sha256"], sha256(content).hexdigest())
        self.assertNotIn("image_data", read_case(identifier)["materials"][0])
        self.assertIsNone(read_image("0" * 32, item["id"]))

    def test_snapshot_is_saved_once_per_case_and_reopens_in_audit(self):
        identifier = self.case["id"]
        fixture = sample_audit("current")
        fixture["source"] = "observed"
        snapshot = build_snapshot(fixture)
        data = MaterialInput(kind="snapshot", title=snapshot.scope, snapshot=snapshot)
        item = add_material(identifier, data)
        self.assertEqual(item, add_material(identifier, data))
        self.assertEqual(item["source_url"], snapshot.scope)
        self.assertTrue(item["snapshot_at"])
        self.assertEqual(read_snapshot(snapshot.fingerprint), snapshot)

    def test_invalid_material_is_rejected(self):
        with self.assertRaises(ValidationError):
            MaterialInput(kind="link", title="Unsafe", source_url="javascript:alert(1)")
        with self.assertRaises(ValueError):
            add_material(self.case["id"], MaterialInput(kind="image", title="Invalid", image_base64="PGh0bWw+"))
        with self.assertRaises(ValueError):
            add_material(self.case["id"], MaterialInput(kind="snapshot", title="Example", snapshot=sample_audit("current")["snapshot"]))
        self.assertEqual(read_case(self.case["id"])["materials"], [])
