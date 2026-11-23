"use strict";

const element = id => document.getElementById(id);
const casesApi = "/api/workspace/cases";
const materialTypes = {link: "Ссылка", note: "Заметка", image: "Скриншот", snapshot: "Снимок аудита"};
const caseDate = new Intl.DateTimeFormat("ru", {dateStyle: "medium", timeStyle: "short"});
let activeCase = null;

function create(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}

function feedback(text, error = false) {
  element("case-status").textContent = text;
  element("case-status").toggleAttribute("data-error", error);
}

async function ask(path, body) {
  const reply = await fetch(path, body === undefined ? undefined : {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
  });
  const result = await reply.json();
  if (!reply.ok) {
    const validation = result.detail?.[0]?.msg?.replace(/^Value error, /, "");
    throw new Error(typeof result.detail === "string" ? result.detail : validation || "Проверьте поля формы.");
  }
  return result;
}

function caseList(cases) {
  const list = element("case-list");
  const rows = cases.map(item => {
    const link = create("a");
    link.href = "/cases?case=" + item.id;
    if (item.id === activeCase?.id) link.setAttribute("aria-current", "page");
    link.append(create("span", item.title), create("small", item.material_count));
    return link;
  });
  list.replaceChildren(...rows);
  if (!rows.length) element("new-case").open = true;
}

function externalLink(target) {
  const anchor = create("a", target, "material-source");
  anchor.href = target;
  anchor.target = "_blank";
  anchor.rel = "noopener noreferrer";
  return anchor;
}

function renderMaterials() {
  if (!activeCase) return;
  const query = element("material-search").value.trim().toLowerCase();
  const filtered = activeCase.materials.filter(item =>
    [item.title, item.source_url, item.note, materialTypes[item.kind]].some(value => value.toLowerCase().includes(query))
  );
  const list = element("materials");
  list.replaceChildren(...filtered.map(item => {
    const row = create("li");
    row.append(create("span", materialTypes[item.kind], "material-label"), create("h4", item.title));
    if (item.source_url) row.append(externalLink(item.source_url));
    const observed = item.observed_on ? " · Наблюдение " + item.observed_on.split("-").reverse().join(".") : "";
    row.append(create("p", "Добавлено " + caseDate.format(new Date(item.created_at)) + observed, "muted material-date"));
    if (item.kind === "link") {
      const audit = create("a", "Открыть адрес в аудите ↗", "material-source");
      audit.href = "/audit?" + new URLSearchParams({case: activeCase.id, target: item.source_url});
      const action = create("div");
      action.append(audit);
      row.append(action);
    }
    if (item.snapshot_at) row.append(create("p", "Состояние за " + caseDate.format(new Date(item.snapshot_at)), "muted material-date"));
    if (item.note) row.append(create("p", item.note, "material-note"));
    if (item.kind === "snapshot") {
      const snapshot = create("a", "Открыть снимок в аудите ↗", "material-source");
      snapshot.href = "/audit?" + new URLSearchParams({snapshot: item.snapshot_fingerprint, case: activeCase.id}) + "#timeline";
      row.append(snapshot);
    }
    if (item.kind === "image") {
      const image = create("img", undefined, "material-image");
      image.src = casesApi + "/" + activeCase.id + "/materials/" + item.id + "/image";
      image.loading = "lazy";
      image.alt = item.title;
      row.append(image);
    }
    return row;
  }));
  if (!filtered.length) list.append(create("li", query ? "По этому запросу ничего не найдено." : "Пока нет материалов.", "muted"));
}

async function loadCase(caseId) {
  const cases = await ask(casesApi);
  activeCase = null;
  element("case-detail").hidden = true;
  caseList(cases);
  const selected = caseId || cases[0]?.id;
  if (!selected) {
    feedback("Создайте дело, чтобы собрать материалы.");
    return;
  }
  activeCase = await ask(casesApi + "/" + encodeURIComponent(selected));
  caseList(cases);
  element("case-detail").hidden = false;
  element("case-name").textContent = activeCase.title;
  element("case-description").textContent = activeCase.description;
  element("case-audit").href = "/audit?case=" + activeCase.id;
  renderMaterials();
  feedback("");
}

function updateFields() {
  const kind = element("material-kind").value;
  element("material-url").required = kind === "link";
  element("material-note").required = kind === "note";
  element("material-file").required = kind === "image";
  element("material-file-row").hidden = kind !== "image";
}

function loadImage(file) {
  if (!file || file.size > 5 * 1024 * 1024) throw new Error("Прикрепите скриншот до 5 МиБ.");
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = () => reject(new Error("Скриншот не удалось прочитать."));
    reader.readAsDataURL(file);
  });
}

element("case-form").addEventListener("submit", async event => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  button.disabled = true;
  try {
    const item = await ask(casesApi, {title: element("new-title").value, description: element("new-description").value});
    history.replaceState(null, "", "/cases?case=" + item.id);
    await loadCase(item.id);
    element("case-form").reset();
    element("new-case").open = false;
    feedback("Дело создано.");
  } catch (error) {
    feedback(error.message, true);
  } finally {
    button.disabled = false;
  }
});

element("material-form").addEventListener("submit", async event => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  const kind = element("material-kind").value;
  const caseId = activeCase.id;
  button.disabled = true;
  try {
    const item = {
      kind, title: element("material-title").value, source_url: element("material-url").value,
      note: element("material-note").value, observed_on: element("material-date").value || null,
    };
    if (kind === "image") item.image_base64 = await loadImage(element("material-file").files[0]);
    await ask(casesApi + "/" + caseId + "/materials", item);
    await loadCase(caseId);
    element("material-form").reset();
    updateFields();
    element("material-editor").open = false;
    feedback("Материал сохранён.");
  } catch (error) {
    feedback(error.message, true);
  } finally {
    button.disabled = false;
  }
});
element("material-kind").addEventListener("change", updateFields);
element("material-search").addEventListener("input", renderMaterials);
updateFields();
loadCase(new URLSearchParams(location.search).get("case")).catch(error => feedback(error.message, true));
