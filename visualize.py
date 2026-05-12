"""
visualize.py — читает topology.json и генерирует topology_report.html
с интерактивной картой сети
"""

import json
import os
from pathlib import Path



HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Network Topology</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600&family=Space+Grotesk:wght@300;500;700&display=swap');

  :root {
    --bg: #0a0e1a;
    --panel: #0f1628;
    --border: #1e2d4a;
    --accent: #00d4ff;
    --accent2: #7b2fff;
    --green: #00ff88;
    --warn: #ff6b35;
    --text: #c8d8f0;
    --muted: #4a6080;
    --node-core: #00d4ff;
    --node-access: #7b2fff;
    --node-router: #00ff88;
    --link: #1e3a5f;
    --link-hover: #00d4ff;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Space Grotesk', sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* grid bg */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }

  header {
    position: relative;
    z-index: 10;
    padding: 20px 32px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(15,22,40,0.9);
    backdrop-filter: blur(10px);
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .logo-icon {
    width: 36px; height: 36px;
    border: 2px solid var(--accent);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }

  h1 {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: #fff;
  }

  h1 span { color: var(--accent); }

  .meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
  }

  .stats-bar {
    display: flex;
    gap: 4px;
  }

  .stat {
    padding: 6px 14px;
    border: 1px solid var(--border);
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    background: rgba(0,212,255,0.04);
  }

  .stat b { color: var(--accent); }

  .main {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: 1fr 300px;
    height: calc(100vh - 73px);
  }

  /* ── Graph ── */
  #graph-wrap {
    position: relative;
    overflow: hidden;
  }

  #graph {
    width: 100%;
    height: 100%;
  }

  .link {
    stroke: var(--link);
    stroke-width: 2;
    transition: stroke 0.2s;
  }

  .link:hover { stroke: var(--link-hover); }

  .link-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    fill: var(--muted);
    pointer-events: none;
  }

  .node circle {
    stroke-width: 2.5;
    cursor: pointer;
    transition: r 0.2s, filter 0.2s;
  }

  .node circle:hover {
    filter: brightness(1.4) drop-shadow(0 0 8px currentColor);
  }

  .node.selected circle {
    stroke-width: 4;
    filter: brightness(1.5) drop-shadow(0 0 12px currentColor);
  }

  .node text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    fill: var(--text);
    pointer-events: none;
    text-anchor: middle;
    dominant-baseline: middle;
  }

  .node .label {
    font-size: 10px;
    fill: var(--muted);
    dominant-baseline: auto;
  }

  /* pulse ring for selected */
  .pulse-ring {
    fill: none;
    stroke-width: 1;
    opacity: 0;
  }

  .node.selected .pulse-ring {
    animation: pulse 1.5s ease-out infinite;
  }

  @keyframes pulse {
    0%   { r: 18px; opacity: 0.6; }
    100% { r: 36px; opacity: 0; }
  }

  /* ── Sidebar ── */
  .sidebar {
    border-left: 1px solid var(--border);
    background: var(--panel);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .sidebar-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
  }

  .device-list {
    overflow-y: auto;
    flex: 1;
    padding: 8px;
  }

  .device-list::-webkit-scrollbar { width: 4px; }
  .device-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

  .device-item {
    padding: 10px 12px;
    border-radius: 8px;
    margin-bottom: 4px;
    cursor: pointer;
    transition: background 0.15s;
    border: 1px solid transparent;
  }

  .device-item:hover { background: rgba(0,212,255,0.06); }
  .device-item.active {
    background: rgba(0,212,255,0.08);
    border-color: rgba(0,212,255,0.2);
  }

  .device-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 600;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .device-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .device-ip {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--muted);
    margin-top: 3px;
    padding-left: 16px;
  }

  .device-neighbors {
    font-size: 10px;
    color: var(--muted);
    margin-top: 3px;
    padding-left: 16px;
  }

  /* ── Info panel ── */
  .info-panel {
    border-top: 1px solid var(--border);
    padding: 16px 20px;
    min-height: 160px;
  }

  .info-panel h3 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: var(--accent);
    margin-bottom: 12px;
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    padding: 4px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
  }

  .info-row .key { color: var(--muted); font-family: 'JetBrains Mono', monospace; }
  .info-row .val { color: var(--text); font-family: 'JetBrains Mono', monospace; }

  .neighbor-tag {
    display: inline-block;
    background: rgba(123,47,255,0.15);
    border: 1px solid rgba(123,47,255,0.3);
    color: #b080ff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    padding: 2px 7px;
    border-radius: 4px;
    margin: 2px 2px 2px 0;
  }

  .empty-info {
    color: var(--muted);
    font-size: 12px;
    font-style: italic;
    margin-top: 8px;
  }

  /* zoom controls */
  .zoom-controls {
    position: absolute;
    bottom: 20px;
    left: 20px;
    display: flex;
    gap: 6px;
    z-index: 10;
  }

  .zoom-btn {
    width: 32px; height: 32px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: rgba(15,22,40,0.9);
    color: var(--text);
    font-size: 16px;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: border-color 0.15s, color 0.15s;
  }

  .zoom-btn:hover { border-color: var(--accent); color: var(--accent); }

  .legend {
    position: absolute;
    bottom: 20px;
    right: 20px;
    background: rgba(15,22,40,0.85);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    z-index: 10;
  }

  .legend-item {
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 5px;
  }

  .legend-dot {
    width: 10px; height: 10px; border-radius: 50%;
  }
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">⬡</div>
    <div>
      <h1>Network <span>Topology</span></h1>
      <div class="meta">Сгенерировано: __GENERATED_AT__</div>
    </div>
  </div>
  <div class="stats-bar">
    <div class="stat">Устройств: <b>__DEVICE_COUNT__</b></div>
    <div class="stat">Связей: <b>__LINK_COUNT__</b></div>
  </div>
