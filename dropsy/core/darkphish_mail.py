"""Read-only email triage using the course search, Bayes and Bellman pipeline."""
import base64
import binascii
import http.client
import re
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from html.parser import HTMLParser
from time import monotonic
from urllib.parse import quote, urljoin, urlsplit

from .darkphish_course import _pipeline, search, update_belief
from .universal_scanner import UniversalOSINTScanner

MAX_LINKS = 4
MAX_HOPS = 4
MAX_EML_BYTES = 512 * 1024
MAX_TEXT = 20_000
LINKS = re.compile(r"https?://[^\s<>\"']+", re.I)
URGENT = re.compile(r"\b(?:urgent|immediately|within (?:24|48) hours|suspend(?:ed)?|срочно|немедленно|заблокиру\w*)\b", re.I)
CREDENTIAL = re.compile(r"\b(?:password|credentials|verification code|one.time code|парол\w*|код подтверждения)\b", re.I)
REQUEST = re.compile(r"\b(?:enter|provide|submit|confirm|verify|введ\w*|подтверд\w*|укаж\w*)\b", re.I)
REDIRECTS = {301, 302, 303, 307, 308}


class MailHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.text = []
        self.hidden = None

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "title", "head"} and self.hidden is None:
            self.hidden = tag
        if not self.hidden and tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag == self.hidden:
            self.hidden = None

    def handle_data(self, text):
        if not self.hidden:
            self.text.append(text)


def extract_message(encoded):
    if not encoded:
        return "", "", "", []
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid .eml file data.") from exc
    if not raw or len(raw) > MAX_EML_BYTES:
        raise ValueError("Use a non-empty .eml file no larger than 512 KiB.")
    message = BytesParser(policy=policy.default).parsebytes(raw)
    if not message.keys():
        raise ValueError("The .eml file has no email headers.")
    text, links = [], []

    def read_body(part):
        if part.get_content_disposition() == "attachment" or part.get_filename():
            return
        content_type = part.get_content_type()
        if part.get_content_maintype() == "multipart":
            for item in part.iter_parts():
                read_body(item)
        elif content_type in {"text/plain", "text/html"}:
            payload = part.get_payload(decode=True)
            if not isinstance(payload, bytes):
                return
            try:
                value = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            except LookupError:
                value = payload.decode("utf-8", errors="replace")
            if content_type == "text/html":
                parser = MailHTML()
                parser.feed(value)
                parser.close()
                links.extend(parser.links)
                value = " ".join(parser.text)
            text.append(value)

    try:
        read_body(message)
        extracted = " ".join([str(message.get("Subject", "")), *text])[:MAX_TEXT]
        return extracted, parseaddr(str(message.get("From", "")))[1], parseaddr(str(message.get("Reply-To", "")))[1], links
    except (ValueError, RecursionError) as exc:
        raise ValueError("The .eml file could not be read.") from exc


def canonical_url(value):
    value = value.strip()
    if not value.lower().startswith(("http://", "https://")):
        raise ValueError("Use an absolute HTTP or HTTPS link.")
    host, origin, url = UniversalOSINTScanner.parse_web_target(value)
    query = quote(urlsplit(value).query, safe="/?%:@!$&'()*+,;=-._~")
    return host, origin, url + ("?" + query if query else "")


def observe_link(url, scanner, enabled, origins, deadline):
    if not enabled:
        return {"hops": [{"url": url, "status": None}], "final": None, "state": "HTTP check off"}
    hops, seen = [], set()
    state = "Redirect limit reached"
    for _ in range(MAX_HOPS):
        try:
            host, origin, url = canonical_url(url)
        except ValueError:
            state = "Invalid or unsupported redirect target"
            break
        if url in seen:
            state = "Redirect loop"
            break
        if origins is not None and origin not in origins:
            state = "Origin outside configured scope"
            break
        if monotonic() >= deadline:
            state = "Check time limit reached"
            break
        seen.add(url)
        try:
            ip = scanner._resolve(host)[0]
            if monotonic() >= deadline:
                state = "Check time limit reached"
                break
            response = scanner._safe_fetch(url, host, ip, headers_only=True)
        except (ValueError, OSError, http.client.HTTPException):
            hops.append({"url": url, "status": None})
            state = "No usable HTTP response"
            break
        status = response["status"]
        hops.append({"url": url, "status": status})
        if status not in REDIRECTS:
            if 200 <= status < 300:
                return {"hops": hops, "final": url, "state": "Destination observed"}
            state = f"HTTP {status} · destination unconfirmed"
            break
        if not response["location"]:
            state = "Redirect with no Location header"
            break
        try:
            url = urljoin(url, response["location"])
        except ValueError:
            state = "Invalid or unsupported redirect target"
            break
    return {"hops": hops, "final": None, "state": state}


