"use strict";

// ---------- Состояние / API ----------
const TOKEN_KEY = "swimbuoy_token";
const getToken = () => localStorage.getItem(TOKEN_KEY) || "";
const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
const clearToken = () => localStorage.removeItem(TOKEN_KEY);

async function api(path, opts = {}) {
  const headers = opts.headers || {};
  if (getToken()) headers["X-Athlete-Token"] = getToken();
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.json);
    delete opts.json;
  }
  const res = await fetch(path, { ...opts, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (e) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

// ---------- Админ (HTTP Basic) ----------
const ADMIN_KEY = "swimbuoy_admin";
const getAdmin = () => localStorage.getItem(ADMIN_KEY) || "";
const setAdmin = (b64) => localStorage.setItem(ADMIN_KEY, b64);
const clearAdmin = () => localStorage.removeItem(ADMIN_KEY);

async function adminApi(path, opts = {}) {
  const headers = opts.headers || {};
  headers["Authorization"] = "Basic " + getAdmin();
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.json);
    delete opts.json;
  }
  const res = await fetch(path, { ...opts, headers });
  if (res.status === 401) { clearAdmin(); throw new Error("Нужен вход админа"); }
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (e) {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

const app = document.getElementById("app");
const nav = document.getElementById("nav");

function toast(msg) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2600);
}

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function fmtDist(m) {
  if (m == null) return "—";
  return m >= 1000 ? (m / 1000).toFixed(2) + " км" : Math.round(m) + " м";
}
function fmtDur(s) {
  if (s == null) return "—";
  const m = Math.floor(s / 60), sec = Math.round(s % 60);
  return m + ":" + String(sec).padStart(2, "0");
}
function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("ru-RU", { dateStyle: "medium", timeStyle: "short" });
}

// ---------- Роутер ----------
function navView() {
  if (getToken()) {
    nav.innerHTML = `<a href="#/">Тренировки</a><a href="#/routes">Маршруты</a>
      <a href="#/upload">Загрузить</a><a href="#/admin">Админ</a><a href="#" id="logout">Выйти</a>`;
    nav.querySelector("#logout").onclick = (e) => { e.preventDefault(); clearToken(); location.hash = "#/"; };
  } else {
    nav.innerHTML = `<a href="#/admin">Админ</a>`;
  }
}

window.addEventListener("hashchange", route);
window.addEventListener("load", route);

async function route() {
  navView();
  const hash = location.hash || "#/";
  const parts = hash.slice(2).split("/"); // убираем "#/"

  // Публичный share — без токена.
  if (parts[0] === "share" && parts[1]) return viewShare(parts[1]);

  // Админка — отдельная авторизация (Basic), без токена спортсмена.
  if (parts[0] === "admin") return viewAdmin(parts[1]);

  if (!getToken()) return viewLogin();

  try {
    if (parts[0] === "" ) return viewDashboard();
    if (parts[0] === "routes" && parts[1] === "new") return viewRouteEdit(null);
    if (parts[0] === "routes" && parts[1] && parts[2] === "edit") return viewRouteEdit(parts[1]);
    if (parts[0] === "routes" && parts[1]) return viewRoute(parts[1]);
    if (parts[0] === "routes") return viewRoutes();
    if (parts[0] === "upload") return viewUpload();
    if (parts[0] === "activities" && parts[1]) return viewActivity(parts[1]);
    viewDashboard();
  } catch (e) {
    app.innerHTML = `<div class="card"><h2>Ошибка</h2><p class="muted">${esc(e.message)}</p></div>`;
  }
}

// ---------- Вход ----------
function viewLogin() {
  app.innerHTML = `
    <div class="center-panel card">
      <h1>Вход</h1>
      <p class="subtitle">Введите токен спортсмена. Его выдаёт администратор
        (или возьмите из вывода <code>seed.py</code>).</p>
      <label>Токен</label>
      <input id="token" placeholder="напр. xQ8…" autofocus />
      <div class="btn-row"><button class="btn" id="go">Войти</button></div>
    </div>`;
  const submit = async () => {
    const t = app.querySelector("#token").value.trim();
    if (!t) return;
    setToken(t);
    try {
      await api("/api/athletes/me");
      location.hash = "#/";
    } catch (e) {
      clearToken();
      toast("Неверный токен");
    }
  };
  app.querySelector("#go").onclick = submit;
  app.querySelector("#token").onkeydown = (e) => { if (e.key === "Enter") submit(); };
}

