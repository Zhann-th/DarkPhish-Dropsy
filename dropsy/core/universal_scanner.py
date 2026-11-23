"""Bounded HTTP and filesystem observations for the Dropsy audit workbench."""
from __future__ import annotations

from codecs import getincrementaldecoder
from collections import deque
from hashlib import sha256
from html.parser import HTMLParser
import http.client
import ipaddress
import os
from pathlib import Path
import re
import socket
import ssl
from time import monotonic
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from .entity_graph import OsintEntity, OsintKnowledgeGraph, OsintLink
from .search_engine import OsintPathSearchEngine


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.title = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        if tag == "a" and len(self.links) < 150:
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)


class UniversalOSINTScanner:
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b")
    DOMAIN_REGEX = re.compile(r"(?<![\w.-])(?:[A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,24}\b")
    SKIP_DIRS = {"node_modules", "venv", "__pycache__", "dist", "build", "vendor"}
    SKIP_NAMES = {"credentials.json", "id_rsa", "id_ed25519"}
    TEXT_EXTS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md", ".txt",
        ".xml", ".csv", ".go", ".rs", ".java", ".c", ".h", ".cpp", ".sql", ".rb", ".php",
    }
    RESPONSE_HEADERS = {
        "strict-transport-security", "content-security-policy", "x-frame-options",
        "x-content-type-options", "referrer-policy", "permissions-policy", "content-type",
    }

    def __init__(self, timeout: float = 2.0, max_pages: int = 20, max_files: int = 1000):
        self.timeout = max(0.1, min(float(timeout), 5))
        self.max_pages = max(1, min(int(max_pages), 40))
        self.max_files = max(1, min(int(max_files), 1000))

    @staticmethod
    def parse_web_target(target):
        if not target or len(target) > 2048 or any(c.isspace() or ord(c) < 32 for c in target) or "\\" in target:
            raise ValueError("Invalid target URL")
        parts = urlsplit(target if "://" in target else "https://" + target)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username is not None:
            raise ValueError("Only HTTP(S) URLs without credentials are supported")
        port = 443 if parts.scheme == "https" else 80
        if parts.port not in (None, port):
            raise ValueError("Use the standard port for HTTP or HTTPS")
        host = parts.hostname.lower().rstrip(".")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            try:
                host = host.encode("idna").decode("ascii").rstrip(".")
            except UnicodeError as exc:
                raise ValueError("Invalid domain name") from exc
            if len(host) > 253 or "." not in host or any(
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in host.split(".")
            ):
                raise ValueError("Invalid domain name")
        authority = f"[{host}]" if ":" in host else host
        origin = f"{parts.scheme}://{authority}"
        path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
        return host, origin, origin + path

    @staticmethod
    def _path_key(target):
        return urlsplit(target).path or "/"

    @staticmethod
    def _node_id(kind, value):
        return kind.lower() + "_" + sha256(str(value).encode()).hexdigest()[:20]

    def _resolve(self, host):
        addresses = sorted({row[4][0] for row in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})
        if not addresses:
            raise ValueError("No DNS results")
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if isinstance(ip, ipaddress.IPv6Address):
                if ip.ipv4_mapped or ip.sixtofour or ip.teredo or ip.scope_id:
                    raise ValueError("Для аудита доступны только публичные IP-адреса.")
            if not ip.is_global or ip.is_multicast or ip.is_reserved:
                raise ValueError("Для аудита доступны только публичные IP-адреса.")
        return addresses[:20]

    def _safe_fetch(self, url, host, ip, max_bytes=65536):
        parts = urlsplit(url)
        port = 443 if parts.scheme == "https" else 80
        certificate = None
        if parts.scheme == "https":
            class PinnedHTTPS(http.client.HTTPSConnection):
                def connect(self):
                    sock = socket.create_connection((ip, port), timeout=self.timeout)
                    try:
                        self.sock = self._context.wrap_socket(sock, server_hostname=host)
                    except BaseException:
                        sock.close()
                        raise

            conn = PinnedHTTPS(host, port, timeout=self.timeout, context=ssl.create_default_context())
        else:
            conn = http.client.HTTPConnection(ip, port, timeout=self.timeout)
        try:
            conn.connect()
            if parts.scheme == "https":
                cert = conn.sock.getpeercert()
                issuer = {
                    key: value for rdn in cert.get("issuer", ()) for key, value in rdn
                }
                certificate = {
                    "subject": host,
                    "issuer": issuer.get("organizationName", issuer.get("commonName")),
                    "not_after": cert.get("notAfter"),
                    "not_before": cert.get("notBefore"),
                    "fingerprint_sha256": sha256(conn.sock.getpeercert(binary_form=True)).hexdigest(),
                    "tls_version": conn.sock.version(),
                    "cipher": conn.sock.cipher()[0],
                    "verified": True,
                }
            conn.request("GET", parts.path or "/", headers={
                "Host": parts.netloc, "User-Agent": "Dropsy/4.0 web asset audit",
                "Accept": "text/html,application/xhtml+xml", "Connection": "close",
            })
            response = conn.getresponse()
            headers = {
                key.lower(): value[:1024] for key, value in response.getheaders()
                if key.lower() in self.RESPONSE_HEADERS
            }
            mime = response.getheader("Content-Type", "").split(";", 1)[0].lower()
            body = response.read(max_bytes + 1) if "html" in mime else b""
            return {
                "status": response.status, "content_type": mime, "headers": headers,
                "body": body[:max_bytes], "truncated": len(body) > max_bytes,
                "certificate": certificate,
            }
        finally:
            conn.close()

    def scan(self, target):
        target = target.strip()
        if not target:
            raise ValueError("Target cannot be empty")
        if len(target) > 2048 or "\0" in target:
            raise ValueError("Invalid target")
        path = Path(target).expanduser()
        if "://" not in target and path.is_dir():
            return self.scan_directory(path)
        if target.startswith(("/", "./", "../", "~")):
            raise ValueError("Local directory not found")
        return self.scan_web(target)

    def scan_web(self, target):
        host, origin, starting_url = self.parse_web_target(target)
        result = {
            "target": host, "scope": starting_url, "target_type": "REMOTE_NETWORK",
            "source": "observed", "resolved_ips": [], "ssl_info": None, "pages": [],
            "page_links": [], "errors": [], "limit_reached": False, "confidence": None,
            "open_ports": [], "confidence_note": "Infrastructure observations do not establish an identity.",
        }
        try:
            result["resolved_ips"] = self._resolve(host)
        except OSError as exc:
            result["errors"].append(f"DNS: {type(exc).__name__}")
        if result["resolved_ips"]:
            self._crawl(result, starting_url, origin, host, result["resolved_ips"][0])
        result["target_response"] = result["pages"][0] if result["pages"] and result["pages"][0]["url"] == starting_url else None
        self._attach_web_graph(result)
        return result

    def _crawl(self, result, starting_url, origin, host, ip):
        queue = deque([starting_url])
        scheduled = {starting_url}
        observed_edges = set()
        deadline = monotonic() + 15
        attempts = 0
        while queue and attempts < self.max_pages and monotonic() < deadline:
            url = queue.popleft()
            attempts += 1
            try:
                response = self._safe_fetch(url, host, ip)
                if response.get("certificate"):
                    result["ssl_info"] = result["ssl_info"] or response["certificate"]
                parser = _PageParser()
                if response["status"] < 300 and "html" in response["content_type"]:
                    parser.feed(response["body"].decode("utf-8", errors="replace"))
                result["pages"].append({
                    "url": url, "path": self._path_key(url), "status": response["status"],
                    "title": " ".join(" ".join(parser.title).split())[:160],
                    "content_type": response["content_type"], "headers": response.get("headers", {}),
                    "size": len(response["body"]), "truncated": response["truncated"],
                })
                for href in parser.links:
                    try:
                        parsed = urlsplit(urljoin(url, href))
                        if parsed.query:
                            continue
                        _, candidate_origin, candidate = self.parse_web_target(parsed.geturl())
                    except ValueError:
                        continue
                    if candidate_origin != origin or candidate == url:
                        continue
                    observed_edges.add((url, candidate))
                    if candidate not in scheduled:
                        queue.append(candidate)
                        scheduled.add(candidate)
            except (OSError, ValueError, http.client.HTTPException) as exc:
                result["errors"].append(f"{url}: {type(exc).__name__}")
        result["limit_reached"] = bool(queue)
        page_urls = {page["url"] for page in result["pages"]}
        result["page_links"] = [
            {"source": start, "target": end} for start, end in sorted(observed_edges)
            if start in page_urls and end in page_urls
        ]

    def _attach_web_graph(self, result):
        graph = OsintKnowledgeGraph()
        root = self._node_id("DOMAIN", result["target"])
        graph.add_entity(OsintEntity(root, result["target"], "DOMAIN", 0, 1, details={"source": result["source"]}))
        for ip in result["resolved_ips"]:
            self._graph_child(graph, root, "IP_ADDRESS", ip, ip, "RESOLVES_TO", "DNS", 1)
        if cert := result["ssl_info"]:
            self._graph_child(graph, root, "SSL_CERT", cert["fingerprint_sha256"], cert.get("issuer") or "TLS", "PRESENTS_CERT", "TLS", 1)
        urls = {}
        for page in result["pages"]:
            node = self._node_id("PAGE", page["url"])
            urls[page["url"]] = node
            graph.add_entity(OsintEntity(node, page["title"] or page["path"], "PAGE", 2, 1, details={"url": page["url"], "status": str(page["status"])}))
        if urls:
            graph.add_link(OsintLink(root, next(iter(urls.values())), "HAS_PAGE", 1, "HTTP"))
        for edge in result["page_links"]:
            graph.add_link(OsintLink(urls[edge["source"]], urls[edge["target"]], "LINKS_TO", 1, "HTML anchor"))
        if result["source"] != "observed":
            for link in graph.links:
                link.source_record = "Synthetic example"
                link.verified = False
        result["graph"] = graph.to_dict()
        result["evidence_count"] = len(result["resolved_ips"]) + bool(result["ssl_info"]) + len(urls)
        result["optimal_path"] = OsintPathSearchEngine(graph).dijkstra_search(root, list(urls.values())[-1]).to_dict() if urls else None

    def _graph_child(self, graph, parent, kind, value, title, relation, source, tier):
        node = self._node_id(kind, value)
        if node not in graph.entities:
            graph.add_entity(OsintEntity(node, title, kind, tier, 1))
            graph.add_link(OsintLink(parent, node, relation, 1, source))
        return node

    def scan_directory(self, path):
        root = Path(path).resolve(strict=True)
        files_data = {}
        emails, domains = set(), set()
        errors = []
        deadline = monotonic() + 12
        visited = 0
        for current, dirs, files in os.walk(root, followlinks=False, onerror=lambda exc: errors.append(type(exc).__name__)):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in self.SKIP_DIRS and not (Path(current) / d).is_symlink())
            for name in sorted(files):
                if len(files_data) >= self.max_files or visited >= self.max_files * 10 or monotonic() >= deadline:
                    break
                visited += 1
                path = Path(current) / name
                if name.startswith(".") or name in self.SKIP_NAMES or path.suffix.lower() not in self.TEXT_EXTS:
                    continue
                try:
                    if path.is_symlink() or not path.is_file():
                        continue
                    with path.open("rb") as handle:
                        raw = handle.read(65537)
                    if b"\0" in raw:
                        continue
                    contents = getincrementaldecoder("utf-8")().decode(raw[:65536], final=len(raw) <= 65536)
                except (OSError, UnicodeError):
                    continue
                relative = path.relative_to(root).as_posix()
                files_data[relative] = {
                    "path": relative, "name": name, "size": len(raw[:65536]), "lines": len(contents.splitlines()),
                    "ext": path.suffix.lower(), "sha256": sha256(raw[:65536]).hexdigest(),
                    "truncated": len(raw) > 65536,
                }
                if len(emails) < 100:
                    emails.update(self.EMAIL_REGEX.findall(contents)[:30])
                if len(domains) < 100:
                    domains.update(self.DOMAIN_REGEX.findall(contents)[:30])
            if len(files_data) >= self.max_files or visited >= self.max_files * 10 or monotonic() >= deadline:
                errors.append("Filesystem inventory limit reached")
                break
        return self._directory_result(root.name, files_data, emails, domains, errors)

    def _directory_result(self, name, files_data, emails, domains, errors):
        graph = OsintKnowledgeGraph()
        root = self._node_id("FOLDER", name)
        graph.add_entity(OsintEntity(root, name, "FOLDER", 0, 1))
        for relative in files_data:
            parts = Path(relative).parts
            parent = root
            for i, part in enumerate(parts):
                kind = "FILE" if i == len(parts) - 1 else "FOLDER"
                parent = self._graph_child(graph, parent, kind, "/".join(parts[:i + 1]), part, "CONTAINS", "Filesystem", min(i + 1, 4))
        for domain in sorted(domains)[:30]:
            self._graph_child(graph, root, "DOMAIN", domain, domain, "REFERENCES_DOMAIN", "Text reference", 3)
        return {
            "target": name, "scope": name, "target_type": "LOCAL_DIRECTORY", "source": "observed",
            "files_scanned": len(files_data), "file_tree": list(files_data), "files_data": files_data,
            "emails_discovered": sorted(emails)[:30], "domains_discovered": sorted(domains)[:30],
            "errors": errors, "graph": graph.to_dict(), "evidence_count": len(files_data), "confidence": None,
            "confidence_note": "Text references do not establish identity or ownership.",
            "optimal_path": {"path_found": False, "optimal_path": [], "total_cost": None, "nodes_expanded": 0},
        }
