"use strict";
const byId = id => document.getElementById(id);
const displayNames = {bfs:"BFS", dfs:"DFS", ucs:"UCS", astar:"A*"};
const fixturePositions = {
  report:[85,150], queue:[270,42], archive:[475,42], reputation:[631,125],
  intake:[282,245], analyst:[500,245], decision:[802,265],
};
const percent = x => (100*x).toFixed(2)+"%";
const n3 = x => x.toFixed(3);
function cell(tag, text) {
  const el=document.createElement(tag);
  el.textContent=text;
  return el;
}
function table(target, headers, rows, chosen) {
  const wrap=document.createElement("div");
  wrap.className="table-scroll";
  const tbl=document.createElement("table");
  const head=tbl.createTHead().insertRow();
  for (const header of headers) {
    const column=cell("th",header);
    column.scope="col";
    head.append(column);
  }
  const body=tbl.createTBody();
  for (const [i,row] of rows.entries()) {
    const tr=body.insertRow();
    if (i===chosen) tr.className="selected-row";
    for (const value of row) tr.append(cell("td",value));
  }
  wrap.append(tbl);
  byId(target).replaceChildren(wrap);
}
function svgElement(tag, attributes) {
  const el=document.createElementNS("http://www.w3.org/2000/svg",tag);
  for(const [key,value] of Object.entries(attributes)) el.setAttribute(key,value);
  return el;
}
let currentSnapshot = null;
const isWebsite = () => byId("mode").value === "site";

function websitePositions(graph, source) {
  const depth = new Map([[source, 0]]);
  const queue = [source];
  for (let i = 0; i < queue.length; i++) {
    const from = queue[i];
    for (const [target] of graph[from]) {
      if (depth.has(target)) continue;
      depth.set(target, depth.get(from) + 1);
      queue.push(target);
    }
  }
  const rows = new Map();
  const outside = Math.max(...depth.values()) + 1;
  const positions = {};
  for (const key of Object.keys(graph)) {
    const column = depth.get(key) ?? outside;
    const row = rows.get(column) || 0;
    positions[key] = [92 + column * 196, 45 + row * 69];
    rows.set(column, row + 1);
  }
  return positions;
}