// ---------- Дашборд (тренировки) ----------
async function viewDashboard() {
  app.innerHTML = `<h1>Тренировки</h1><p class="subtitle">Заплывы с часов и загруженные вручную.</p>
    <div class="btn-row">
      <a class="btn" href="#/upload">⬆ Загрузить трек</a>
      <a class="btn secondary" href="#/routes">Маршруты</a>
    </div>
    <div id="list" class="empty">Загрузка…</div>`;
  const items = await api("/api/activities");
  const el = app.querySelector("#list");
  if (!items.length) { el.innerHTML = `<div class="empty">Пока нет тренировок. Загрузите GPX или отправьте заплыв с часов.</div>`; return; }
  el.className = "grid";
  el.innerHTML = items.map((a) => `
    <div class="card clickable" onclick="location.hash='#/activities/${a.id}'">
      <div style="display:flex;justify-content:space-between;align-items:start;gap:8px">
        <strong>${esc(a.name)}</strong>
        ${a.is_public ? '<span class="pill info">share</span>' : ""}
      </div>
      <div class="muted" style="font-size:13px;margin-top:6px">${fmtDate(a.recorded_at || a.created_at)}</div>
      <div style="margin-top:12px;display:flex;gap:18px">
        <div><div style="font-weight:700">${fmtDist(a.distance_m)}</div><div class="muted" style="font-size:12px">дистанция</div></div>
        <div><div style="font-weight:700">${fmtDur(a.duration_s)}</div><div class="muted" style="font-size:12px">время</div></div>
        <div><div style="font-weight:700">${a.buoys_taken ?? "—"}/${a.buoys_total ?? "—"}</div><div class="muted" style="font-size:12px">буи</div></div>
      </div>
      <div class="muted" style="font-size:12px;margin-top:10px">источник: ${esc(a.source)}</div>
    </div>`).join("");
}

// ---------- Маршруты ----------
async function viewRoutes() {
  app.innerHTML = `<h1>Маршруты</h1><p class="subtitle">Точки буёв для часов и отчётов.</p>
    <div class="btn-row"><a class="btn" href="#/routes/new">＋ Новый маршрут</a></div>
    <div id="list" class="empty">Загрузка…</div>`;
  const items = await api("/api/routes");
  const el = app.querySelector("#list");
  if (!items.length) { el.innerHTML = `<div class="empty">Маршрутов нет. Создайте первый.</div>`; return; }
  el.className = "grid";
  el.innerHTML = items.map((r) => `
    <div class="card clickable" onclick="location.hash='#/routes/${r.id}'">
      <div style="display:flex;justify-content:space-between;gap:8px">
        <strong>${esc(r.name)}</strong>
        ${r.is_public ? '<span class="pill info">public</span>' : ""}
      </div>
      <div class="muted" style="font-size:13px;margin-top:8px">${r.points_count} буёв · радиус ${r.arrivalMRadius ?? r.arrivalRadiusM} м</div>
      <div class="muted" style="font-size:12px;margin-top:6px">обновлён ${fmtDate(r.updated_at)}</div>
    </div>`).join("");
}

