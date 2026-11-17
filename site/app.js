import { decryptBlob } from "./crypto.js";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const el = (tag, cls, html) => { const n = document.createElement(tag); if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; };
const esc = (s) => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = (v) => v == null ? "?" : (Math.abs(v) >= 100 ? Math.round(v) : +(+v).toFixed(2)).toString();
const store = { get(k){ try { return localStorage.getItem(k); } catch { return null; } },
                set(k,v){ try { localStorage.setItem(k,v); } catch {} } };

let MANIFEST = null, SELECTED = null, DATA = null, ACTIVE_PANEL = "summary";
let SUM_FILTER = "concern";   // default Summary view: markers out of range
let SUM_SORT_SEV = false;     // "sort by severity" is opt-in, not the default

/* ---------------- theme ---------------- */
function applyTheme(t){ if (t) document.documentElement.dataset.theme = t; }
applyTheme(store.get("hh-theme"));
$("#theme-toggle")?.addEventListener("click", () => {
  const cur = document.documentElement.dataset.theme
    || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const next = cur === "dark" ? "light" : "dark";
  applyTheme(next); store.set("hh-theme", next);
});

/* ---------------- login ---------------- */
async function initLogin(){
  try {
    MANIFEST = await (await fetch("data/manifest.json", { cache: "no-store" })).json();
  } catch { $("#login-error").textContent = "Could not load the profile list."; $("#login-error").hidden = false; return; }
  const box = $("#people");
  const last = store.get("hh-last");
  MANIFEST.people.forEach(p => {
    const b = el("button", "person-chip");
    b.type = "button"; b.setAttribute("aria-pressed", "false");
    b.innerHTML = `<span class="ava">${esc(p.initials)}</span><span>${esc(p.name)}</span>`;
    b.addEventListener("click", () => selectPerson(p, b));
    box.appendChild(b);
    if (p.id === last) selectPerson(p, b);
  });
}
function selectPerson(p, btn){
  SELECTED = p;
  $$(".person-chip").forEach(c => c.setAttribute("aria-pressed", "false"));
  btn.setAttribute("aria-pressed", "true");
  $("#unlock").disabled = false;
  $("#pass").focus();
}
$("#unlock-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!SELECTED) return;
  const pass = $("#pass").value.trim();
  const err = $("#login-error"); err.hidden = true;
  const btn = $("#unlock"); btn.disabled = true; btn.textContent = "Unlocking…";
  try {
    const blob = await (await fetch(`data/${SELECTED.id}.enc`, { cache: "no-store" })).json();
    DATA = await decryptBlob(blob, pass);
    store.set("hh-last", SELECTED.id);
    $("#pass").value = "";
    renderApp();
  } catch {
    err.textContent = "That passphrase didn’t work for this profile. Please check and try again.";
    err.hidden = false;
  } finally { btn.disabled = false; btn.textContent = "Unlock my timeline"; }
});