</header>

<div class="main">
  <div id="graph-wrap">
    <svg id="graph"></svg>
    <div class="zoom-controls">
      <button class="zoom-btn" onclick="zoomIn()">+</button>
      <button class="zoom-btn" onclick="zoomOut()">−</button>
      <button class="zoom-btn" onclick="zoomReset()" title="Reset">⌂</button>
    </div>
    <div class="legend">
      <div class="legend-item"><div class="legend-dot" style="background:#00d4ff"></div> Core / Distribution</div>
      <div class="legend-item"><div class="legend-dot" style="background:#7b2fff"></div> Access Switch</div>
      <div class="legend-item"><div class="legend-dot" style="background:#00ff88"></div> Router</div>
    </div>
  </div>

  <div class="sidebar">
    <div class="sidebar-header">Устройства</div>
    <div class="device-list" id="device-list"></div>
    <div class="info-panel" id="info-panel">
      <div class="empty-info">Выбери устройство на схеме или в списке</div>
    </div>
  </div>
</div>

<script>
const TOPOLOGY = __TOPOLOGY_JSON__;

// ── Build graph data ─────────────────────────────────────────────────────────
const nodes = [];
const links = [];
const nodeMap = {};

Object.entries(TOPOLOGY.devices).forEach(([name, data]) => {
  const type = name.toLowerCase().includes("router") || name.toLowerCase().startsWith("r")
    ? "router"
    : name.toLowerCase().includes("core") || name.toLowerCase().includes("dist")
    ? "core"
    : "access";
  const node = { id: name, ip: data.ip, type, neighbors: data.neighbors, error: data.error };
  nodes.push(node);
  nodeMap[name] = node;
});

const seen = new Set();
Object.entries(TOPOLOGY.devices).forEach(([name, data]) => {
  (data.neighbors || []).forEach(n => {
    const key = [name, n.neighbor].sort().join("--");
    if (!seen.has(key) && nodeMap[n.neighbor]) {
      seen.add(key);
      links.push({
        source: name,
        target: n.neighbor,
        sourcePort: n.local_port,
        targetPort: n.neighbor_port
      });
    }
  });
});

// ── Color map ────────────────────────────────────────────────────────────────
const colors = { core: "#00d4ff", access: "#7b2fff", router: "#00ff88" };

// ── D3 Force simulation ──────────────────────────────────────────────────────
const svg = d3.select("#graph");
const wrap = document.getElementById("graph-wrap");

let W = wrap.clientWidth, H = wrap.clientHeight;
svg.attr("width", W).attr("height", H);

const g = svg.append("g");

const zoom = d3.zoom()
  .scaleExtent([0.3, 3])
  .on("zoom", e => g.attr("transform", e.transform));
svg.call(zoom);

const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(130))
  .force("charge", d3.forceManyBody().strength(-400))
  .force("center", d3.forceCenter(W / 2, H / 2))
  .force("collision", d3.forceCollide(50));

// Links
const linkSel = g.append("g")
  .selectAll("line")
  .data(links)
  .join("line")
  .attr("class", "link");

// Link labels (port names)
const linkLabelSel = g.append("g")
  .selectAll("text")
  .data(links)
  .join("text")
  .attr("class", "link-label")
  .text(d => `${d.sourcePort} ↔ ${d.targetPort}`);