async function viewRoute(id) {
  const r = await api(`/api/routes/${id}`);
  const order = (r.session && r.session.order) || Object.keys(r.points);
  app.innerHTML = `
    <h1>${esc(r.name)}</h1>
    <p class="subtitle">${order.length} точек · радиус ${r.arrivalRadiusM} м · dwell ${r.dwellSec} с</p>
    <div class="btn-row">
      <a class="btn" href="/api/routes/${id}.gpx">⬇ GPX (на часы / карты)</a>
      <a class="btn secondary" href="/api/routes/${id}.json">⬇ JSON</a>
      ${r.owner ? `<a class="btn ghost" href="#/routes/${id}/edit">✎ Изменить</a>
      <button class="btn danger" id="del">Удалить</button>` : ""}
    </div>
    <div id="map" class="map"></div>
    <div class="legend"><span class="l-buoy">буй</span></div>
    <h2>Точки</h2>
    <table><thead><tr><th>#</th><th>ID</th><th>Имя</th><th>Координаты</th></tr></thead>
      <tbody>${order.map((pid, i) => {
        const p = r.points[pid]; if (!p) return "";
        return `<tr><td>${i + 1}</td><td>${esc(pid)}</td><td>${esc(p.name || "")}</td>
          <td class="muted">${p.lat.toFixed(6)}, ${p.lon.toFixed(6)}</td></tr>`;
      }).join("")}</tbody></table>`;

  // Карта маршрута.
  const map = L.map("map");
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map);
  const pts = [];
  if (r.start) { L.marker([r.start.lat, r.start.lon]).addTo(map).bindPopup("Старт"); pts.push([r.start.lat, r.start.lon]); }
  const line = [];
  if (r.start) line.push([r.start.lat, r.start.lon]);
  order.forEach((pid, i) => {
    const p = r.points[pid]; if (!p) return;
    L.circleMarker([p.lat, p.lon], { radius: 8, color: "#fbbf24", fillColor: "#fbbf24", fillOpacity: .9 })
      .addTo(map).bindPopup(`${i + 1}. ${esc(p.name || pid)}`);
    pts.push([p.lat, p.lon]); line.push([p.lat, p.lon]);
  });
  L.polyline(line, { color: "#2dd4bf", weight: 2, dashArray: "6 6" }).addTo(map);
  if (pts.length) map.fitBounds(pts, { padding: [40, 40] });

  const del = app.querySelector("#del");
  if (del) del.onclick = async () => {
    if (!confirm("Удалить маршрут?")) return;
    await api(`/api/routes/${id}`, { method: "DELETE" });
    location.hash = "#/routes";
  };
}

