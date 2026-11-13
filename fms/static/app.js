// PinkLAB Booth FMS front end: one SSE stream for state, small POSTs for commands.
const $ = (id) => document.getElementById(id);
const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) })
  .then((r) => r.json()).catch(() => ({ ok: false, error: "서버 연결 실패" }));

let state = null, places = [], cupColors = {}, mapMeta = null, mapImg = null, mapVersion = null;
const canvas = $("map"), ctx = canvas.getContext("2d");
// view: metres -> canvas pixels. Default fits the booth (X 0..9, Y -6..0) with a margin.
const view = { scale: 60, ox: 0, oy: 0, fitted: false };

// ------------------------------------------------------------------ static info
fetch("/api/static_info").then((r) => r.json()).then((d) => {
  places = d.places; cupColors = d.cup_colors;
  const box = $("places");
  for (const p of places) {
    const b = document.createElement("button");
    b.textContent = p.label;
    if (p.station) b.classList.add("station");
    b.onclick = () => post("/api/goal", { place: p.key }).then(showError);
    box.appendChild(b);
  }
});

function showError(r) { if (r && !r.ok) addLocal("시스템", r.error, "error"); }
function addLocal(who, text, kind) { const div = msgDiv({ who, text, kind, t: new Date().toTimeString().slice(0, 8) }); $("chat").appendChild(div); $("chat").scrollTop = 1e9; }

// ------------------------------------------------------------------ map
function resize() {
  const r = canvas.getBoundingClientRect();
  canvas.width = Math.round(r.width * devicePixelRatio); canvas.height = Math.round(r.height * devicePixelRatio);
  if (!view.fitted) fit();
  draw();
}
function fit() {
  const w = canvas.width, h = canvas.height, X0 = -0.6, X1 = 9.6, Y0 = -6.6, Y1 = 0.6;
  view.scale = Math.min(w / (X1 - X0), h / (Y1 - Y0));
  view.ox = (w - (X1 - X0) * view.scale) / 2 - X0 * view.scale;
  view.oy = (h - (Y1 - Y0) * view.scale) / 2 + Y1 * view.scale;
  view.fitted = true;
}
const toPx = (x, y) => [view.ox + x * view.scale, view.oy - y * view.scale];
const toWorld = (px, py) => [(px - view.ox) / view.scale, (view.oy - py) / view.scale];

function loadMap() {
  fetch("/api/map").then((r) => r.json()).then((m) => {
    if (!m.resolution) return;
    mapMeta = m;
    const img = new Image();
    img.onload = () => { mapImg = img; draw(); };
    img.src = "/api/map.png?v=" + m.version;
  });
}

