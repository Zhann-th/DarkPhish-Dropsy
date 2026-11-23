"use strict";

const previewButtons = [...document.querySelectorAll("[data-preview]")];
const previewRows = document.getElementById("preview-rows");
const previewStatus = document.getElementById("preview-status");
const previewLink = document.getElementById("preview-link");

async function sampleApi(path, body) {
  const options = body ? {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  } : undefined;
  const response = await fetch("/api/" + path, options);
  if (!response.ok) throw new Error("Пример недоступен.");
  return response.json();
}

function showPreview(key, comparison) {
  const pageChanges = comparison.changes.filter(change => change.category === "page");
  const help = pageChanges.find(change => change.key.endsWith("/help"));
  const home = pageChanges.find(change => change.key === comparison.scope);
  const csp = headers => headers?.["content-security-policy"] ? "Есть" : "Отсутствует";
  const values = [
    ["Страница /help", help?.before?.status ?? "—", help?.after?.status ?? "—"],
    ["Заголовок CSP", csp(home?.before), csp(home?.after)],
  ];
  previewRows.replaceChildren(...values.map(([label, before, after]) => {
    const row = document.createElement("tr");
    const name = document.createElement("th");
    name.scope = "row";
    name.textContent = label;
    row.append(name);
    for (const value of [before, after]) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    return row;
  }));
  for (const button of previewButtons) {
    button.setAttribute("aria-pressed", String(button.dataset.preview === key));
  }
  previewLink.href = key === "repair" ? "/audit?example=1&frame=recovered#timeline" : "/audit?example=1#timeline";
  previewStatus.textContent = key === "repair" ? "Сравнение после правки" : "Сравнение после релиза";
}

async function initPreview() {
  try {
    const [baseline, current, recovered] = await Promise.all(
      ["baseline", "current", "recovered"].map(version => sampleApi("audit/example/" + version))
    );
    const [release, repair] = await Promise.all([
      sampleApi("audit/compare", {baseline: baseline.snapshot, current: current.snapshot}),
      sampleApi("audit/compare", {baseline: current.snapshot, current: recovered.snapshot}),
    ]);
    const comparisons = {release, repair};
    for (const button of previewButtons) {
      const key = button.dataset.preview;
      button.disabled = false;
      button.addEventListener("click", () => showPreview(key, comparisons[key]));
    }
    showPreview("release", release);
  } catch {
    previewStatus.textContent = "Показан статичный учебный пример.";
  }
}

initPreview();
