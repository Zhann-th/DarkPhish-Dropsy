from base64 import b64encode
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from dropsy.core.darkphish_mail import analyze_mail
from dropsy.core.universal_scanner import UniversalOSINTScanner

EXAMPLES = Path(__file__).resolve().parents[1] / "docs/darkphish/examples"


class MailAnalysisTests(TestCase):
    def fixture(self, name):
        return b64encode((EXAMPLES / f"{name}.eml").read_bytes()).decode()

    def test_example_inputs_and_hidden_link(self):
        with patch.object(UniversalOSINTScanner, "_resolve") as resolver:
            ordinary = analyze_mail(encoded=self.fixture("ordinary"), expected_domain="service.example")
            suspicious = analyze_mail(encoded=self.fixture("suspicious"), expected_domain="service.example")
        resolver.assert_not_called()
        self.assertEqual(ordinary["review_reason"], "insufficient evidence")
        self.assertEqual(ordinary["links"][0]["score"], None)
        self.assertEqual(suspicious["links"][0]["input"], "https://account-review.example/verify")
        self.assertEqual(len(suspicious["links"]), 2)
        self.assertAlmostEqual(suspicious["belief"]["posterior"], .81987891)
        self.assertEqual(suspicious["decision"]["recommended"], "Escalate to incident team")

    def test_relative_redirect_and_query(self):
        responses = [{"status": 302, "location": "/done?flow=example"},
                     {"status": 200, "location": None}]
        with patch.object(UniversalOSINTScanner, "_resolve", return_value=["1.1.1.1"]) as resolve:
            with patch.object(UniversalOSINTScanner, "_safe_fetch", side_effect=responses) as fetch:
                result = analyze_mail(url="https://service.example/start?a=b#anchor", resolve=True)
        self.assertEqual(resolve.call_count, 2)
        self.assertEqual(fetch.call_args_list[0].args[0], "https://service.example/start?a=b")
        self.assertTrue(fetch.call_args.kwargs["headers_only"])
        self.assertEqual(result["links"][0]["final"], "https://service.example/done?flow=example")
        self.assertEqual([hop["status"] for hop in result["links"][0]["hops"]], [302, 200])

    def test_redirect_to_internal_address_is_not_fetched(self):
        answers = [[(0, 0, 0, "", ("1.1.1.1", 0))], [(0, 0, 0, "", ("127.0.0.1", 0))]]
        with patch("socket.getaddrinfo", side_effect=answers):
            with patch.object(UniversalOSINTScanner, "_safe_fetch", return_value={
                "status": 302, "location": "http://127.0.0.1/"
            }) as fetch:
                result = analyze_mail(url="https://service.example/start", resolve=True)
        self.assertEqual(fetch.call_count, 1)
        self.assertIsNone(result["links"][0]["final"])

    def test_unsupported_method_result_never_confirms_destination(self):
        with patch.object(UniversalOSINTScanner, "_resolve", return_value=["1.1.1.1"]):
            with patch.object(UniversalOSINTScanner, "_safe_fetch", return_value={"status": 405, "location": None}):
                result = analyze_mail(url="https://service.example/", resolve=True)
        self.assertIsNone(result["links"][0]["final"])
        self.assertIn("405", result["links"][0]["state"])
