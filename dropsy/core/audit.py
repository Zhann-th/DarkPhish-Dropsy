"""Versioned, content-addressed audit snapshots and evidence-based comparisons."""
from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .universal_scanner import UniversalOSINTScanner

Category = Literal["dns", "tls", "page", "link", "file"]
TextValue = Annotated[str, StringConstraints(max_length=2048)]
FieldName = Annotated[str, StringConstraints(max_length=60)]
Value = TextValue | int | bool | None


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Category
    key: str = Field(min_length=1, max_length=4200)
    fields: dict[FieldName, Value] = Field(max_length=16)


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: Literal["high", "medium", "low", "info"]
    title: str = Field(max_length=200)
    evidence: str = Field(max_length=4096)
    action: str = Field(max_length=1000)


class Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    source: Literal["observed", "synthetic"]
    mode: Literal["web", "directory"]
    scope: str = Field(min_length=1, max_length=2048)
    captured_at: datetime
    partial: bool
    records: list[Record] = Field(max_length=2200)
    findings: list[Finding] = Field(max_length=60)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


def _digest(snapshot):
    body = snapshot.model_dump(mode="json", exclude={"fingerprint"})
    return sha256(json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def _finding(findings, level, title, evidence, action):
    findings.append({"level": level, "title": title, "evidence": evidence, "action": action})


def build_snapshot(data, captured_at=None):
    local = data["target_type"] == "LOCAL_DIRECTORY"
    records, findings = [], []
    for address in data.get("resolved_ips", []):
        records.append(Record(category="dns", key=address, fields={"address": address}))
    if cert := data.get("ssl_info"):
        records.append(Record(category="tls", key="leaf", fields=cert))
        if cert.get("not_after"):
            try:
                days = (datetime.strptime(cert["not_after"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC) - datetime.now(UTC)).days
            except ValueError:
                days = None
            if days is not None and days <= 30:
                _finding(findings, "high" if days < 7 else "medium", "Скоро истекает сертификат",
                         f"TLS · {cert['not_after']}", "Проверьте автоматическое продление сертификата.")
    for page in data.get("pages", []):
        records.append(Record(category="page", key=page["url"], fields={
            "status": page["status"], "title": page["title"], **page.get("headers", {}),
        }))
    for edge in data.get("page_links", []):
        records.append(Record(category="link", key=edge["source"] + " → " + edge["target"], fields={}))
    for name, meta in data.get("files_data", {}).items():
        records.append(Record(category="file", key=name, fields={
            "sha256": meta["sha256"], "sample_bytes": meta["size"], "truncated": meta["truncated"],
        }))
    if first := data.get("target_response"):
        url = first["url"]
        headers = first.get("headers", {})
        if urlsplit(url).scheme == "http" and 200 <= first["status"] < 300:
            _finding(findings, "medium", "Стартовая страница обслуживается по HTTP",
                     f"{url} · HTTP {first['status']}", "Проверьте доступность HTTPS и перенаправление с HTTP.")
        if 200 <= first["status"] < 300 and "html" in first["content_type"]:
            if url.startswith("https://") and "strict-transport-security" not in headers:
                _finding(findings, "medium", "HSTS отсутствует в ответе стартовой страницы",
                         url, "Проверьте готовность домена к HSTS и задайте политику на HTTPS.")
            if "content-security-policy" not in headers:
                _finding(findings, "medium", "CSP отсутствует в ответе стартовой страницы",
                         url, "Определите допустимые источники ресурсов и проверьте политику CSP.")
            if "x-frame-options" not in headers and "frame-ancestors" not in headers.get("content-security-policy", "").lower():
                _finding(findings, "low", "Ограничение встраивания страницы не обнаружено",
                         url, "Проверьте настройку CSP frame-ancestors или X-Frame-Options.")
    broken = [f"{p['path']} ({p['status']})" for p in data.get("pages", []) if p["status"] in (404, 410)]
    if broken:
        _finding(findings, "low", "Найдены недоступные страницы", ", ".join(broken[:8])[:4000],
                 "Проверьте ссылки на эти страницы и актуальность маршрутов.")
    partial = bool(data.get("errors") or data.get("limit_reached") or any(
        row.get("truncated") for row in [*data.get("pages", []), *data.get("files_data", {}).values()]
    ))
    if partial:
        _finding(findings, "info", "Покрытие ограничено", f"Ошибок сбора: {len(data.get('errors', []))}",
                 "При сравнении считайте пропавшие записи ненаблюдавшимися в этом снимке.")
    snapshot = Snapshot(
        source=data["source"], mode="directory" if local else "web", scope=data["scope"],
        captured_at=captured_at or datetime.now(UTC).replace(microsecond=0), partial=partial,
        records=sorted(records, key=lambda r: (r.category, r.key))[:2200],
        findings=findings, fingerprint="0" * 64,
    )
    snapshot.fingerprint = _digest(snapshot)
    return snapshot


def validate_snapshot(snapshot):
    if _digest(snapshot) != snapshot.fingerprint:
        raise ValueError("Контрольная сумма снимка не совпадает.")
    if len({(r.category, r.key) for r in snapshot.records}) != len(snapshot.records):
        raise ValueError("В снимке есть повторяющиеся записи.")


def compare_snapshots(baseline, current):
    validate_snapshot(baseline)
    validate_snapshot(current)
    if (baseline.scope, baseline.mode, baseline.source) != (current.scope, current.mode, current.source):
        raise ValueError("Снимки должны иметь одинаковую область, режим и источник.")
    old = {(r.category, r.key): r for r in baseline.records}
    new = {(r.category, r.key): r for r in current.records}
    changes = []
    for key in sorted(old.keys() | new.keys()):
        before, after = old.get(key), new.get(key)
        if before and after and before.fields == after.fields:
            continue
        state = "changed" if before and after else "added" if after else "missing"
        changes.append({"category": key[0], "key": key[1], "state": state,
                        "before": before.fields if before else None, "after": after.fields if after else None})
    return {
        "scope": current.scope, "source": current.source, "partial": baseline.partial or current.partial,
        "summary": {state: sum(r["state"] == state for r in changes) for state in ("added", "changed", "missing")},
        "changes": changes,
    }


def sample_audit(variant):
    target = "workbench.example"
    origin = f"https://{target}"
    broken = variant == "current"
    page_list = [
        {"url": origin + "/", "path": "/", "title": "Workbench", "status": 200, "content_type": "text/html",
         "headers": {"strict-transport-security": "max-age=31536000", **(
             {"content-security-policy": "default-src 'self'; frame-ancestors 'none'"} if not broken else {}
         )}},
        {"url": origin + "/help", "path": "/help", "title": "Help", "status": 404 if broken else 200,
         "content_type": "text/html", "headers": {}},
    ]
    if variant != "baseline":
        page_list.append({"url": origin + "/status", "path": "/status", "title": "Status",
                          "status": 200, "content_type": "text/html", "headers": {}})
    data = {
        "target": target, "scope": origin + "/", "target_type": "REMOTE_NETWORK", "source": "synthetic",
        "resolved_ips": ["192.0.2.10" if variant == "baseline" else "192.0.2.20"], "ssl_info": None,
        "pages": page_list, "target_response": page_list[0], "errors": [], "confidence": None,
        "confidence_note": "Synthetic training fixture. No network requests were made.",
        "page_links": [{"source": page_list[0]["url"], "target": page["url"]} for page in page_list[1:]],
    }
    UniversalOSINTScanner()._attach_web_graph(data)
    day = {"baseline": 14, "current": 15, "recovered": 16}[variant]
    data["snapshot"] = build_snapshot(data, captured_at=datetime(2026, 10, day, 9, tzinfo=UTC))
    return data
