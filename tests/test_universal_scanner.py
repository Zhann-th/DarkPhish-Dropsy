import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from dropsy.core.universal_scanner import UniversalOSINTScanner


class TestUniversalScanner(TestCase):
    def test_rejects_bad_targets(self):
        scanner = UniversalOSINTScanner()
        for target in ('', '/not/a/real/directory', 'https://user:password@example.com/',
                       'file:///etc/passwd', 'javascript:alert(1)', 'a domain.com'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                scanner.scan(target)

    def test_rejects_private_network(self):
        scanner = UniversalOSINTScanner()
        with self.assertRaises(ValueError):
            scanner.scan('127.0.0.1')
        with self.assertRaises(ValueError):
            scanner.scan('192.168.1.1')

    def test_host_with_public_and_internal_dns_answers_is_blocked(self):
        records = [(2, 1, 6, "", (address, 0)) for address in ("1.1.1.1", "192.168.1.1")]
        with patch("socket.getaddrinfo", return_value=records), \
             patch.object(UniversalOSINTScanner, "_safe_fetch") as fetch:
            with self.assertRaises(ValueError):
                UniversalOSINTScanner().scan_web("https://example.org")
            fetch.assert_not_called()

    def test_international_hostname_and_path_are_normalized(self):
        host, origin, url = UniversalOSINTScanner.parse_web_target("https://пример.рф/тест?q=one")
        self.assertEqual(host, "xn--e1afmkfd.xn--p1ai")
        self.assertEqual(origin, "https://xn--e1afmkfd.xn--p1ai")
        self.assertEqual(url, origin + "/%D1%82%D0%B5%D1%81%D1%82")

    def test_local_tree_no_fake_person(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'src').mkdir()
            (root / 'src' / 'main.py').write_text('API_URL="https://api.example.com"\ncontact="team@example.org"')
            (root / '.venv').mkdir()
            (root / '.venv' / 'private.txt').write_text('hidden@secret.example')
            (root / 'outside_link').symlink_to('/etc/passwd')
            data = UniversalOSINTScanner().scan(tmp)
            names = {entity['name'] for entity in data['graph']['entities']}
            types = {entity['entity_type'] for entity in data['graph']['entities']}
            self.assertIn('main.py', names)
            self.assertIn('src', names)
            self.assertEqual(data['files_scanned'], 1)
            self.assertIn('team@example.org', data['emails_discovered'])
            self.assertNotIn('PERSON', types)
            self.assertIsNone(data['confidence'])
            self.assertFalse(data['optimal_path']['path_found'])

    def test_live_site_links_and_dns_edges_without_fake_identity(self):
        scanner = UniversalOSINTScanner(max_pages=3)
        def fake_fetch(url, host, ip, max_bytes=65536):
            html = '<title>Home</title><a href="/about">About</a><a href="https://other.test/">External</a>' if url.endswith('/') else '<title>About</title><a href="/">Home</a>'
            return {'status': 200, 'content_type': 'text/html', 'body': html.encode(), 'truncated': False, 'server': ''}
        with patch.object(scanner, '_resolve', return_value=['1.1.1.1']), \
             patch.object(scanner, '_safe_fetch', side_effect=fake_fetch):
            data = scanner.scan('https://example.com/')
        self.assertEqual(len(data['pages']), 2)
        self.assertTrue(data['optimal_path']['path_found'])
        self.assertEqual(len([e for e in data['graph']['entities'] if e['entity_type'] == 'PAGE']), 2)
        self.assertTrue(any(e['relationship'] == 'LINKS_TO' for e in data['graph']['links']))
        self.assertFalse(any(e['entity_type'] == 'PERSON' for e in data['graph']['entities']))
        self.assertEqual(data['open_ports'], [])
        self.assertIsNone(data['confidence'])

    def test_bounds_on_file_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(10):
                (Path(tmp) / f'{i}.txt').write_text('hello')
            result = UniversalOSINTScanner(max_files=3).scan(tmp)
            self.assertEqual(result['files_scanned'], 3)
            self.assertTrue(result['errors'])