let drag = null;   // {x, y, x2, y2} world metres while choosing a goal heading
function draw() {
  const w = canvas.width, h = canvas.height, s = view.scale, dpr = devicePixelRatio;
  ctx.fillStyle = "#cfcfd2"; ctx.fillRect(0, 0, w, h);
  if (mapImg && mapMeta) {
    const [x, y] = toPx(mapMeta.origin[0], mapMeta.origin[1] + mapMeta.height * mapMeta.resolution);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(mapImg, x, y, mapMeta.width * mapMeta.resolution * s, mapMeta.height * mapMeta.resolution * s);
  }
  // booth outline
  ctx.strokeStyle = "#de6ba7"; ctx.lineWidth = 2 * dpr; ctx.setLineDash([6 * dpr, 4 * dpr]);
  { const [a, b] = toPx(0, 0); ctx.strokeRect(a, b, 9 * s, 6 * s); }
  ctx.setLineDash([]);
  if (!state) return;
  // places
  ctx.font = `${12 * dpr}px sans-serif`; ctx.textAlign = "center";
  for (const p of places) {
    const [x, y] = toPx(p.goal[0], p.goal[1]);
    ctx.beginPath(); ctx.arc(x, y, 6 * dpr, 0, 7);
    ctx.fillStyle = p.station ? "#f8d5e4" : "#fff"; ctx.fill();
    ctx.lineWidth = 2 * dpr; ctx.strokeStyle = p.station ? "#de6ba7" : "#4863ae"; ctx.stroke();
    ctx.fillStyle = "#231f20"; ctx.fillText(p.label, x, p.station ? y + 18 * dpr : y - 10 * dpr);   // stations below, others above
  }
  // lidar
  ctx.fillStyle = "rgba(229,57,53,.75)";
  for (const [x, y] of state.scan) { const [a, b] = toPx(x, y); ctx.fillRect(a - 1.5 * dpr, b - 1.5 * dpr, 3 * dpr, 3 * dpr); }
  // Nav2 path
  if (state.plan.length > 1) {
    ctx.strokeStyle = "#de6ba7"; ctx.lineWidth = 3 * dpr; ctx.beginPath();
    state.plan.forEach(([x, y], i) => { const [a, b] = toPx(x, y); i ? ctx.lineTo(a, b) : ctx.moveTo(a, b); });
    ctx.stroke();
  }
  // goal
  const g = state.nav && state.nav.goal;
  if (g && state.nav.state === "이동 중") arrow(g[0], g[1], g[2], "#de6ba7");
  // cups
  for (const [name, p] of Object.entries(state.cups)) {
    const [x, y] = toPx(p[0], p[1]), c = cupColors[name] || [0.5, 0.5, 0.5];
    ctx.beginPath(); ctx.arc(x, y, 5 * dpr, 0, 7);
    ctx.fillStyle = `rgb(${c.map((v) => Math.round(v * 255)).join(",")})`; ctx.fill();
    ctx.lineWidth = 1.5 * dpr; ctx.strokeStyle = "#231f20"; ctx.stroke();
  }
  // robot: 0.76 x 0.64 m footprint + heading
  if (state.pose) {
    const [rx, ry, yaw] = state.pose, [a, b] = toPx(rx, ry);
    ctx.save(); ctx.translate(a, b); ctx.rotate(-yaw);
    ctx.fillStyle = "rgba(72,99,174,.85)"; ctx.fillRect(-0.38 * s, -0.32 * s, 0.76 * s, 0.64 * s);
    ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.moveTo(0.34 * s, 0); ctx.lineTo(0.05 * s, -0.16 * s); ctx.lineTo(0.05 * s, 0.16 * s); ctx.fill();
    ctx.restore();
  }
  if (drag) {
    const yaw = Math.atan2(drag.y2 - drag.y, drag.x2 - drag.x);
    arrow(drag.x, drag.y, yaw, "#4863ae");
  }
}
function arrow(x, y, yaw, color) {
  const [a, b] = toPx(x, y), L = 0.5 * view.scale, dpr = devicePixelRatio;
  ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 3 * dpr;
  ctx.beginPath(); ctx.arc(a, b, 5 * dpr, 0, 7); ctx.fill();
  const ex = a + L * Math.cos(yaw), ey = b - L * Math.sin(yaw);
  ctx.beginPath(); ctx.moveTo(a, b); ctx.lineTo(ex, ey); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(ex, ey);
  ctx.lineTo(ex - 10 * dpr * Math.cos(yaw - 0.5), ey + 10 * dpr * Math.sin(yaw - 0.5));
  ctx.lineTo(ex - 10 * dpr * Math.cos(yaw + 0.5), ey + 10 * dpr * Math.sin(yaw + 0.5)); ctx.fill();
}

function eventWorld(e) {
  const r = canvas.getBoundingClientRect();
  return toWorld((e.clientX - r.left) * devicePixelRatio, (e.clientY - r.top) * devicePixelRatio);
}
canvas.addEventListener("pointerdown", (e) => { const [x, y] = eventWorld(e); drag = { x, y, x2: x, y2: y }; canvas.setPointerCapture(e.pointerId); });
canvas.addEventListener("pointermove", (e) => {
  const [x, y] = eventWorld(e);
  $("maptip").textContent = `x ${x.toFixed(2)}  y ${y.toFixed(2)}`;
  if (drag) { drag.x2 = x; drag.y2 = y; draw(); }
});
canvas.addEventListener("pointerup", () => {
  if (!drag) return;
  const d = drag; drag = null;
  let yaw;
  if (Math.hypot(d.x2 - d.x, d.y2 - d.y) > 0.15) yaw = Math.atan2(d.y2 - d.y, d.x2 - d.x);
  else if (state && state.pose) yaw = Math.atan2(d.y - state.pose[1], d.x - state.pose[0]);   // face the way it travels
  else yaw = 0;
  post("/api/goal", { x: d.x, y: d.y, yaw }).then(showError);
  draw();
});
canvas.addEventListener("wheel", (e) => {
  e.preventDefault();
  const r = canvas.getBoundingClientRect(), px = (e.clientX - r.left) * devicePixelRatio, py = (e.clientY - r.top) * devicePixelRatio;
  const [wx, wy] = toWorld(px, py), k = e.deltaY < 0 ? 1.15 : 1 / 1.15;
  view.scale *= k; view.ox = px - wx * view.scale; view.oy = py + wy * view.scale; draw();
}, { passive: false });
canvas.addEventListener("dblclick", () => { view.fitted = false; fit(); draw(); });
window.addEventListener("resize", resize);

