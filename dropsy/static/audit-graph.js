"use strict";

const graphPageLimit = 80;

function graphModel(snapshot) {
  const records = snapshot.records.filter(record => record.category === "page");
  if (!records.length) return null;
  const root = records.find(record => record.key === snapshot.scope) || records[0];
  const visible = [root, ...records.filter(record => record !== root)].slice(0, graphPageLimit);
  const pages = new Map(visible.map(record => [record.key, {...record, incoming: [], outgoing: []}]));
  let count = 0;
  for (const record of snapshot.records) {
    if (record.category !== "link") continue;
    const [source, target] = record.key.split(" → ");
    if (source === target || !pages.has(source) || !pages.has(target)) continue;
    pages.get(source).outgoing.push(target);
    pages.get(target).incoming.push(source);
    count++;
  }

  const parent = new Map([[root.key, null]]);
  const depth = new Map([[root.key, 0]]);
  const queue = [root.key];
  for (let i = 0; i < queue.length; i++) {
    const source = queue[i];
    for (const target of pages.get(source).outgoing) {
      if (parent.has(target)) continue;
      parent.set(target, source);
      depth.set(target, depth.get(source) + 1);
      queue.push(target);
    }
  }

  const levels = new Map([[0, [root.key]]]);
  for (const address of pages.keys()) {
    if (address === root.key) continue;
    const level = depth.get(address) ?? Infinity;
    if (!levels.has(level)) levels.set(level, []);
    levels.get(level).push(address);
  }
  return {pages, root: root.key, count, parent, levels, omitted: records.length - visible.length};
}

function graphElement(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined) node.textContent = value;
  return node;
}

function pagePath(address) {
  try {
    const path = new URL(address).pathname;
    try {
      return decodeURI(path);
    } catch {
      return path;
    }
  } catch {
    return address;
  }
}

function renderAuditGraph(snapshot, inspect) {
  const get = id => document.getElementById(id);
  const panel = get("audit-graph-panel");
  const graph = graphModel(snapshot);
  panel.hidden = !graph;
  if (!graph) return;

  const structure = get("audit-graph-structure");
  const neighbors = get("audit-graph-neighbors");
  const structureButton = get("audit-graph-structure-mode");
  const neighborsButton = get("audit-graph-neighbors-mode");
  const route = get("audit-graph-route");
  const selection = get("audit-graph-selection");
  let selected = graph.root;
  let mode = "structure";

  get("audit-graph-meta").textContent =
    `Страниц: ${graph.pages.size} · ссылок между ними: ${graph.count}` +
    (graph.omitted ? ` · вне графика: ${graph.omitted}` : "") +
    (snapshot.partial ? " · неполный снимок" : "");

  function card(address, onClick) {
    const page = graph.pages.get(address);
    const path = pagePath(address);
    const title = page.fields.title?.trim() || path;
    const button = graphElement("button", "audit-graph-node");
    button.type = "button";
    button.title = `${title} · ${address}`;
    const status = page.fields.status;
    const code = graphElement("span", "audit-graph-status", status ?? "—");
    code.title = status ? `HTTP ${status}` : "HTTP-статус неизвестен";
    code.dataset.kind = status >= 400 ? "error" : status >= 300 ? "redirect" : status >= 200 ? "ok" : "unknown";
    const top = graphElement("span", "audit-graph-node-top");
    top.append(graphElement("span", "audit-graph-title", title), code);
    button.append(top, graphElement("span", "audit-graph-path", path));
    if (address === graph.root) button.dataset.root = "";
    button.addEventListener("click", onClick);
    return button;
  }

  function renderNeighbors() {
    const page = graph.pages.get(selected);
    const group = (label, addresses) => {
      const section = graphElement("section", "audit-graph-relation");
      section.append(graphElement("h4", "", `${label} · ${addresses.length}`));
      if (!addresses.length) {
        section.append(graphElement("p", "muted", "В снимке таких ссылок нет."));
      } else {
        const grid = graphElement("div", "audit-graph-grid");
        for (const address of addresses) {
          grid.append(card(address, () => {
            select(address);
            get("audit-graph-focus").focus({preventScroll: true});
          }));
        }
        section.append(grid);
      }
      return section;
    };
    const current = graphElement("div", "audit-graph-focus");
    const focus = graphElement("h4", "", pagePath(selected));
    focus.id = "audit-graph-focus";
    focus.tabIndex = -1;
    current.append(graphElement("span", "eyebrow", "Выбранная страница"), focus);
    neighbors.replaceChildren(group("Ведут на страницу ↓", page.incoming), current, group("Со страницы ведут ↓", page.outgoing));
  }

  const cards = new Map();
  function select(address) {
    selected = address;
    const page = graph.pages.get(address);
    const chain = [];
    if (graph.parent.has(address)) {
      for (let current = address; current !== null; current = graph.parent.get(current)) chain.unshift(current);
    }
    const path = graphElement("ol", "audit-graph-breadcrumbs");
    for (const item of chain) {
      const label = item === graph.root ? "Старт" : pagePath(item);
      const li = graphElement("li");
      if (item === address) {
        const current = graphElement("span", "", label);
        current.setAttribute("aria-current", "location");
        li.append(current);
      } else {
        const button = graphElement("button", "", label);
        button.type = "button";
        button.addEventListener("click", () => {
          select(item);
          if (mode === "structure") cards.get(item).focus();
          else get("audit-graph-focus").focus({preventScroll: true});
        });
        li.append(button);
      }
      path.append(li);
    }
    route.replaceChildren(chain.length ? path : graphElement("span", "muted", "Путь от старта в снимке не найден."));
    for (const [key, button] of cards) {
      button.setAttribute("aria-pressed", String(key === address));
      button.classList.toggle("on-route", chain.includes(key));
    }
    selection.textContent = `${page.key} · HTTP ${page.fields.status ?? "—"} · входящих: ${page.incoming.length} · исходящих: ${page.outgoing.length}`;
    if (mode === "neighbors") renderNeighbors();
  }

  structure.replaceChildren();
  for (const [depth, addresses] of [...graph.levels].sort(([a], [b]) => a - b)) {
    const section = graphElement("section", "audit-graph-level");
    const heading = depth === 0 ? "Стартовая страница" : depth === Infinity ? "Без пути от старта"
      : depth === 1 ? "1 переход от старта" : `Переходов от старта: ${depth}`;
    const intro = graphElement("div", "audit-graph-level-heading");
    intro.append(graphElement("h4", "", heading), graphElement("span", "", String(addresses.length)));
    const grid = graphElement("div", "audit-graph-grid");
    for (const address of addresses) {
      const item = card(address, () => select(address));
      cards.set(address, item);
      grid.append(item);
    }
    section.append(intro, grid);
    structure.append(section);
  }

  function switchMode(next) {
    mode = next;
    structure.hidden = mode !== "structure";
    neighbors.hidden = mode !== "neighbors";
    structureButton.setAttribute("aria-pressed", String(!structure.hidden));
    neighborsButton.setAttribute("aria-pressed", String(!neighbors.hidden));
    if (!neighbors.hidden) renderNeighbors();
  }
  structureButton.onclick = () => switchMode("structure");
  neighborsButton.onclick = () => switchMode("neighbors");
  get("audit-graph-inspect").onclick = () => inspect(selected);
  switchMode("structure");
  select(graph.root);
}