def domain_matches(host, expected):
    return host == expected or host.endswith("." + expected)


def analyze_mail(text="", url="", encoded="", expected_domain="", method="astar", resolve=False, origins=None):
    mail_text, sender, reply, html_links = extract_message(encoded)
    text = (text + "\n" + mail_text)[:MAX_TEXT]
    if not (text.strip() or url.strip() or html_links):
        raise ValueError("Paste text, enter a link, or upload an .eml with readable content.")
    expected = ""
    if expected_domain.strip():
        candidate = expected_domain.strip()
        if not re.fullmatch(r"[^/@:?#\s]+", candidate):
            raise ValueError("Enter a domain without a scheme or path.")
        expected, _, _ = canonical_url("https://" + candidate)
    manual_url = canonical_url(url)[2] if url.strip() else None
    candidates = [manual_url] if manual_url else []
    for raw in (*html_links, *(url.rstrip(".,;!)]}") for url in LINKS.findall(text))):
        try:
            candidate = canonical_url(raw)[2]
        except ValueError:
            continue
        if candidate not in candidates:
            candidates.append(candidate)
        if len(candidates) > MAX_LINKS:
            break

    graph, labels, signals = {"mail": []}, {"mail": "Email input"}, {}
    tail = "mail"

    def node(parent, key, label, signal=None):
        graph[parent].append((key, 1))
        graph[key] = []
        labels[key] = label
        if signal:
            signals[key] = signal
        return key

    if URGENT.search(text):
        tail = node(tail, "urgent", "Urgent wording", ("Urgency or threat wording detected", .60, .35))
    if REQUEST.search(text) and CREDENTIAL.search(text):
        tail = node(tail, "credential", "Credential request", ("Request wording and credential terms both appear", .75, .12))
    if "@" in sender and "@" in reply and sender.rsplit("@", 1)[1].lower() != reply.rsplit("@", 1)[1].lower():
        tail = node(tail, "reply", "Reply-To domain", ("From and Reply-To domains differ", .55, .18))

    scanner = UniversalOSINTScanner(timeout=1.6)
    deadline = monotonic() + 12
    reports = []
    for i, target in enumerate(candidates[:MAX_LINKS]):
        found = observe_link(target, scanner, resolve, origins, deadline)
        parent = tail
        hops = found["hops"] or [{"url": target, "status": None}]
        for j, hop in enumerate(hops):
            host = urlsplit(hop["url"]).hostname
            parent = node(parent, f"link-{i}-{j}", host)
        inspected = found["final"] or target
        host = urlsplit(inspected).hostname
        if expected and not domain_matches(host, expected):
            basis = "Observed destination" if found["final"] else "Original link"
            signals[parent] = (f"{basis} host differs from the expected domain", .65, .17)
        reports.append({"input": target, "index": i, "goal": parent, **found})

    goals = [row["goal"] for row in reports] or [tail]
    # One path per candidate link. The selected method supplies the evidence
    # for each score, then the highest-scoring route gets the detailed policy.
    scored = [update_belief(search(method, graph, "mail", goal)["path"], signals) for goal in goals]
    chosen = max(range(len(goals)), key=lambda i: scored[i]["posterior"])
    result = _pipeline(method, graph, labels, signals, "mail", goals[chosen])
    for row, belief in zip(reports, scored):
        row["score"] = belief["posterior"] if belief["steps"] else None
    has_signals = bool(result["belief"]["steps"])
    review_reason = None
    if not has_signals:
        review_reason = "insufficient evidence"
    elif result["decision"]["recommended"] == "Close as low priority" and any(not row["final"] for row in reports):
        review_reason = "destination incomplete"
    return {**result, "source": "mail", "links": reports, "selected_link": chosen if reports else None,
            "has_signals": has_signals, "review_reason": review_reason, "truncated_links": len(candidates) > MAX_LINKS}