async function viewRouteEdit(id) {
  let data = { name: "", arrivalRadiusM: 20, dwellSec: 4, orderMode: "fixed",
    points: { P1: { lat: 60.0, lon: 30.0, name: "Старт" } }, order: ["P1"], start: null, is_public: false };
  if (id) {
    const r = await api(`/api/routes/${id}`);
    data = {
      name: r.name, arrivalRadiusM: r.arrivalRadiusM, dwellSec: r.dwellSec,
      orderMode: (r.session && r.session.orderMode) || "fixed",
      points: r.points, order: (r.session && r.session.order) || Object.keys(r.points),
      start: r.start || null, is_public: !!r.is_public,
    };
  }
  app.innerHTML = `
    <h1>${id ? "Изменить маршрут" : "Новый маршрут"}</h1>
    <p class="subtitle">Координаты можно вставить вручную или кликом по карте (добавляет буй в конец).</p>
    <div class="row">
      <div><label>Название</label><input id="name" value="${esc(data.name)}" /></div>
      <div style="flex:0 0 120px"><label>Радиус, м</label><input id="rad" type="number" value="${data.arrivalRadiusM}" /></div>
      <div style="flex:0 0 120px"><label>Dwell, с</label><input id="dwell" type="number" value="${data.dwellSec}" /></div>
    </div>
    <label><input type="checkbox" id="pub" style="width:auto" ${data.is_public ? "checked" : ""}/> Публичный (виден другим и часам)</label>
    <div id="map" class="map" style="margin-top:14px"></div>
    <h2>Буи (по порядку)</h2>
    <div id="pts"></div>
    <div class="btn-row">
      <button class="btn secondary small" id="add">＋ Добавить буй</button>
    </div>
    <div class="btn-row"><button class="btn" id="save">Сохранить</button>
      <a class="btn ghost" href="#/routes">Отмена</a></div>`;

  const map = L.map("map").setView(
    [data.points[data.order[0]]?.lat || 60, data.points[data.order[0]]?.lon || 30], 14);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map);
  let markers = [];

  function nextId() {
    let n = 1;
    while (data.order.includes("P" + n)) n++;
    return "P" + n;
  }
  function renderPts() {
    const box = app.querySelector("#pts");
    box.innerHTML = data.order.map((pid, i) => {
      const p = data.points[pid];
      return `<div class="card" style="margin-bottom:8px"><div class="row" style="align-items:end">
        <div style="flex:0 0 60px"><label>ID</label><input value="${esc(pid)}" disabled /></div>
        <div><label>Имя</label><input data-f="name" data-id="${pid}" value="${esc(p.name || "")}" /></div>
        <div style="flex:0 0 130px"><label>Lat</label><input data-f="lat" data-id="${pid}" value="${p.lat}" /></div>
        <div style="flex:0 0 130px"><label>Lon</label><input data-f="lon" data-id="${pid}" value="${p.lon}" /></div>
        <div style="flex:0 0 auto"><button class="btn danger small" data-del="${pid}">✕</button></div>
      </div></div>`;
    }).join("");
    box.querySelectorAll("input[data-f]").forEach((inp) => {
      inp.onchange = () => {
        const pid = inp.dataset.id, f = inp.dataset.f;
        data.points[pid][f] = f === "name" ? inp.value : parseFloat(inp.value);
        renderMap();
      };
    });
    box.querySelectorAll("button[data-del]").forEach((b) => {
      b.onclick = () => {
        const pid = b.dataset.del;
        delete data.points[pid];
        data.order = data.order.filter((x) => x !== pid);
        renderPts(); renderMap();
      };
    });
  }
  function renderMap() {
    markers.forEach((m) => map.removeLayer(m));
    markers = [];
    const line = [];
    data.order.forEach((pid, i) => {
      const p = data.points[pid];
      const m = L.circleMarker([p.lat, p.lon], { radius: 8, color: "#fbbf24", fillColor: "#fbbf24", fillOpacity: .9 })
        .addTo(map).bindTooltip(`${i + 1}`);
      markers.push(m); line.push([p.lat, p.lon]);
    });
    markers.push(L.polyline(line, { color: "#2dd4bf", weight: 2, dashArray: "6 6" }).addTo(map));
  }
  map.on("click", (e) => {
    const pid = nextId();
    data.points[pid] = { lat: +e.latlng.lat.toFixed(6), lon: +e.latlng.lng.toFixed(6), name: "" };
    data.order.push(pid);
    renderPts(); renderMap();
  });
  app.querySelector("#add").onclick = () => {
    const c = map.getCenter(); const pid = nextId();
    data.points[pid] = { lat: +c.lat.toFixed(6), lon: +c.lng.toFixed(6), name: "" };
    data.order.push(pid); renderPts(); renderMap();
  };
  app.querySelector("#save").onclick = async () => {
    const body = {
      name: app.querySelector("#name").value.trim() || "Маршрут",
      arrivalRadiusM: parseInt(app.querySelector("#rad").value) || 20,
      dwellSec: parseInt(app.querySelector("#dwell").value) || 4,
      orderMode: data.orderMode,
      points: data.points, order: data.order,
      start: data.start, is_public: app.querySelector("#pub").checked,
    };
    if (!data.order.length) return toast("Добавьте хотя бы один буй");
    const saved = id
      ? await api(`/api/routes/${id}`, { method: "PUT", json: body })
      : await api("/api/routes", { method: "POST", json: body });
    location.hash = `#/routes/${saved.id}`;
  };
  renderPts(); renderMap();
}

// ---------- Загрузка трека ----------
async function viewUpload() {
  const routes = await api("/api/routes");
  app.innerHTML = `
    <h1>Загрузить трек</h1>
    <p class="subtitle">GPX, TCX или FIT. Привяжите к маршруту, чтобы построить отчёт по коридору.</p>
    <div class="card center-panel" style="margin-top:10px">
      <label>Файл трека</label>
      <input id="file" type="file" accept=".gpx,.tcx,.fit" />
      <label>Маршрут (для отчёта)</label>
      <select id="route"><option value="">— без маршрута —</option>
        ${routes.map((r) => `<option value="${r.id}">${esc(r.name)}</option>`).join("")}</select>
      <label>Название (необязательно)</label>
      <input id="name" placeholder="Заплыв 14.06" />
      <div class="btn-row"><button class="btn" id="go">Загрузить</button></div>
    </div>`;
  app.querySelector("#go").onclick = async () => {
    const f = app.querySelector("#file").files[0];
    if (!f) return toast("Выберите файл");
    const fd = new FormData();
    fd.append("file", f);
    const rid = app.querySelector("#route").value;
    if (rid) fd.append("route_id", rid);
    const nm = app.querySelector("#name").value.trim();
    if (nm) fd.append("name", nm);
    try {
      const a = await api("/api/activities/upload", { method: "POST", body: fd });
      location.hash = `#/activities/${a.id}`;
    } catch (e) { toast(e.message); }
  };
}