/* ---------------- status helpers ---------------- */
function chipInfo(b){
  const st = b.latest.status;
  if (st === "normal") return { cls: "normal", label: "In range" };
  if (st === "nolimit" || st === "unknown") return { cls: "nolimit", label: "—" };
  if (b.concern) return { cls: st + " concern", label: st === "high" ? "High" : "Low" };
  return { cls: st + (st === "high" ? " ok" : ""), label: st === "high" ? "High" : "Low" };
}
function movedInfo(b){
  const m = b.moved;
  if (m === "improved") return { cls: "up", label: "↗ improved" };
  if (m === "improving") return { cls: "up", label: "↗ improving" };
  if (m === "worsened") return { cls: "down", label: "↘ worsened" };
  if (m === "worsening") return { cls: "down", label: "↘ worsening" };
  if (b.n > 1) return { cls: "flat", label: `${b.n} tests` };
  return { cls: "flat", label: "1 test" };
}
/* Reference range as a short string, e.g. "12–20 mg/dL", "< 100 mg/dL", or null. */
function refRange(L, unit){
  const u = unit ? " " + unit : "";
  if (L.ref_low != null && L.ref_high != null) return `${fmt(L.ref_low)}–${fmt(L.ref_high)}${u}`;
  if (L.ref_high != null) return `&lt; ${fmt(L.ref_high)}${u}`;
  if (L.ref_low != null) return `&gt; ${fmt(L.ref_low)}${u}`;
  return null;
}
/* Direction class (good/bad/neutral) for a marker's trend. */
function movedCls(b){
  if (b.moved === "improved" || b.moved === "improving") return "up";
  if (b.moved === "worsened" || b.moved === "worsening") return "down";
  return "flat";
}
/* Compact "was → now" cell for the summary tables. */
function trendCellHTML(b){
  if (!b.trend) return `<span class="chg flat">${b.n > 1 ? b.n + " tests" : "1 test"}</span>`;
  const t = b.trend;
  const y0 = t.from_date.slice(2, 4), y1 = t.to_date.slice(2, 4);
  return `<span class="chg ${movedCls(b)}" title="${esc(t.from_date)} → ${esc(t.to_date)}">`
    + `${fmt(t.from_value)}<span class="chg-y">’${y0}</span> → ${fmt(t.to_value)}<span class="chg-y">’${y1}</span></span>`;
}
/* Table of markers, one row each, built from narrative items (which carry a biomarker id). */
function summaryTable(items){
  const wrap = el("div", "sum-table-wrap");
  const tbl = el("table", "sum-table");
  tbl.innerHTML = `<thead><tr><th>Marker</th><th>Latest</th><th>Reference</th><th>Status</th><th>Trend</th></tr></thead>`;
  const tb = el("tbody");
  items.forEach(it => {
    const b = DATA.biomarkers.find(x => x.biomarker === it.biomarker);
    const tr = el("tr");
    if (!b){ tr.innerHTML = `<td colspan="5">${esc(it.text)}</td>`; tb.appendChild(tr); return; }
    const ch = chipInfo(b), rng = refRange(b.latest, b.unit);
    tr.className = "clickable";
    tr.innerHTML =
      `<td class="m">${esc(b.display)}</td>`
      + `<td class="num"><b>${fmt(b.latest.value)}</b> <span class="u">${esc(b.unit||"")}</span></td>`
      + `<td class="num ref">${rng || "—"}</td>`
      + `<td><span class="chip ${ch.cls}">${ch.label}</span></td>`
      + `<td class="num">${trendCellHTML(b)}</td>`;
    tr.addEventListener("click", () => openDetail(b));
    tb.appendChild(tr);
  });
  tbl.appendChild(tb); wrap.appendChild(tbl); return wrap;
}

