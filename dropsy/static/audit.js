"use strict";

const byId = id => document.getElementById(id);
const categories = {dns: "DNS", tls: "TLS", page: "Страница", link: "Ссылка", file: "Файл"};
const levels = {high: "Высокий", medium: "Средний", low: "Низкий", info: "Сведения"};
const states = {added: "Появилось", changed: "Изменилось", missing: "Не наблюдается"};
let current = null;
let baseline = null;
let comparison = null;
let comparisonRevision = 0;
let busy = false;

function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}

function notify(message, error = false) {
  byId("status").textContent = message;
  byId("status").toggleAttribute("data-error", error);
}

async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : "Сервер отклонил запрос. Проверьте входные данные.");
  }
  return data;
}

function sourceLabel(snapshot) {
  return snapshot.source === "synthetic" ? "Учебный пример" : "Собранные наблюдения";
}

function badge(value, labels) {
  const el = node("span", labels[value] || value, "level");
  el.dataset.level = value;
  return el;
}

function fields(values) {
  const list = node("dl", undefined, "fields");
  if (!values) return list;
  for (const [key, value] of Object.entries(values)) {
    list.append(node("dt", key), node("dd", value ?? "—"));
  }
  return list;
}

function details(label, prefix, values) {
  const row = node("details");
  const summary = node("summary");
  summary.append(prefix, document.createTextNode(label));
  row.append(summary, values);
  return row;
}

function redrawRecords() {
  if (!current) return;
  const search = byId("record-search").value.trim().toLowerCase();
  const category = byId("record-category").value;
  const matching = current.records.filter(record =>
    (!category || record.category === category) &&
    (!search || [record.key, ...Object.entries(record.fields).flat()].join(" ").toLowerCase().includes(search))
  );
  const container = byId("records");
  container.replaceChildren();
  if (!matching.length) {
    container.append(node("p", "Нет записей по этому фильтру.", "muted"));
    return;
  }
  const fragment = document.createDocumentFragment();
  for (const record of matching) {
    const values = node("div");
    values.append(Object.keys(record.fields).length ? fields(record.fields) : node("small", "Запись фиксирует наличие связи."));
    const row = details(record.key, badge(record.category, categories), values);
    row.dataset.recordKey = record.key;
    fragment.append(row);
  }
  container.append(fragment);
}

function renderCurrent() {
  byId("results").hidden = false;
  const darkphishLink = byId("open-darkphish");
  darkphishLink.hidden = current.mode !== "web" || current.source !== "observed";
  if (!darkphishLink.hidden) darkphishLink.href = "/darkphish?" + new URLSearchParams({target: current.scope});
  byId("assistant-output").hidden = true;
  byId("set-baseline").disabled = false;
  byId("source").textContent = sourceLabel(current) + (current.partial ? " · ограниченное покрытие" : "");
  byId("scope").textContent = current.scope + " · " + new Date(current.captured_at).toLocaleString("ru");
  byId("fingerprint").textContent = "SHA-256 " + current.fingerprint;
  const metrics = current.mode === "directory" ? [
    ["Файлы", current.records.filter(r => r.category === "file").length],
    ["Частичные образцы", current.records.filter(r => r.fields.truncated === true).length],
  ] : [
    ["DNS-адреса", current.records.filter(r => r.category === "dns").length],
    ["HTTP-страницы", current.records.filter(r => r.category === "page").length],
  ];
  metrics.push(["Записи", current.records.length], ["Замечания", current.findings.length]);
  byId("metrics").replaceChildren(...metrics.map(([label, value]) => {
    const metric = node("div", undefined, "metric");
    metric.append(node("dt", label), node("dd", value));
    return metric;
  }));
  const findings = byId("findings");
  findings.replaceChildren(...current.findings.map(finding => {
    const item = node("li");
    const heading = node("strong", finding.title);
    item.append(badge(finding.level, levels), heading, node("small", finding.evidence), node("p", finding.action));
    return item;
  }));
  if (!current.findings.length) findings.append(node("li", "По настроенным правилам замечаний нет."));
  redrawRecords();
  renderAuditGraph(current, inspectAuditPage);
  renderLinkMap();
  byId("save-history").disabled = current.source === "synthetic";
  byId("attach-case").hidden = current.source === "synthetic";
}