// ------------------------------------------------------------------ state stream
function connect() {
  const es = new EventSource("/api/stream");
  es.onopen = () => { $("conn").textContent = "연결됨"; $("conn").classList.remove("off"); };
  es.onerror = () => { $("conn").textContent = "끊김"; $("conn").classList.add("off"); };
  es.onmessage = (ev) => { state = JSON.parse(ev.data); update(); };
}
let chatCount = 0;
function update() {
  const s = state;
  $("simt").textContent = s.sim_time;
  if (s.map_version !== mapVersion) { mapVersion = s.map_version; loadMap(); }
  $("pose").textContent = s.pose ? `x ${s.pose[0].toFixed(2)} · y ${s.pose[1].toFixed(2)} · ${(s.pose[2] * 180 / Math.PI).toFixed(0)}°` : "AMCL 대기";
  $("speed").textContent = `${s.twist[0].toFixed(2)} m/s · ${s.twist[1].toFixed(2)} rad/s`;
  const n = s.nav;
  $("nav").textContent = n.state + (n.label ? ` · ${n.label}` : "") + (n.state === "이동 중" && n.remaining != null ? ` · 남은 ${n.remaining} m` : "");
  const m = s.mission;
  $("mission").textContent = m.active ? `${m.step + 1}/${m.total} · ${m.detail}` : (s.busy ? "LLM 처리 중…" : "없음");
  $("world").textContent = s.world;
  const steps = $("steps");
  steps.innerHTML = "";
  if (m.steps.length) m.steps.forEach((t, i) => {
    const li = document.createElement("li"); li.textContent = t;
    if (m.active) li.className = i < m.step ? "done" : i === m.step ? "now" : "";
    steps.appendChild(li);
  });
  $("confirm").hidden = !s.pending;
  $("camon").checked = s.camera; $("camon").nextElementSibling.textContent = s.camera ? "켜짐" : "꺼짐"; $("camarea").hidden = !s.camera;
  if (s.camera && !$("camimg").getAttribute("src")) setCam();          // page reloaded while the camera was on
  if (s.chat.length !== chatCount) {
    const box = $("chat"); box.innerHTML = "";
    for (const c of s.chat) box.appendChild(msgDiv(c));
    box.scrollTop = 1e9; chatCount = s.chat.length;
  }
  draw();
}
function msgDiv(c) {
  const div = document.createElement("div");
  const cls = c.who === "사용자" ? "user" : c.who === "로봇" ? "robot" : "system";
  div.className = `msg ${cls} ${c.kind || ""}`;
  const who = document.createElement("span"); who.className = "who"; who.textContent = `${c.who} · ${c.t}`;
  div.appendChild(who); div.appendChild(document.createTextNode(c.text));
  return div;
}

// ------------------------------------------------------------------ manual drive
let driveTimer = null, driveDir = null;
function startDrive(v, w) {
  driveDir = [v, w];
  if (driveTimer) return;
  const tick = () => { const spd = +$("spd").value; post("/api/drive", { v: driveDir[0] * spd, w: driveDir[1] * Math.min(0.6, spd * 4) }); };
  tick(); driveTimer = setInterval(tick, 150);
}
function stopDrive() { clearInterval(driveTimer); driveTimer = null; document.querySelectorAll(".pad button").forEach((b) => b.classList.remove("held")); }
document.querySelectorAll(".pad button").forEach((b) => {
  if (b.id === "padstop") { b.onclick = () => post("/api/stop"); return; }
  b.addEventListener("pointerdown", (e) => { b.classList.add("held"); b.setPointerCapture(e.pointerId); startDrive(+b.dataset.v, +b.dataset.w); });
  for (const ev of ["pointerup", "pointercancel", "lostpointercapture"]) b.addEventListener(ev, stopDrive);
});
$("spd").oninput = () => { $("spdv").textContent = (+$("spd").value).toFixed(2); };
const KEYS = { w: [1, 0], arrowup: [1, 0], s: [-1, 0], arrowdown: [-1, 0], a: [0, 1], arrowleft: [0, 1], d: [0, -1], arrowright: [0, -1] };
const down = new Set();
window.addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
  const k = KEYS[e.key.toLowerCase()]; if (!k) return;
  e.preventDefault(); down.add(e.key.toLowerCase()); startDrive(...k);
});
window.addEventListener("keyup", (e) => { down.delete(e.key.toLowerCase()); if (!down.size) stopDrive(); });
$("estop").onclick = () => { stopDrive(); post("/api/stop"); };

// ------------------------------------------------------------------ camera
$("camon").onchange = () => post("/api/camera", { on: $("camon").checked }).then(() => setCam());
$("camsel").onchange = setCam;
function setCam() {
  if ($("camon").checked || (state && state.camera)) $("camimg").src = `/camera/${$("camsel").value}.mjpg?t=${Date.now()}`;
  else $("camimg").removeAttribute("src");
}

// ------------------------------------------------------------------ chat
function send(text) { if (text.trim()) post("/api/chat", { text }).then(showError); }
$("chatform").onsubmit = (e) => { e.preventDefault(); send($("chatin").value); $("chatin").value = ""; };
$("yes").onclick = () => send("응");
$("no").onclick = () => send("아니");
document.querySelectorAll(".examples button").forEach((b) => { b.onclick = () => send(b.textContent); });

resize(); connect();