// ---------- Отчёт по тренировке ----------
function renderReportMap(elId, geojson) {
  const map = L.map(elId);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map);
  const bounds = [];
  const ll = (c) => [c[1], c[0]]; // geojson [lon,lat] -> leaflet [lat,lon]
  (geojson.features || []).forEach((f) => {
    const k = f.properties.kind, g = f.geometry;
    if (k === "corridor" && g.type === "Polygon") {
      L.polygon(g.coordinates[0].map(ll), { color: "#2dd4bf", weight: 0, fillColor: "#2dd4bf", fillOpacity: .12 }).addTo(map);
    } else if (k === "leg") {
      L.polyline(g.coordinates.map(ll), { color: "#2dd4bf", weight: 1.5, dashArray: "5 6", opacity: .7 }).addTo(map);
    } else if (k === "track") {
      const pts = g.coordinates.map(ll);
      L.polyline(pts, { color: "#38bdf8", weight: 3 }).addTo(map);
      pts.forEach((p) => bounds.push(p));
    } else if (k === "buoy") {
      const taken = f.properties.taken;
      L.circleMarker(ll(g.coordinates), { radius: 8, color: taken ? "#fbbf24" : "#f87171",
        fillColor: taken ? "#fbbf24" : "#f87171", fillOpacity: .9 })
        .addTo(map).bindPopup(`${esc(f.properties.name)}<br>ближе всего: ${f.properties.closest_m} м<br>${taken ? "взят" : "не взят"}`);
    } else if (k === "start") {
      L.marker(ll(g.coordinates)).addTo(map).bindPopup("Старт");
    }
  });
  if (bounds.length) map.fitBounds(bounds, { padding: [40, 40] });
}

function reportBody(report, container) {
  if (!report || !report.ok) {
    container.innerHTML += `<div class="card"><p class="muted">${esc((report && report.error) || "Отчёт не построен. Привяжите трек к маршруту.")}</p></div>`;
    return;
  }
  const s = report.summary;
  container.innerHTML += `
    <div class="stats">
      <div class="stat"><div class="v">${fmtDist(s.distance_m)}</div><div class="k">проплыто</div></div>
      <div class="stat"><div class="v">${fmtDur(s.duration_s)}</div><div class="k">время</div></div>
      <div class="stat"><div class="v">${s.pace_min_100m ?? "—"}</div><div class="k">мин/100м</div></div>
      <div class="stat"><div class="v">${s.buoys_taken}/${s.buoys_total}</div><div class="k">буёв взято</div></div>
      <div class="stat"><div class="v">${s.efficiency_pct != null ? s.efficiency_pct + "%" : "—"}</div><div class="k">эффективность</div></div>
      <div class="stat"><div class="v">${s.xte_overall ? s.xte_overall.p95 + " м" : "—"}</div><div class="k">XTE p95</div></div>
    </div>
    <div id="rmap" class="map"></div>
    <div class="legend"><span class="l-track">трек</span><span class="l-corridor">коридор</span>
      <span class="l-buoy">взят</span><span class="l-miss">не взят</span></div>
    <h2>Отклонение по плечам (cross-track)</h2>
    <table><thead><tr><th>Плечо</th><th>Длина</th><th>Медиана</th><th>p90</th><th>p95</th><th>макс</th><th>коридор ±</th></tr></thead>
      <tbody>${report.legs.map((l) => `<tr>
        <td>${esc(l.from)}→${esc(l.to)}</td>
        <td>${fmtDist(l.length_m)}</td>
        <td>${l.xte && l.xte.median != null ? l.xte.median + " м" : "—"}</td>
        <td>${l.xte && l.xte.p90 != null ? l.xte.p90 + " м" : "—"}</td>
        <td>${l.xte && l.xte.p95 != null ? l.xte.p95 + " м" : "—"}</td>
        <td>${l.xte && l.xte.max != null ? l.xte.max + " м" : "—"}</td>
        <td>${l.corridor_half_m} м</td></tr>`).join("")}</tbody></table>`;
  renderReportMap("rmap", report.geojson);
}