function inspectAuditPage(address) {
  byId("record-search").value = address;
  byId("record-category").value = "page";
  redrawRecords();
  const record = [...byId("records").querySelectorAll("details")].find(item => item.dataset.recordKey === address);
  if (record) {
    record.open = true;
    record.querySelector("summary").focus();
  }
}

function renderLinkMap() {
  const map = byId("link-map");
  map.replaceChildren();
  const outgoing = new Map();
  for (const record of current.records) {
    if (record.category !== "link") continue;
    const [from, to] = record.key.split(" → ");
    if (!to) continue;
    if (!outgoing.has(from)) outgoing.set(from, []);
    outgoing.get(from).push(to);
  }
  byId("topology-panel").hidden = !outgoing.size;
  for (const [from, destinations] of outgoing) {
    const values = node("div");
    const list = node("ul", undefined, "link-list");
    for (const address of destinations) {
      const item = node("li");
      const route = node("button", address, "route-button");
      route.type = "button";
      route.addEventListener("click", () => {
        inspectAuditPage(address);
      });
      item.append(route);
      list.append(item);
    }
    values.append(list);
    const group = details(from, badge("page", categories), values);
    group.open = !map.childElementCount;
    map.append(group);
  }
}

function chooseBaseline(snapshot) {
  baseline = snapshot;
  byId("baseline-status").textContent = sourceLabel(baseline) + " · " + baseline.scope +
    " · " + new Date(baseline.captured_at).toLocaleString("ru");
}

function changedFields(change) {
  const before = change.before || {};
  const after = change.after || {};
  const keys = [...new Set([...Object.keys(before), ...Object.keys(after)])].sort();
  const visible = keys.filter(key =>
    Object.hasOwn(before, key) !== Object.hasOwn(after, key) || before[key] !== after[key]
  );
  if (!visible.length) return node("small", "Изменилось наличие записи.");
  const table = node("table", undefined, "delta-table");
  const heading = node("thead");
  const header = node("tr");
  for (const label of ["Поле", "До", "После"]) {
    const cell = node("th", label);
    cell.scope = "col";
    header.append(cell);
  }
  heading.append(header);
  const body = node("tbody");
  for (const key of visible) {
    const row = node("tr");
    const label = node("th", key);
    label.scope = "row";
    row.append(label);
    for (const fields of [before, after]) {
      row.append(node("td", Object.hasOwn(fields, key) ? String(fields[key]) : "Не наблюдалось"));
    }
    body.append(row);
  }
  table.append(heading, body);
  return table;
}

async function refreshComparison() {
  const revision = ++comparisonRevision;
  comparison = null;
  byId("diff").replaceChildren();
  if (!current || !baseline) {
    byId("diff-summary").textContent = "Загрузите эталон для сравнения.";
    return;
  }
  byId("diff-summary").textContent = "Сравнение снимков…";
  try {
    const data = await api("/api/audit/compare", {current, baseline});
    if (revision !== comparisonRevision) return;
    comparison = data;
    const {added, changed, missing} = data.summary;
    byId("diff-summary").textContent = `Появилось ${added} · Изменилось ${changed} · Не наблюдается ${missing}` +
      (data.partial ? " · Сравнение с ограниченным покрытием" : "");
    const fragment = document.createDocumentFragment();
    for (const change of data.changes) {
      const values = node("div");
      values.append(changedFields(change));
      fragment.append(details(change.key, badge(change.state, states), values));
    }
    byId("diff").append(fragment);
  } catch (error) {
    if (revision === comparisonRevision) byId("diff-summary").textContent = error.message;
  }
}

async function collect(action, ready = "Снимок готов.") {
  if (busy) return;
  busy = true;
  byId("collect").disabled = true;
  byId("load-example").disabled = true;
  notify("Сбор данных…");
  try {
    current = await action();
    renderCurrent();
    notify(ready);
    await refreshComparison();
    return true;
  } catch (error) {
    notify(error.message, true);
    return false;
  } finally {
    busy = false;
    byId("collect").disabled = false;
    byId("load-example").disabled = false;
  }
}