// Nodes
const nodeSel = g.append("g")
  .selectAll("g")
  .data(nodes)
  .join("g")
  .attr("class", "node")
  .call(d3.drag()
    .on("start", (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
    .on("drag",  (e, d) => { d.fx = e.x; d.fy = e.y; })
    .on("end",   (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
  )
  .on("click", (e, d) => selectDevice(d.id));

nodeSel.append("circle")
  .attr("class", "pulse-ring")
  .attr("r", 18)
  .attr("stroke", d => colors[d.type]);

const radius = d => d.type === "core" ? 18 : d.type === "router" ? 16 : 14;

nodeSel.append("circle")
  .attr("r", radius)
  .attr("fill", d => colors[d.type] + "22")
  .attr("stroke", d => colors[d.type]);

nodeSel.append("text")
  .attr("dy", "0.35em")
  .text(d => d.id.length > 12 ? d.id.slice(0, 11) + "…" : d.id);

nodeSel.append("text")
  .attr("class", "label")
  .attr("dy", d => radius(d) + 14)
  .text(d => d.ip);

simulation.on("tick", () => {
  linkSel
    .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);

  linkLabelSel
    .attr("x", d => (d.source.x + d.target.x) / 2)
    .attr("y", d => (d.source.y + d.target.y) / 2);

  nodeSel.attr("transform", d => `translate(${d.x},${d.y})`);
});

// ── Sidebar device list ──────────────────────────────────────────────────────
const listEl = document.getElementById("device-list");

nodes.forEach(n => {
  const div = document.createElement("div");
  div.className = "device-item";
  div.id = `item-${n.id}`;
  div.innerHTML = `
    <div class="device-name">
      <div class="device-dot" style="background:${colors[n.type]}"></div>
      ${n.id}
    </div>
    <div class="device-ip">${n.ip}</div>
    <div class="device-neighbors">${(n.neighbors||[]).length} соседей</div>
  `;
  div.onclick = () => selectDevice(n.id);
  listEl.appendChild(div);
});

// ── Select device ────────────────────────────────────────────────────────────
let selected = null;

function selectDevice(id) {
  if (selected === id) { selected = null; updateSelection(null); return; }
  selected = id;
  updateSelection(id);
}

function updateSelection(id) {
  // Nodes
  nodeSel.classed("selected", d => d.id === id);

  // Links — highlight connected
  linkSel.attr("stroke", d =>
    id && (d.source.id === id || d.target.id === id)
      ? "var(--accent)"
      : id ? "rgba(30,58,95,0.3)" : "var(--link)"
  ).attr("stroke-width", d =>
    id && (d.source.id === id || d.target.id === id) ? 3 : 2
  );

  // Sidebar list
  document.querySelectorAll(".device-item").forEach(el => el.classList.remove("active"));
  if (id) document.getElementById(`item-${id}`)?.classList.add("active");

  // Info panel
  const panel = document.getElementById("info-panel");
  if (!id) {
    panel.innerHTML = `<div class="empty-info">Выбери устройство на схеме или в списке</div>`;
    return;
  }

  const node = nodeMap[id];
  const neighborTags = (node.neighbors || [])
    .map(n => `<span class="neighbor-tag">${n.neighbor}</span>`)
    .join("");

  panel.innerHTML = `
    <h3>${id}</h3>
    <div class="info-row"><span class="key">IP</span><span class="val">${node.ip}</span></div>
    <div class="info-row"><span class="key">Тип</span><span class="val">${node.type}</span></div>
    <div class="info-row"><span class="key">Соседей</span><span class="val">${(node.neighbors||[]).length}</span></div>
    ${node.error ? `<div class="info-row"><span class="key" style="color:var(--warn)">Ошибка</span><span class="val" style="color:var(--warn)">${node.error}</span></div>` : ""}
    <div style="margin-top:10px; font-size:10px; color:var(--muted); font-family:'JetBrains Mono',monospace; margin-bottom:6px;">СОСЕДИ</div>
    ${neighborTags || '<span style="color:var(--muted);font-size:11px">нет соседей</span>'}
  `;
}

// ── Zoom controls ────────────────────────────────────────────────────────────
function zoomIn()    { svg.transition().call(zoom.scaleBy, 1.4); }
function zoomOut()   { svg.transition().call(zoom.scaleBy, 0.7); }
function zoomReset() { svg.transition().call(zoom.transform, d3.zoomIdentity.translate(W/2, H/2).scale(1).translate(-W/2, -H/2)); }

window.addEventListener("resize", () => {
  W = wrap.clientWidth; H = wrap.clientHeight;
  svg.attr("width", W).attr("height", H);
  simulation.force("center", d3.forceCenter(W/2, H/2)).alpha(0.3).restart();
});
</script>
</body>
</html>
"""


def build_html(topology: dict) -> str:
    devices = topology.get("devices", {})
    generated_at = topology.get("generated_at", "—")

    # Подсчёт уникальных связей
    seen = set()
    for name, data in devices.items():
        for n in data.get("neighbors", []):
            key = tuple(sorted([name, n["neighbor"]]))
            seen.add(key)
    link_count = len(seen)

    html = HTML_TEMPLATE
    html = html.replace("__TOPOLOGY_JSON__", json.dumps(topology, ensure_ascii=False))
    html = html.replace("__GENERATED_AT__", generated_at)
    html = html.replace("__DEVICE_COUNT__", str(len(devices)))
    html = html.replace("__LINK_COUNT__", str(link_count))
    return html


if __name__ == "__main__":
    topo_path = "topology.json"

    if not os.path.exists(topo_path):
        print(f"Ошибка: {topo_path} не найден.")
        print("Сначала запусти collector.py чтобы собрать данные с устройств.")
        exit(1)

    with open(topo_path, encoding="utf-8") as f:
        topology = json.load(f)
    print(f"Загружен {topo_path}")

    html = build_html(topology)
    out = "topology_report.html"
    Path(out).write_text(html, encoding="utf-8")
    print(f"Отчёт сохранён: {out}")
    print("Открой topology_report.html в браузере")