async function viewActivity(id) {
  const a = await api(`/api/activities/${id}`);
  app.innerHTML = `
    <h1>${esc(a.name)}</h1>
    <p class="subtitle">${fmtDate(a.recorded_at || a.created_at)} · источник: ${esc(a.source)}</p>
    <div class="btn-row">
      <button class="btn ${a.is_public ? "secondary" : ""}" id="share">${a.is_public ? "🔗 Ссылка скопирована" : "Поделиться"}</button>
      <button class="btn danger" id="del">Удалить</button>
    </div>
    <div id="report"></div>`;
  reportBody(a.report, app.querySelector("#report"));

  app.querySelector("#share").onclick = async () => {
    const res = await api(`/api/activities/${id}/share`, { method: "POST", json: { is_public: true } });
    const url = location.origin + "/#/share/" + res.share_token;
    try { await navigator.clipboard.writeText(url); } catch (e) {}
    toast("Публичная ссылка скопирована: " + url);
  };
  app.querySelector("#del").onclick = async () => {
    if (!confirm("Удалить тренировку?")) return;
    await api(`/api/activities/${id}`, { method: "DELETE" });
    location.hash = "#/";
  };
}

// ---------- Публичный отчёт ----------
async function viewShare(token) {
  app.innerHTML = `<div class="empty">Загрузка отчёта…</div>`;
  try {
    const d = await api(`/api/public/activities/${token}`);
    app.innerHTML = `
      <h1>${esc(d.name)}</h1>
      <p class="subtitle">${esc(d.athlete)}${d.route_name ? " · " + esc(d.route_name) : ""}
        · ${fmtDate(d.recorded_at)}</p>
      <div id="report"></div>`;
    reportBody(d.report, app.querySelector("#report"));
  } catch (e) {
    app.innerHTML = `<div class="card center-panel"><h2>Отчёт недоступен</h2>
      <p class="muted">${esc(e.message)}</p></div>`;
  }
}

// ---------- Админка ----------
function adminLoginView() {
  app.innerHTML = `
    <div class="center-panel card">
      <h1>Админ-панель</h1>
      <p class="subtitle">Вход для администратора.</p>
      <label>Логин</label><input id="u" value="admin" />
      <label>Пароль</label><input id="p" type="password" placeholder="••••••" />
      <div class="btn-row"><button class="btn" id="go">Войти</button></div>
    </div>`;
  const submit = async () => {
    const u = app.querySelector("#u").value.trim();
    const p = app.querySelector("#p").value;
    setAdmin(btoa(u + ":" + p));
    try { await adminApi("/api/admin/login"); location.hash = "#/admin"; route(); }
    catch (e) { clearAdmin(); toast("Неверный логин или пароль"); }
  };
  app.querySelector("#go").onclick = submit;
  app.querySelector("#p").onkeydown = (e) => { if (e.key === "Enter") submit(); };
}

async function viewAdmin(tab) {
  if (!getAdmin()) return adminLoginView();
  try { await adminApi("/api/admin/login"); }
  catch (e) { return adminLoginView(); }

  tab = tab || "athletes";
  const tabLink = (id, label) =>
    `<a class="btn ${tab === id ? "" : "ghost"} small" href="#/admin/${id}">${label}</a>`;
  app.innerHTML = `
    <h1>Админ-панель</h1>
    <div class="btn-row">
      ${tabLink("athletes", "Спортсмены")}
      ${tabLink("routes", "Маршруты")}
      ${tabLink("activities", "Тренировки")}
      <a class="btn ghost small" href="#" id="alogout" style="margin-left:auto">Выйти</a>
    </div>
    <div id="atab" class="empty">Загрузка…</div>`;
  app.querySelector("#alogout").onclick = (e) => { e.preventDefault(); clearAdmin(); location.hash = "#/admin"; route(); };

  if (tab === "athletes") return adminAthletes();
  if (tab === "routes") return adminRoutes();
  if (tab === "activities") return adminActivities();
}

