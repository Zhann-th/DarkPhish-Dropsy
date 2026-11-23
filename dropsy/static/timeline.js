"use strict";

const timelineExample = ["baseline", "current", "recovered"];
const exampleNames = ["До релиза", "После релиза", "После правки"];
let assets = [];
let timelineRows = [];
let availableExample = [];
let nextOffset = null;
let assetRevision = 0;

function dateLabel(snapshot) {
  const day = new Intl.DateTimeFormat("ru", {
    year: "numeric", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).format(new Date(snapshot.captured_at));
  return snapshot.label ? `${snapshot.label} · ${day}` : day;
}

function renderAssetPicker(value) {
  const picker = byId("history-asset");
  const placeholder = node("option", assets.length ? "Выберите сохранённый актив" : "Сохранённых активов пока нет");
  placeholder.value = "";
  const options = assets.map((asset, index) => {
    const option = node("option", asset.scope);
    option.value = String(index);
    return option;
  });
  if (availableExample.length) {
    const option = node("option", "workbench.example · учебный пример");
    option.value = "example";
    options.push(option);
  }
  picker.replaceChildren(placeholder, ...options);
  picker.disabled = !options.length;
  picker.value = value ?? "";
}

async function loadAssets(scope, mode) {
  assets = await api("/api/history/assets");
  const index = assets.findIndex(asset => asset.scope === scope && asset.mode === mode);
  const value = index >= 0 ? String(index) : undefined;
  renderAssetPicker(value);
  return value;
}

function restoreHistoryControls(fromId, toId) {
  byId("history-controls").hidden = !timelineRows.length;
  byId("history-more").hidden = nextOffset === null;
  for (const [id, selected] of [["history-baseline", fromId], ["history-current", toId]]) {
    const picker = byId(id);
    picker.replaceChildren(...timelineRows.map(row => {
      const option = node("option", dateLabel(row) + (row.partial ? " · частичный" : ""));
      option.value = row.fingerprint;
      return option;
    }));
    picker.value = selected;
  }
  const slider = byId("history-range");
  slider.max = Math.max(0, timelineRows.length - 1);
  slider.disabled = timelineRows.length < 2;
  slider.value = Math.max(timelineRows.findIndex(row => row.fingerprint === toId), 0);
  slider.setAttribute("aria-valuetext", dateLabel(timelineRows[Number(slider.value)]));
  byId("history-ticks").replaceChildren(
    node("span", dateLabel(timelineRows[0])),
    node("span", dateLabel(timelineRows.at(-1))),
  );
}

function historyUrl(asset, offset = 0) {
  const params = new URLSearchParams({scope: asset.scope, mode: asset.mode, offset});
  return "/api/history?" + params;
}

function sortTimeline(rows) {
  return rows.sort((a, b) => new Date(a.captured_at) - new Date(b.captured_at) ||
    a.fingerprint.localeCompare(b.fingerprint));
}

async function showHistoryAsset(value, preferred, frame = 1) {
  if (busy) return;
  const revision = ++assetRevision;
  const note = byId("history-note");
  const asset = assets[Number(value)];
  byId("history-controls").hidden = true;
  byId("history-asset").disabled = true;
  try {
    const ready = await collect(async () => {
      if (value === "example") {
        timelineRows = availableExample;
        nextOffset = null;
        const from = timelineRows[Math.max(0, frame - 1)];
        const to = timelineRows[frame];
        chooseBaseline(from.snapshot);
        restoreHistoryControls(from.fingerprint, to.fingerprint);
        note.textContent = "Три учебных снимка: до релиза, после релиза и после исправления.";
        return to.snapshot;
      }
      if (!asset) throw new Error("Выберите актив из истории.");
      const data = await api(historyUrl(asset));
      if (revision !== assetRevision || !data.snapshots.length) throw new Error("В истории нет снимков этого актива.");
      timelineRows = data.snapshots.reverse();
      nextOffset = data.next_offset;
      let to = timelineRows.find(row => row.fingerprint === preferred);
      if (!to && preferred) {
        const snapshot = await api("/api/history/" + encodeURIComponent(preferred));
        to = {...snapshot, snapshot};
        timelineRows = sortTimeline([...timelineRows, to]);
      }
      to ||= timelineRows.at(-1);
      const from = timelineRows[Math.max(0, timelineRows.indexOf(to) - 1)];
      const [older, newer] = await Promise.all([fetchSnapshot(from), fetchSnapshot(to)]);
      chooseBaseline(older);
      restoreHistoryControls(from.fingerprint, to.fingerprint);
      note.textContent = `Сохранённых снимков: ${asset.snapshot_count}. История хранится на этом сервере.`;
      return newer;
    }, "Выбранная версия открыта.");
    if (ready) byId("history-asset").value = value;
  } finally {
    byId("history-asset").disabled = !(assets.length || availableExample.length);
    if (!byId("history-controls").hidden) byId("history-range").disabled = timelineRows.length < 2;
  }
}

function fetchSnapshot(row) {
  if (row.snapshot) return Promise.resolve(row.snapshot);
  return api("/api/history/" + encodeURIComponent(row.fingerprint));
}

function compareHistory() {
  const fromId = byId("history-baseline").value;
  const toId = byId("history-current").value;
  const from = timelineRows.find(row => row.fingerprint === fromId);
  const to = timelineRows.find(row => row.fingerprint === toId);
  if (!from || !to || busy) return;
  return collect(async () => {
    const [previous, latest] = await Promise.all([fetchSnapshot(from), fetchSnapshot(to)]);
    chooseBaseline(previous);
    restoreHistoryControls(fromId, toId);
    return latest;
  }, "Сравнение готово.");
}

byId("history-range").addEventListener("input", event => {
  const row = timelineRows[Number(event.target.value)];
  if (!row) return;
  event.target.setAttribute("aria-valuetext", dateLabel(row));
  byId("history-current").value = row.fingerprint;
});
byId("history-range").addEventListener("change", compareHistory);
byId("history-baseline").addEventListener("change", compareHistory);
byId("history-current").addEventListener("change", compareHistory);
byId("history-asset").addEventListener("change", event => {
  if (event.target.value) showHistoryAsset(event.target.value);
  else byId("history-controls").hidden = true;
});

byId("history-more").addEventListener("click", async event => {
  const asset = assets[Number(byId("history-asset").value)];
  if (busy || !asset || nextOffset === null) return;
  const revision = assetRevision;
  const button = event.currentTarget;
  button.disabled = true;
  try {
    const data = await api(historyUrl(asset, nextOffset));
    if (revision !== assetRevision) return;
    const older = data.snapshots.reverse().filter(row => !timelineRows.some(existing => existing.fingerprint === row.fingerprint));
    timelineRows = sortTimeline([...older, ...timelineRows]);
    nextOffset = data.next_offset;
    restoreHistoryControls(byId("history-baseline").value, byId("history-current").value);
  } catch (error) {
    notify(error.message, true);
  } finally {
    button.disabled = false;
  }
});

byId("save-history").addEventListener("click", async event => {
  if (!current || current.source !== "observed" || busy) return;
  const snapshot = current;
  const button = event.currentTarget;
  button.disabled = true;
  try {
    const outcome = await api("/api/history", snapshot);
    const value = await loadAssets(snapshot.scope, snapshot.mode);
    if (current === snapshot && value !== undefined) await showHistoryAsset(value, snapshot.fingerprint);
    notify(outcome.saved ? "Снимок сохранён в истории." : "Этот снимок уже есть в истории.");
  } catch (error) {
    notify(error.message, true);
  } finally {
    button.disabled = !current || current.source === "synthetic";
  }
});

let exampleLoading = false;
async function openExample(frame) {
  if (exampleLoading || busy) return;
  exampleLoading = true;
  try {
    const series = await Promise.all(timelineExample.map(name => api("/api/audit/example/" + name)));
    availableExample = series.map(({snapshot}, index) => ({...snapshot, snapshot, label: exampleNames[index]}));
    renderAssetPicker("example");
    await showHistoryAsset("example", undefined, frame);
  } catch (error) {
    notify(error.message, true);
  } finally {
    exampleLoading = false;
  }
}

byId("load-example").addEventListener("click", async () => {
  await openExample(1);
  byId("timeline").scrollIntoView({block: "start"});
});
const launchOptions = new URLSearchParams(location.search);
const requestedCase = launchOptions.get("case");
const requestedTarget = launchOptions.get("target");
if (requestedTarget) byId("target").value = requestedTarget.slice(0, 2048);

async function loadCaseOptions() {
  const cases = await api("/api/workspace/cases");
  const picker = byId("attach-case-select");
  picker.replaceChildren(...cases.map(item => {
    const option = node("option", item.title);
    option.value = item.id;
    return option;
  }));
  if (cases.some(item => item.id === requestedCase)) {
    picker.value = requestedCase;
    byId("audit-case-reference").hidden = false;
    byId("audit-case-back").href = "/cases?case=" + requestedCase;
  }
  byId("attach-case-save").disabled = !cases.length;
  if (!cases.length) byId("attach-case-open").textContent = "Сначала создайте дело ↗";
}
loadCaseOptions().catch(() => {
  byId("attach-case-save").disabled = true;
});

byId("attach-case-form").addEventListener("submit", async event => {
  event.preventDefault();
  const snapshot = current;
  const caseId = byId("attach-case-select").value;
  if (!snapshot || snapshot.source !== "observed" || !caseId) return;
  const button = byId("attach-case-save");
  button.disabled = true;
  try {
    await api("/api/workspace/cases/" + encodeURIComponent(caseId) + "/materials", {
      kind: "snapshot", title: snapshot.scope, snapshot,
    });
    if (current === snapshot && !busy) {
      const value = await loadAssets(snapshot.scope, snapshot.mode);
      if (value !== undefined) await showHistoryAsset(value, snapshot.fingerprint);
    }
    byId("attach-case-open").href = "/cases?case=" + caseId;
    byId("attach-case-open").textContent = "Перейти к делу ↗";
    notify("Снимок сохранён и добавлен в дело.");
    byId("audit-case-reference").hidden = false;
    byId("audit-case-back").href = "/cases?case=" + caseId;
  } catch (error) {
    notify(error.message, true);
  } finally {
    button.disabled = false;
  }
});

async function openTimeline() {
  const fingerprint = launchOptions.get("snapshot");
  try {
    if (fingerprint) {
      const snapshot = await api("/api/history/" + encodeURIComponent(fingerprint));
      const value = await loadAssets(snapshot.scope, snapshot.mode);
      if (value === undefined) throw new Error("Актив для снимка не найден.");
      await showHistoryAsset(value, fingerprint);
      return;
    }
    await loadAssets();
    if (launchOptions.has("example")) await openExample(launchOptions.get("frame") === "recovered" ? 2 : 1);
  } catch (error) {
    byId("history-note").textContent = error.message;
  }
}
openTimeline();