function download(name, mime, data) {
  const url = URL.createObjectURL(new Blob([data], {type: mime}));
  const link = node("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function markdownText(value) {
  return String(value).replace(/[\r\n]+/g, " ").replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/([\\`*_{}!\[\]#>])/g, "\\$1");
}

function exportReport() {
  const report = [
    "# Dropsy — отчёт по активу", "",
    `- Область — ${markdownText(current.scope)}`,
    `- Источник — ${sourceLabel(current)}`,
    `- Время — ${current.captured_at}`,
    `- SHA-256 — ${current.fingerprint}`,
    `- Записей — ${current.records.length}`,
    `- Покрытие — ${current.partial ? "ограничено" : "сбор завершён в выбранной области"}`,
    "", "## Замечания", "",
  ];
  for (const row of current.findings) {
    report.push(`- **${levels[row.level]} · ${markdownText(row.title)}**. ${markdownText(row.evidence)}. ${markdownText(row.action)}`);
  }
  if (!current.findings.length) report.push("По настроенным правилам замечаний нет.");
  if (comparison) {
    report.push("", "## Изменения к эталону", "", `SHA-256 эталона — ${baseline.fingerprint}`, "");
    if (comparison.partial) report.push("Сравнение с ограниченным покрытием.", "");
    for (const row of comparison.changes) {
      report.push(`- ${states[row.state]} · ${categories[row.category]} · ${markdownText(row.key)}`);
    }
    if (!comparison.changes.length) report.push("Различий между записями нет.");
  }
  download("dropsy-report.md", "text/markdown;charset=utf-8", report.join("\n") + "\n");
}

byId("collect-form").addEventListener("submit", event => {
  event.preventDefault();
  collect(async () => (await api("/api/scan", {
    target: byId("target").value.trim(),
    max_pages: Number(byId("max-pages").value),
  })).snapshot);
});
byId("set-baseline").addEventListener("click", () => {
  chooseBaseline(current);
  notify("Текущий снимок стал эталоном для следующего сбора.");
  refreshComparison();
});
async function readSnapshot(file) {
  if (file.size > 12 * 1024 * 1024) throw new Error("Размер снимка превышает 12 МБ.");
  const snapshot = JSON.parse(await file.text());
  return api("/api/audit/validate", snapshot);
}

byId("current-file").addEventListener("change", event => {
  const file = event.target.files[0];
  event.target.value = "";
  if (file) collect(() => readSnapshot(file), "Снимок загружен. Контрольная сумма совпадает.");
});

byId("baseline-file").addEventListener("change", async event => {
  const file = event.target.files[0];
  event.target.value = "";
  if (!file) return;
  try {
    const snapshot = await readSnapshot(file);
    chooseBaseline(snapshot);
    notify("Эталон загружен и проверен.");
    await refreshComparison();
  } catch (error) {
    notify(error.message, true);
  }
});
byId("record-search").addEventListener("input", redrawRecords);
byId("record-category").addEventListener("change", redrawRecords);
byId("download-json").addEventListener("click", () => download(
  "dropsy-snapshot.json", "application/json", JSON.stringify(current, null, 2)
));
byId("download-report").addEventListener("click", exportReport);
byId("explain").addEventListener("click", async () => {
  const button = byId("explain");
  const output = byId("assistant-output");
  const snapshot = current;
  button.disabled = true;
  output.hidden = false;
  output.textContent = "Разбираем наблюдения…";
  try {
    const result = await api("/api/gemini/chat", {
      message: "Объясни замечания снимка и шаги по исправлению.",
      snapshot,
    });
    if (current === snapshot) {
      output.textContent = (result.source === "google_gemini_api" ? "Gemini" : "Локальный анализ") +
        "\n\n" + result.reply.replace(/^#{1,3} /gm, "");
    }
  } catch (error) {
    if (current === snapshot) output.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

api("/api/audit/config").then(config => {
  let options = "Можно указать любой публичный HTTP(S)-адрес.";
  if (config.web_mode === "restricted") {
    options = config.origins.length ? `Разрешённые адреса — ${config.origins.join(", ")}.` :
      "В настройках сервера включён список разрешённых адресов, но в нём нет корректных записей.";
  }
  byId("config-status").textContent = options + (config.local_enabled ? " Для папки начните путь с ./." : "");
}).catch(() => {
  byId("config-status").textContent = "Конфигурация сбора недоступна.";
});