function drawGraph(data, route) {
  const {graph, labels} = data;
  const positions = data.source === "observed" ? websitePositions(graph, data.start) : fixturePositions;
  const svg=byId("graph");
  svg.replaceChildren();
  const points = Object.values(positions);
  const width = Math.max(670, Math.max(...points.map(([x]) => x)) + 85);
  const height = Math.max(data.source === "observed" ? 135 : 330, Math.max(...points.map(([,y]) => y)) + 45);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const defs=svgElement("defs",{});
  const marker=svgElement("marker",{id:"arrow",markerWidth:8,markerHeight:8,refX:7,refY:4,orient:"auto"});
  marker.append(svgElement("path",{d:"M0 0 L8 4 L0 8Z",fill:"#477267"}));
  defs.append(marker);
  svg.append(defs);
  for(const [from, outgoing] of Object.entries(graph)) {
    for(const [to,weight] of outgoing) {
      const [x1,y1]=positions[from], [x2,y2]=positions[to];
      const routeIndex=route.indexOf(from);
      const selected=routeIndex>=0 && route[routeIndex+1]===to;
      const forward = x1 <= x2;
      const start = x1 + (forward ? 69 : -69), end = x2 + (forward ? -71 : 71);
      const midpoint = x1 === x2 ? x1 + 84 : (start + end) / 2;
      const targetX = x1 === x2 ? x2 + 71 : end;
      svg.append(svgElement("path", {d: `M${start} ${y1} C${midpoint} ${y1} ${midpoint} ${y2} ${targetX} ${y2}`,
        class:selected?"edge selected":"edge","marker-end":"url(#arrow)"}));
      const cost=svgElement("text",{x:midpoint,y:(y1+y2)/2-7,"text-anchor":"middle",class:"weight"});
      cost.textContent=weight;
      svg.append(cost);
    }
  }
  for(const [key,[x,y]] of Object.entries(positions)) {
    const group=svgElement("g",{class:route.includes(key)?"graph-node selected":"graph-node"});
    group.append(svgElement("rect",{x:x-69,y:y-18,width:138,height:36,rx:3}));
    const label=svgElement("text",{x,y:y+4,"text-anchor":"middle"});
    const fullLabel = labels[key];
    label.textContent = fullLabel.length > 18 ? fullLabel.slice(0, 17) + "…" : fullLabel;
    const tooltip = svgElement("title",{});
    tooltip.textContent = data.pages?.find(page => page.id === key)?.url || fullLabel;
    group.append(tooltip, label);
    svg.append(group);
  }
}
function fill(data) {
  const route=data.routes[data.method];
  drawGraph(data, route.path);
  const observed = data.source === "observed";
  byId("context").textContent = observed
    ? data.url + " · " + data.pages.length + " observed pages" + (data.partial ? " · partial coverage" : "")
      + (data.start === data.goal ? " · route contains only the starting page" : "")
    : "Synthetic phishing-report example";
  byId("hypothesis").textContent = observed
    ? "H = the observed route deserves a closer site review, under the course model."
    : "H = the reported email is phishing in the synthetic scenario.";
  byId("assumptions").textContent = observed
    ? "HTTP observations are real. Prior, likelihoods, weights and rewards are illustrative. The result does not classify the site as phishing."
    : "Synthetic observations and illustrative rewards.";
  if (observed) {
    const selector = byId("destination");
    selector.replaceChildren(...data.pages.filter(page=>data.reachable.includes(page.id)).map(page=>{
      const option = cell("option", data.labels[page.id] + " · HTTP " + (page.status ?? "—"));
      option.value = page.id;
      return option;
    }));
    selector.value = data.goal;
    byId("destination-field").hidden = false;
  }
  byId("route-summary").textContent=displayNames[data.method]+" · cost "+route.cost+" · "+route.trace.length+" expanded";
  const entries=Object.entries(data.routes);
  table("comparison",["Method","Cost","Hops","Expanded","Route"],entries.map(([key,result])=>
    [displayNames[key],result.cost,result.path.length-1,result.trace.length,result.path.map(id=>data.labels[id]).join(" → ")]),
    entries.findIndex(([key])=>key===data.method));
  const weighted=["ucs","astar"].includes(data.method);
  table("trace", weighted?["Node","g","h","f"]:["Node","Accumulated route cost"],
    route.trace.map(row=>weighted?[data.labels[row.node],row.g,row.h,row.f]:[data.labels[row.node],row.g]));
  const belief=data.belief;
  byId("posterior").textContent=percent(belief.initial)+" → "+percent(belief.posterior);
  table("belief-table",["Observation","P(E|H)","P(E|¬H)","Posterior"],belief.steps.map(row=>
    [row.signal,row.likelihood_phishing,row.likelihood_benign,percent(row.posterior)]));
  const decision=data.decision;
  byId("decision").textContent=decision.recommended;
  byId("iterations").textContent=decision.iterations+" Bellman iterations · γ = "+decision.gamma;
  const actions=Object.entries(decision.actions);
  table("actions",["Action","E[R]","P(pending)","Q"],actions.map(([name,row])=>
    [name,n3(row.reward),row.pending_probability,n3(row.q)]),actions.findIndex(([name])=>name===decision.recommended));
  byId("results").hidden=false;
}
async function post(path, body) {
  const response = await fetch(path, {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Check the input and try again.");
  return result;
}

const analyzeButton = byId("controls").querySelector("button");
const collectButton = byId("site-controls").querySelector("button");
let pending = false;

function setPending(busy) {
  pending = busy;
  analyzeButton.disabled = busy || (isWebsite() && currentSnapshot === null);
  collectButton.disabled = busy;
  byId("mode").disabled = busy;
}

function notify(message, error = false) {
  const notice = byId("notice");
  notice.textContent = message;
  notice.classList.toggle("demo-error", error);
}

function analyzeCurrent() {
  const website = isWebsite();
  return post("/api/darkphish/analyze", {
    method: byId("method").value,
    scenario: byId("scenario").value,
    snapshot: website ? currentSnapshot : null,
    destination: website ? byId("destination").value || null : null,
  }).then(fill);
}

async function run(collect = false) {
  if (pending || (!collect && isWebsite() && !currentSnapshot)) return;
  setPending(true);
  notify(collect ? "Collecting public pages…" : "Calculating…");
  try {
    if (collect) {
      currentSnapshot = null;
      byId("destination").replaceChildren();
      byId("destination-field").hidden = true;
      const data = await post("/api/darkphish/collect", {target: byId("target").value.trim()});
      currentSnapshot = data.snapshot;
    }
    await analyzeCurrent();
    notify("");
  } catch (error) {
    byId("results").hidden = true;
    notify(error.message, true);
  } finally {
    setPending(false);
  }
}

byId("controls").addEventListener("submit", event => {event.preventDefault(); run();});
byId("site-controls").addEventListener("submit", event => {event.preventDefault(); run(true);});
byId("mode").addEventListener("change", () => {
  const website = isWebsite();
  byId("site-controls").hidden = !website;
  byId("scenario-field").hidden = website;
  byId("destination-field").hidden = true;
  byId("results").hidden = true;
  notify(website && !currentSnapshot ? "Enter a public URL and collect a snapshot." : "");
  setPending(false);
  if (!website || currentSnapshot) run();
});
const target = new URLSearchParams(location.search).get("target");
if (target) {
  byId("target").value = target;
  byId("mode").value = "site";
  byId("mode").dispatchEvent(new Event("change"));
} else {
  run();
}