async function adminAthletes() {
  const box = app.querySelector("#atab");
  box.className = "";
  const list = await adminApi("/api/athletes");
  box.innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <h2 style="margin-top:0">Новый спортсмен</h2>
      <div class="row" style="align-items:end">
        <div><label>Имя</label><input id="nm" placeholder="Имя спортсмена" /></div>
        <div style="flex:0 0 auto"><button class="btn" id="add">Создать токен</button></div>
      </div>
    </div>
    <table><thead><tr><th>Имя</th><th>Токен</th><th>Маршруты</th><th>Тренировки</th><th></th></tr></thead>
      <tbody>${list.map((a) => `<tr>
        <td>${esc(a.name)}</td>
        <td><code style="font-size:15px;letter-spacing:1px">${esc(a.token)}</code></td>
        <td>${a.routes}</td><td>${a.activities}</td>
        <td><button class="btn danger small" data-del="${a.id}">Удалить</button></td>
      </tr>`).join("")}</tbody></table>`;
  box.querySelector("#add").onclick = async () => {
    const nm = box.querySelector("#nm").value.trim();
    if (!nm) return toast("Введите имя");
    const a = await adminApi("/api/athletes", { method: "POST", json: { name: nm } });
    toast("Токен: " + a.token);
    adminAthletes();
  };
  box.querySelectorAll("button[data-del]").forEach((b) => {
    b.onclick = async () => {
      if (!confirm("Удалить спортсмена со всеми его маршрутами и тренировками?")) return;
      await adminApi(`/api/athletes/${b.dataset.del}`, { method: "DELETE" });
      adminAthletes();
    };
  });
}

async function adminRoutes() {
  const box = app.querySelector("#atab");
  box.className = "";
  const list = await adminApi("/api/admin/routes");
  if (!list.length) { box.innerHTML = `<div class="empty">Маршрутов нет.</div>`; return; }
  box.innerHTML = `<table><thead><tr><th>Название</th><th>Спортсмен</th><th>Буи</th><th>Публичный</th><th></th></tr></thead>
    <tbody>${list.map((r) => `<tr>
      <td>${esc(r.name)}</td><td class="muted">${esc(r.athlete || "")}</td>
      <td>${r.points_count}</td><td>${r.is_public ? "да" : "нет"}</td>
      <td><button class="btn danger small" data-del="${r.id}">Удалить</button></td>
    </tr>`).join("")}</tbody></table>`;
  box.querySelectorAll("button[data-del]").forEach((b) => {
    b.onclick = async () => {
      if (!confirm("Удалить маршрут?")) return;
      await adminApi(`/api/admin/routes/${b.dataset.del}`, { method: "DELETE" });
      adminRoutes();
    };
  });
}

async function adminActivities() {
  const box = app.querySelector("#atab");
  box.className = "";
  const list = await adminApi("/api/admin/activities");
  if (!list.length) { box.innerHTML = `<div class="empty">Тренировок нет.</div>`; return; }
  box.innerHTML = `<table><thead><tr><th>Название</th><th>Спортсмен</th><th>Дист.</th><th>Буи</th><th>Источник</th><th></th></tr></thead>
    <tbody>${list.map((a) => `<tr>
      <td>${esc(a.name)}</td><td class="muted">${esc(a.athlete || "")}</td>
      <td>${fmtDist(a.distance_m)}</td>
      <td>${a.buoys_taken ?? "—"}/${a.buoys_total ?? "—"}</td>
      <td class="muted">${esc(a.source)}</td>
      <td><button class="btn danger small" data-del="${a.id}">Удалить</button></td>
    </tr>`).join("")}</tbody></table>`;
  box.querySelectorAll("button[data-del]").forEach((b) => {
    b.onclick = async () => {
      if (!confirm("Удалить тренировку?")) return;
      await adminApi(`/api/admin/activities/${b.dataset.del}`, { method: "DELETE" });
      adminActivities();
    };
  });
}