/* ---------------- sparkline ----------------
   One dot per report. The x-axis is the person's WHOLE date range (shared by every
   card), so a given date sits at the same horizontal spot in all cards and a marker
   measured only in, say, '23 lands where '23 is everywhere. Each point is labelled
   with its value; the axis is labelled month-year. Uniform scaling keeps text crisp. */
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function monYr(iso){ const m = +iso.slice(5, 7) || 1; return `${MON[m-1]}-${iso.slice(0, 4)}`; }   // 2025-06-15 -> Jun-2025
function dotCol(s){
  return s === "normal" ? "var(--ok)" : (s === "nolimit" || s === "unknown" ? "var(--ink-3)" : "var(--bad)");
}
/* Shared time domain for all card sparklines: the person's full report span. */
function sparkDomain(ts){
  const dr = (typeof DATA !== "undefined" && DATA) ? DATA.date_range : null;
  let gmin = dr ? Date.parse(dr[0]) : NaN, gmax = dr ? Date.parse(dr[1]) : NaN;
  if (isNaN(gmin) || isNaN(gmax)) { gmin = Math.min(...ts); gmax = Math.max(...ts); }
  return [gmin, gmax, (gmax - gmin) || 1];
}
function sparkline(pts){
  const P = pts.filter(p => p.value != null);
  if (!P.length) return `<svg class="spark" viewBox="0 0 240 82"></svg>`;
  const vals = P.map(p => p.value);
  const vmin = Math.min(...vals), vmax = Math.max(...vals), vspan = (vmax - vmin) || 1;
  const ts = P.map(p => Date.parse(p.date));
  const [gmin, , tspan] = sparkDomain(ts);
  const W = 240, H = 82, padX = 16, padT = 16, axisH = 16;   // bottom strip holds a single row of date labels
  const plotBot = H - axisH, plotH = plotBot - padT;
  const X = t => padX + ((t - gmin) / tspan) * (W - padX * 2);   // position by true date on the shared axis
  const Y = v => padT + (1 - (v - vmin) / vspan) * plotH;
  const line = P.length > 1
    ? `<path d="${P.map((p, i) => `${i ? "L" : "M"}${X(ts[i]).toFixed(1)} ${Y(p.value).toFixed(1)}`).join(" ")}"
        fill="none" stroke="var(--ink-3)" stroke-width="1.4" opacity=".55"/>`
    : "";
  const lblY = H - 4;                   // all date labels share one baseline (a proper time axis)
  const xs = P.map((p, i) => X(ts[i]));
  // dedupe identical month-year labels (same-month repeat tests), then size the whole row's
  // font so the closest adjacent pair still fits on one line — shrink to fit, never stagger.
  const labelByIdx = {}, seenLbl = new Set();
  P.forEach((p, i) => { const l = monYr(p.date); if (!seenLbl.has(l)) { seenLbl.add(l); labelByIdx[i] = l; } });
  const keptX = Object.keys(labelByIdx).map(k => xs[k]).sort((a, b) => a - b);
  let minGap = Infinity;
  for (let i = 1; i < keptX.length; i++) minGap = Math.min(minGap, keptX[i] - keptX[i - 1]);
  // label width ≈ 4.3·fontSize viewBox units (8-char "Mon-YYYY"); solve for the fit, clamp to [5, 8]
  const fs = (keptX.length > 1 && isFinite(minGap))
    ? Math.max(5, Math.min(8, +(((minGap - 3) / 4.3)).toFixed(2)))
    : 8;
  // last resort: if two dates are so close they still overlap at the smallest font, drop one
  // (scanning right-to-left so the most recent date always keeps its label).
  const half = 2.15 * fs, render = new Set();
  const keptIdx = Object.keys(labelByIdx).map(Number).sort((a, b) => xs[a] - xs[b]);
  let lastLeft = Infinity;
  for (let k = keptIdx.length - 1; k >= 0; k--) {
    const idx = keptIdx[k];
    if (xs[idx] + half <= lastLeft - 1.5) { render.add(idx); lastLeft = xs[idx] - half; }
  }
  const marks = P.map((p, i) => {
    const x = xs[i], y = Y(p.value);
    let above = i % 2 === 0;                            // alternate so neighbouring value labels don't collide
    if (above && y < padT + 9) above = false;           // keep top label from clipping
    if (!above && y > plotBot - 10) above = true;        // keep bottom value label out of the axis strip
    const ly = above ? y - 6 : y + 9;
    const axisLbl = render.has(i)
      ? `<text class="spark-yr" x="${x.toFixed(1)}" y="${lblY}" text-anchor="middle" style="font-size:${fs}px">${esc(labelByIdx[i])}</text>`
      : "";
    return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.6" fill="${dotCol(p.status)}"/>
      <text class="spark-lbl" x="${x.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="middle">${esc(fmt(p.value))}</text>
      ${axisLbl}`;
  }).join("");
  return `<svg class="spark" viewBox="0 0 ${W} ${H}">${line}${marks}</svg>`;
}

/* ---------------- render dashboard ---------------- */
function renderApp(){
  $("#login").hidden = true; $("#app").hidden = false;
  $("#avatar").textContent = SELECTED.initials;
  $("#person-name").textContent = DATA.name;
  const dr = DATA.date_range;
  $("#person-sub").textContent = `${DATA.n_biomarkers} markers · ${DATA.n_reports} reports · ${dr[0]} → ${dr[1]}`;
  $("#disclaimer").innerHTML = `<b>Note.</b> ${esc(DATA.disclaimer)}`;
  renderGlance(); renderTabs(); renderPanels();
  $("#app-footer").innerHTML =
    `Generated ${esc(DATA.generated)} from ${DATA.n_reports} report dates across ${DATA.labs.length} labs. `
    + `Every value links to its source report. &nbsp;·&nbsp; Your data stayed encrypted on the server and was unlocked only in this browser.`;
  window.scrollTo(0, 0);
}

function glanceList(items, kind){
  const ul = el("ul", "g-rows");
  items.forEach(it => {
    const b = DATA.biomarkers.find(x => x.biomarker === it.biomarker);
    const li = el("li", "g-row");
    if (!b){ li.innerHTML = `<span>${esc(it.text)}</span>`; ul.appendChild(li); return; }
    const ch = chipInfo(b);
    const right = (kind === "change" && b.trend)
      ? `<span class="chg ${movedCls(b)}">${fmt(b.trend.from_value)} → ${fmt(b.trend.to_value)}</span>`
      : `<span class="chip ${ch.cls}">${ch.label}</span>`;
    li.classList.add("clickable");
    li.innerHTML = `<span class="g-name">${esc(b.display)}</span>`
      + `<span class="g-val"><span class="g-num">${fmt(b.latest.value)}</span> ${right}</span>`;
    li.addEventListener("click", () => openById(b.biomarker));
    ul.appendChild(li);
  });
  if (!items.length) ul.appendChild(el("li", "more", "Nothing flagged — nice."));
  return ul;
}
function renderGlance(){
  const g = $("#glance"); g.innerHTML = "";
  const N = DATA.narrative;
  const c1 = el("div", "gcard focus"); c1.innerHTML = `<h3>Focus areas</h3><div class="big">${N.focus_areas.length}</div>`;
  c1.appendChild(glanceList(N.focus_areas, "status")); g.appendChild(c1);
  const c2 = el("div", "gcard improve"); c2.innerHTML = `<h3>Improvements</h3><div class="big">${N.improvements.length}</div>`;
  c2.appendChild(glanceList(N.improvements, "change")); g.appendChild(c2);
  const c3 = el("div", "gcard"); c3.innerHTML = `<h3>Worth discussing with a doctor</h3>`;
  c3.appendChild(glanceList(N.discuss, "status")); g.appendChild(c3);
  const c4 = el("div", "gcard"); c4.innerHTML =
    `<h3>Timeline</h3><div class="big">${DATA.n_reports}</div>
     <ul><li class="more">report dates · ${DATA.n_biomarkers} markers tracked</li>
     <li class="more">${esc(DATA.date_range[0])} → ${esc(DATA.date_range[1])}</li>
     <li class="more">${DATA.labs.length} laboratories</li></ul>`;
  g.appendChild(c4);
}
function renderTabs(){
  const t = $("#panel-tabs"); t.innerHTML = "";
  const mk = (id, label) => { const b = el("button", "tab", esc(label)); b.type = "button";
    b.setAttribute("aria-pressed", String(ACTIVE_PANEL === id));
    b.addEventListener("click", () => { ACTIVE_PANEL = id; renderTabs(); renderPanels(); }); return b; };
  t.appendChild(mk("summary", "Summary"));
  t.appendChild(mk("all", "All markers"));
  DATA.panels.forEach(p => t.appendChild(mk(p.id, p.label)));
}
function openById(id){ const b = DATA.biomarkers.find(x => x.biomarker === id); if (b) openDetail(b); }

/* The four old sections collapse into one table filtered by these views, over
   the single per-marker dataset (each marker appears once). */
const SUM_FILTERS = [
  { id: "concern",   label: "Out of range", icon: "⚠", test: b => b.concern },
  { id: "worsening", label: "Worsening",    icon: "↘", test: b => b.moved === "worsened"  || b.moved === "worsening" },
  { id: "improving", label: "Improving",    icon: "↗", test: b => b.moved === "improved"  || b.moved === "improving" },
  { id: "priority",  label: "Worth raising with a doctor", icon: "★", test: b => b.priority },
  { id: "all",       label: "All markers",  icon: "",  test: () => true },
];
const FILTER_EMPTY = {
  concern:   "No markers are outside their reference range on the latest test.",
  worsening: "Nothing is trending the wrong way.",
  improving: "No clear improvements yet (most markers need more than one test).",
  priority:  "Nothing flagged to raise with a doctor from these numbers alone.",
  all:       "No markers tracked yet.",
};

/* One marker row, built directly from a biomarker summary object. */
function markerRow(b){
  const ch = chipInfo(b), rng = refRange(b.latest, b.unit);
  const tr = el("tr", "clickable");
  tr.innerHTML =
      `<td class="m">${esc(b.display)}</td>`
    + `<td class="num"><b>${fmt(b.latest.value)}</b> <span class="u">${esc(b.unit||"")}</span></td>`
    + `<td class="num ref">${rng || "—"}</td>`
    + `<td><span class="chip ${ch.cls}">${ch.label}</span></td>`
    + `<td class="num">${trendCellHTML(b)}</td>`;
  tr.addEventListener("click", () => openDetail(b));
  return tr;
}
function markerTable(list){
  const wrap = el("div", "sum-table-wrap");
  const tbl = el("table", "sum-table");
  tbl.innerHTML = `<thead><tr><th>Marker</th><th>Latest</th><th>Reference</th><th>Status</th><th>Trend</th></tr></thead>`;
  const tb = el("tbody");
  list.forEach(b => tb.appendChild(markerRow(b)));
  tbl.appendChild(tb); wrap.appendChild(tbl); return wrap;
}
function filteredMarkers(){
  const f = SUM_FILTERS.find(x => x.id === SUM_FILTER) || SUM_FILTERS[0];
  let list = DATA.biomarkers.filter(f.test);
  if (SUM_SORT_SEV){
    list = list.slice().sort((a, b) =>
      (b.severity||0) - (a.severity||0)
      || (b.concern?1:0) - (a.concern?1:0)
      || a.display.localeCompare(b.display));
  }
  return list;   // default order = DATA.biomarkers (panel, then name)
}
function renderSummary(wrap){
  const art = el("article", "summary-view");

  // 1+2. headline paragraph and "what can help" sit side by side (see .sum-top)
  const top = el("div", "sum-top");
  if (DATA.headline) top.appendChild(el("p", "sum-headline", esc(DATA.headline)));

  const acts = DATA.actions || [], actx = DATA.action_context || [];
  if (acts.length || actx.length){
    const lv = el("section", "sum-levers");
    lv.appendChild(el("h3", "lv-head",
      `What can help <span class="lv-note">general information, not medical advice</span>`));
    const ul = el("ul", "act-list");
    acts.forEach(a => {
      const li = el("li", "act-row");
      const pills = a.markers.map(m =>
        `<button type="button" class="metric-pill" data-bm="${esc(m.biomarker)}">${esc(m.display)}</button>`).join("");
      li.innerHTML =
        `<div class="act-label">${esc(a.label)}${a.detail ? `<span class="act-detail">${esc(a.detail)}</span>` : ""}</div>`
        + `<div class="act-metrics">${pills}</div>`;
      li.querySelectorAll(".metric-pill").forEach(btn => btn.addEventListener("click", () => openById(btn.dataset.bm)));
      ul.appendChild(li);
    });
    lv.appendChild(ul);
    if (actx.length){
      const names = actx.map(c => `<button type="button" class="lv-name" data-bm="${esc(c.biomarker)}">${esc(c.display)}</button>`).join(", ");
      const note = el("p", "act-context", `Some flagged markers are non-specific and need clinical context: ${names}.`);
      note.querySelectorAll(".lv-name").forEach(btn => btn.addEventListener("click", () => openById(btn.dataset.bm)));
      lv.appendChild(note);
    }
    lv.appendChild(el("p", "lv-foot",
      "Educational only — what’s right for you is a conversation for your doctor."));
    top.appendChild(lv);
  }
  if (top.children.length === 1) top.classList.add("solo");
  if (top.children.length) art.appendChild(top);

  // 3. filter chips + severity-sort toggle, over one marker table
  const bar = el("div", "sum-bar");
  const chips = el("div", "sum-chips");
  const tableHost = el("div", "sum-tablehost");

  function paintChips(){
    chips.innerHTML = "";
    SUM_FILTERS.forEach(f => {
      const count = DATA.biomarkers.filter(f.test).length;
      const b = el("button", "sum-chip" + (SUM_FILTER === f.id ? " on" : ""));
      b.type = "button";
      b.setAttribute("aria-pressed", String(SUM_FILTER === f.id));
      b.innerHTML = `${f.icon ? `<span class="ci">${f.icon}</span> ` : ""}${esc(f.label)} <span class="cc">${count}</span>`;
      b.addEventListener("click", () => { SUM_FILTER = f.id; paintChips(); paintTable(); });
      chips.appendChild(b);
    });
  }
  function paintTable(){
    tableHost.innerHTML = "";
    const list = filteredMarkers();
    if (!list.length){ tableHost.appendChild(el("p", "sum-empty", esc(FILTER_EMPTY[SUM_FILTER] || "Nothing here."))); return; }
    tableHost.appendChild(markerTable(list));
  }

  const sort = el("label", "sum-sort");
  sort.innerHTML = `<input type="checkbox" id="sum-sort-sev"> <span>Sort by severity</span>`;
  sort.querySelector("input").checked = SUM_SORT_SEV;
  sort.querySelector("input").addEventListener("change", e => { SUM_SORT_SEV = e.target.checked; paintTable(); });

  bar.appendChild(chips); bar.appendChild(sort);
  art.appendChild(bar);
  art.appendChild(tableHost);
  paintChips(); paintTable();

  art.appendChild(el("p", "sum-foot",
    "One row per marker; tap any row to see its full timeline and source reports. "
    + "This describes what the numbers show — it is not a diagnosis."));
  wrap.appendChild(art);
}

function renderPanels(){
  const wrap = $("#panels"); wrap.innerHTML = "";
  $("#only-flagged").closest(".flagged-toggle").style.visibility = ACTIVE_PANEL === "summary" ? "hidden" : "visible";
  if (ACTIVE_PANEL === "summary"){ renderSummary(wrap); return; }
  const onlyFlagged = $("#only-flagged").checked;
  const panels = ACTIVE_PANEL === "all" ? DATA.panels : DATA.panels.filter(p => p.id === ACTIVE_PANEL);
  panels.forEach(panel => {
    let items = DATA.biomarkers.filter(b => b.panel === panel.id);
    if (onlyFlagged) items = items.filter(b => b.concern);
    if (!items.length) return;
    const sec = el("section", "panel");
    sec.appendChild(el("div", "panel-head",
      `<h2>${esc(panel.label)}</h2><span class="count">${items.length} marker${items.length>1?"s":""}</span>`));
    const grid = el("div", "grid");
    items.forEach(b => grid.appendChild(tile(b)));
    sec.appendChild(grid); wrap.appendChild(sec);
  });
  if (!wrap.children.length) wrap.appendChild(el("p", "footer-note", "No markers match this filter."));
}
function tile(b){
  const ch = chipInfo(b), mv = movedInfo(b);
  const t = el("button", "tile" + (b.concern ? " flagged" : ""));
  t.type = "button";
  const rng = refRange(b.latest, b.unit);
  t.innerHTML =
    `<div class="tile-top"><span class="tile-name">${esc(b.display)}</span>
       <span class="tile-tags"><span class="chip ${ch.cls}">${ch.label}</span>${
         mv.cls !== "flat" ? `<span class="trend ${mv.cls}">${mv.label}</span>` : ""}</span></div>
     <div class="tile-val"><span class="v">${fmt(b.latest.value)}</span><span class="u">${esc(b.unit||"")}</span></div>
     <div class="tile-ref">${rng ? `<span class="rl">Ref</span> ${rng}` : `<span class="rl">No reference range</span>`}</div>
     ${sparkline(b.points)}`;
  t.addEventListener("click", () => openDetail(b));
  return t;
}

/* ---------------- detail modal + timeline ---------------- */
function timelineChart(b){
  const W = 680, H = 230, padL = 48, padR = 16, padT = 16, padB = 34;
  const pts = b.points.filter(p => p.value != null);
  const vals = pts.map(p => p.value);
  const refs = pts.flatMap(p => [p.ref_low, p.ref_high]).filter(v => v != null);
  let lo = Math.min(...vals, ...refs), hi = Math.max(...vals, ...refs);
  const pad = (hi - lo) * 0.15 || Math.abs(hi) * 0.15 || 1; lo -= pad; hi += pad;
  const n = pts.length;
  const ts = pts.map(p => Date.parse(p.date));
  const tmin = Math.min(...ts), tmax = Math.max(...ts), tspan = (tmax - tmin) || 1;
  const X = i => padL + (n === 1 ? (W - padL - padR) / 2 : ((ts[i] - tmin) / tspan) * (W - padL - padR));
  const Y = v => padT + (1 - (v - lo) / ((hi - lo) || 1)) * (H - padT - padB);
  const L = b.latest;
  let band = "";
  if (L.ref_low != null || L.ref_high != null){
    const yTop = Y(L.ref_high != null ? L.ref_high : hi);
    const yBot = Y(L.ref_low != null ? L.ref_low : lo);
    band = `<rect x="${padL}" y="${yTop}" width="${W-padL-padR}" height="${Math.max(0,yBot-yTop)}"
      fill="var(--ok)" opacity=".10"/>
      ${L.ref_high!=null?`<line x1="${padL}" x2="${W-padR}" y1="${yTop}" y2="${yTop}" stroke="var(--ok)" stroke-dasharray="4 4" opacity=".5"/>`:""}
      ${L.ref_low!=null?`<line x1="${padL}" x2="${W-padR}" y1="${yBot}" y2="${yBot}" stroke="var(--ok)" stroke-dasharray="4 4" opacity=".5"/>`:""}`;
  }
  const yticks = [lo, (lo+hi)/2, hi].map(v =>
    `<text x="${padL-8}" y="${Y(v)+3.5}" text-anchor="end" font-size="10" fill="var(--ink-3)">${fmt(v)}</text>
     <line x1="${padL}" x2="${W-padR}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--border)" opacity=".6"/>`).join("");
  const line = n > 1 ? `<path d="${pts.map((p,i)=>`${i?"L":"M"}${X(i).toFixed(1)} ${Y(p.value).toFixed(1)}`).join(" ")}"
      fill="none" stroke="var(--accent)" stroke-width="2"/>` : "";
  const dots = pts.map((p,i) => {
    const col = p.status === "normal" ? "var(--ok)" : (p.status==="nolimit"||p.status==="unknown" ? "var(--ink-3)" : "var(--bad)");
    return `<circle cx="${X(i).toFixed(1)}" cy="${Y(p.value).toFixed(1)}" r="4.5" fill="${col}" stroke="var(--surface)" stroke-width="1.5">
      <title>${esc(p.date)}: ${fmt(p.value)} ${esc(p.unit||"")} — ${esc(p.lab)}</title></circle>
      <text x="${X(i).toFixed(1)}" y="${H-padB+16}" text-anchor="middle" font-size="9.5" fill="var(--ink-3)">${esc(monYr(p.date))}</text>`;
  }).join("");
  return `<svg class="chart" viewBox="0 0 ${W} ${H}">${yticks}${band}${line}${dots}</svg>`;
}
function openDetail(b){
  const body = $("#modal-body");
  const L = b.latest;
  const refStr = refRange(L, b.unit) || "—";
  const ch = chipInfo(b);
  const rows = [...b.points].reverse().map(p => {
    const rs = (p.ref_low != null || p.ref_high != null)
      ? (p.ref_low != null && p.ref_high != null ? `${fmt(p.ref_low)}–${fmt(p.ref_high)}`
         : p.ref_high != null ? `< ${fmt(p.ref_high)}` : `> ${fmt(p.ref_low)}`) : "—";
    const sc = p.status === "normal" ? "normal" : (p.status==="nolimit"?"nolimit":p.status);
    return `<tr><td>${esc(p.date)}</td><td><b>${fmt(p.value)}</b> ${esc(p.unit||"")}</td>
      <td><span class="chip ${sc}">${p.status==="normal"?"In range":p.status==="nolimit"?"—":p.status}</span></td>
      <td>${rs}${p.ref_source==="general-hint"?" <span class='src'>(general)</span>":""}</td>
      <td>${esc(p.lab)}</td><td class="src">${esc(p.source_file.split(/[\\/]/).pop())} · p${p.source_page}</td></tr>`;
  }).join("");
  body.innerHTML =
    `<div class="detail-head"><div><h2>${esc(b.display)}</h2>
       <div class="detail-sub">${esc((DATA.panels.find(p=>p.id===b.panel)||{}).label||"")} · latest ${fmt(L.value)} ${esc(b.unit||"")} · reference ${refStr} · ${b.n} test${b.n>1?"s":""}</div></div>
       <span class="chip ${ch.cls}">${ch.label}</span></div>
     ${!b.comparable ? `<div class="note-warn">⚠ These results were reported in different units (${esc(b.units.join(", "))}). They are shown together but may not be directly comparable — treat the trend with caution.</div>` : ""}
     <div class="chart-wrap">${timelineChart(b)}</div>
     <table class="obs"><thead><tr><th>Date</th><th>Value</th><th>Status</th><th>Reference</th><th>Lab</th><th>Source report</th></tr></thead>
     <tbody>${rows}</tbody></table>
     <p class="privacy-note">Reference ranges marked “general” are standard adult hints used only when a report didn’t state its own range. Shaded band on the chart uses the most recent reference range.</p>`;
  $("#modal").hidden = false;
}
$$("[data-close]").forEach(x => x.addEventListener("click", () => $("#modal").hidden = true));
document.addEventListener("keydown", e => { if (e.key === "Escape") $("#modal").hidden = true; });
$("#only-flagged").addEventListener("change", renderPanels);
$("#lock").addEventListener("click", () => { DATA = null; location.reload(); });

initLogin();
