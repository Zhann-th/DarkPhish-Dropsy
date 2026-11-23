"use strict";

const graphPageLimit = 80;
const graphNodeWidth = 176;
const graphNodeHeight = 58;

function graphModel(snapshot) {
  const records = snapshot.records.filter(record => record.category === "page");
  if (!records.length) return null;
  const root = records.find(record => record.key === snapshot.scope) || records[0];
  const visible = [root, ...records.filter(record => record !== root)].slice(0, graphPageLimit);
  const pages = new Map(visible.map(record => [record.key, {...record, incoming: [], outgoing: []}]));
  const links = [];
  for (const record of snapshot.records) {
    if (record.category !== "link") continue;
    const [source, target] = record.key.split(" → ");
    if (source === target || !pages.has(source) || !pages.has(target)) continue;
    pages.get(source).outgoing.push(target);
    pages.get(target).incoming.push(source);
    links.push({source, target});
  }

  const depth = new Map([[root.key, 0]]);
  const queue = [root.key];
  for (let i = 0; i < queue.length; i++) {
    const source = queue[i];
    for (const target of pages.get(source).outgoing) {
      if (depth.has(target)) continue;
      depth.set(target, depth.get(source) + 1);
      queue.push(target);
    }
  }

  const detachedDepth = Math.max(...depth.values()) + 1;
  const rowsPerColumn = new Map();
  for (const page of pages.values()) {
    const column = depth.get(page.key) ?? detachedDepth;
    const row = rowsPerColumn.get(column) || 0;
    page.x = 22 + column * 242;
    page.y = 24 + row * 82;
    rowsPerColumn.set(column, row + 1);
  }
  return {
    pages, links, root: root.key, omitted: records.length - visible.length,
    width: Math.max(285, Math.max(...[...pages.values()].map(page => page.x)) + graphNodeWidth + 62),
    height: Math.max(130, Math.max(...[...pages.values()].map(page => page.y)) + graphNodeHeight + 24),
  };
}

function graphPath(source, target) {
  const startY = source.y + graphNodeHeight / 2;
  const endY = target.y + graphNodeHeight / 2;
  if (source.x === target.x) {
    const side = source.x + graphNodeWidth;
    return `M ${side} ${startY} C ${side + 48} ${startY}, ${side + 48} ${endY}, ${side + 2} ${endY}`;
  }
  const forward = source.x < target.x;
  const startX = source.x + (forward ? graphNodeWidth : 0);
  const endX = target.x + (forward ? -2 : graphNodeWidth + 2);
  const middle = (startX + endX) / 2;
  return `M ${startX} ${startY} C ${middle} ${startY}, ${middle} ${endY}, ${endX} ${endY}`;
}

function graphSvg(tag, attributes = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
  return element;
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
  const panel = document.getElementById("audit-graph-panel");
  const graph = graphModel(snapshot);
  panel.hidden = !graph;
  if (!graph) return;

  const get = id => document.getElementById(id);
  const viewport = get("audit-graph-viewport");
  const surface = get("audit-graph-surface");
  const stage = get("audit-graph-stage");
  const selection = get("audit-graph-selection");
  const inspectButton = get("audit-graph-inspect");
  get("audit-graph-meta").textContent =
    `Страниц: ${graph.pages.size} · связей: ${graph.links.length}` +
    (graph.omitted ? ` · вне графика: ${graph.omitted} (доступны в доказательствах)` : "") +
    (snapshot.partial ? " · неполный снимок" : "");

  const svg = graphSvg("svg", {
    width: graph.width, height: graph.height, viewBox: `0 0 ${graph.width} ${graph.height}`,
    "aria-hidden": "true", class: "audit-graph-edges",
  });
  const defs = graphSvg("defs");
  const marker = graphSvg("marker", {
    id: "audit-arrow", markerWidth: 7, markerHeight: 7, refX: 6, refY: 3.5, orient: "auto",
  });
  marker.append(graphSvg("path", {d: "M1 0 L7 3.5 L1 7 Z", fill: "context-stroke"}));
  defs.append(marker);
  svg.append(defs);
  const edges = graph.links.map(link => {
    const edge = graphSvg("path", {
      d: graphPath(graph.pages.get(link.source), graph.pages.get(link.target)),
      class: "audit-graph-edge", "marker-end": "url(#audit-arrow)",
    });
    svg.append(edge);
    return edge;
  });
  stage.replaceChildren(svg);

  const buttons = new Map();
  function select(page) {
    const path = pagePath(page.key);
    const status = page.fields.status ?? "—";
    selection.textContent = `${page.key} · HTTP ${status} · входящих: ${page.incoming.length} · исходящих: ${page.outgoing.length}`;
    inspectButton.onclick = () => inspect(page.key);
    edges.forEach((edge, i) => {
      const link = graph.links[i];
      edge.classList.toggle("selected", link.source === page.key || link.target === page.key);
    });
    for (const [address, button] of buttons) {
      button.setAttribute("aria-pressed", String(address === page.key));
    }
    const heading = page.fields.title || path;
    buttons.get(page.key).title = `${heading} · ${page.key}`;
  }

  for (const page of graph.pages.values()) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "audit-graph-node";
    button.style.left = `${page.x}px`;
    button.style.top = `${page.y}px`;
    button.style.width = `${graphNodeWidth}px`;
    button.style.height = `${graphNodeHeight}px`;
    button.title = page.key;
    const name = document.createElement("span");
    name.className = "audit-graph-path";
    name.textContent = pagePath(page.key);
    const details = document.createElement("small");
    details.textContent = `HTTP ${page.fields.status ?? "—"}${page.key === snapshot.scope ? " · старт" : ""}`;
    if (Number(page.fields.status) >= 400) button.dataset.error = "";
    button.append(name, details);
    button.addEventListener("click", () => select(page));
    buttons.set(page.key, button);
    stage.append(button);
  }

  let zoom = 1;
  function applyZoom(next) {
    zoom = Math.max(.65, Math.min(1.6, next));
    stage.style.width = `${graph.width}px`;
    stage.style.height = `${graph.height}px`;
    stage.style.transform = `scale(${zoom})`;
    surface.style.width = `${graph.width * zoom}px`;
    surface.style.height = `${graph.height * zoom}px`;
    get("audit-graph-zoom-in").disabled = zoom >= 1.6;
    get("audit-graph-zoom-out").disabled = zoom <= .65;
  }
  get("audit-graph-zoom-in").onclick = () => applyZoom(zoom + .15);
  get("audit-graph-zoom-out").onclick = () => applyZoom(zoom - .15);
  get("audit-graph-reset").onclick = () => {
    applyZoom(1);
    viewport.scrollLeft = 0;
    viewport.scrollTop = 0;
    select(graph.pages.get(graph.root));
  };
  get("audit-graph-reset").onclick();
}
