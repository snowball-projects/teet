import { eligible, optimize } from "./optimizer.js";
const $ = (s) => document.querySelector(s),
  esc = (s) =>
    String(s).replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
const fmt = (n) =>
  Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 });
let data,
  result = null,
  local = false;
const rawStats = [
  "Str",
  "Agi",
  "Int",
  "HP",
  "HPR",
  "MP",
  "MPR",
  "DMG",
  "CC",
  "CX",
  "Splash",
  "AS",
  "Armor",
  "CDS",
  "MR",
  "MS",
];
function params() {
  return {
    hero: $("#hero").value,
    dungeon: Number($("#dungeon").value),
    count: Number($("#count").value),
    crit: $("#crit").checked,
    mr: $("#mr").checked,
    cdr: $("#cdr").checked,
  };
}
function catalog() {
  const p = params(),
    query = $("#search").value.toLowerCase(),
    items = eligible(data, p.hero, p.dungeon).filter((i) =>
      i.name.toLowerCase().includes(query),
    );
  const ids = new Set(result?.items.map((i) => i.id) || []);
  $("#match-count").textContent = items.length;
  $("#item-body").innerHTML =
    items
      .map(
        (i) =>
          `<tr class="${ids.has(i.id) ? "selected" : ""}"><td>${esc(i.name)}</td><td>${i.stats.Dungeon}</td>${rawStats.map((k) => `<td>${i.stats[k] ? fmt(i.stats[k]) : "·"}</td>`).join("")}</tr>`,
      )
      .join("") ||
    `<tr><td colspan="${rawStats.length + 2}">No matching items.</td></tr>`;
  const primary = "Total_DMG_" + data.primary[p.hero];
  $("#weights").innerHTML = Object.entries(data.weights[p.hero])
    .filter(([k]) => !k.startsWith("Total_DMG_") || k === primary)
    .map(
      ([k, v]) =>
        `<div class="stat"><span>${esc(k.replaceAll("_", " "))}</span><span>${fmt(v)}</span></div>`,
    )
    .join("");
}
function solve() {
  try {
    result = optimize(data, params());
    $("#notice").textContent = "";
    $("#score").textContent = fmt(result.score) + " weighted";
    $("#result").innerHTML =
      result.items
        .map(
          (i) =>
            `<div class="item"><strong>${esc(i.name)}</strong><p>Dungeon ${i.stats.Dungeon} · ${esc(i.class_group)}</p></div>`,
        )
        .join("") +
      `<div class="totals"><h3>Total stats</h3>${Object.entries(result.totals)
        .filter(
          ([k, v]) =>
            v &&
            (!k.startsWith("Total_DMG_") ||
              k === "Total_DMG_" + data.primary[params().hero]),
        )
        .map(
          ([k, v]) =>
            `<div class="stat"><span>${esc(k.replaceAll("_", " "))}</span><span>${fmt(v)}</span></div>`,
        )
        .join("")}</div>`;
  } catch (e) {
    result = null;
    $("#score").textContent = "";
    $("#result").innerHTML = '<p class="muted">No feasible build.</p>';
    $("#notice").textContent = e.message;
  }
  catalog();
}
function change() {
  result = null;
  $("#score").textContent = "";
  $("#notice").textContent = "";
  $("#result").innerHTML =
    '<p class="muted">Settings changed. Optimize to update the build.</p>';
  catalog();
}
function route() {
  const auto = location.hash === "#automation";
  $("#equipment").hidden = auto;
  $("#automation").hidden = !auto;
  document.querySelectorAll("[data-page]").forEach((a) => {
    if (a.dataset.page === (auto ? "automation" : "items"))
      a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  document.title = (auto ? "Automation" : "Equipment") + " · teet";
}
async function api(path, body) {
  const r = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const d = await r.json();
  if (!r.ok) throw Error(d.error || "Local helper unavailable.");
  return d;
}
async function status() {
  if (!local) return;
  try {
    const s = await api("/api/status");
    $("#automation-status").textContent = s.message;
    $("#start").disabled = s.running;
    $("#stop").disabled = !s.running;
  } catch {
    local = false;
    $("#local-controls").disabled = true;
    $("#automation-status").textContent =
      "Companion disconnected. Reopen local controls.";
  }
}
$("#info").onclick = () => $("#about").showModal();
window.addEventListener("hashchange", route);
route();
$("#mode").onchange = () => {
  $("#repeat-options").hidden = $("#mode").value === "fishing";
};
$("#start").onclick = async () => {
  try {
    await api("/api/start", {
      mode: $("#mode").value,
      key: $("#key").value,
      interval: Number($("#interval").value),
    });
    await status();
  } catch (e) {
    $("#automation-status").textContent = e.message;
  }
};
$("#stop").onclick = async () => {
  try {
    await api("/api/stop", {});
    await status();
  } catch (e) {
    $("#automation-status").textContent = e.message;
  }
};
try {
  const r = await fetch("./data.json");
  if (!r.ok) throw Error("Item data could not be loaded.");
  data = await r.json();
  $("#hero").innerHTML = data.classes
    .map(
      (c) =>
        `<option ${c === "Dark ArchTemplar" ? "selected" : ""}>${esc(c)}</option>`,
    )
    .join("");
  $("#dungeon").innerHTML = [...new Set(data.items.map((i) => i.stats.Dungeon))]
    .sort((a, b) => a - b)
    .map((n) => `<option ${n === 11 ? "selected" : ""}>${n}</option>`)
    .join("");
  $("#catalog-count").textContent = data.items.length;
  $("#item-head").innerHTML =
    "<tr><th>Item</th><th>Dungeon</th>" +
    rawStats.map((k) => `<th>${k}</th>`).join("") +
    "</tr>";
  for (const id of ["hero", "dungeon", "count", "crit", "mr", "cdr"])
    $("#" + id).onchange = change;
  $("#search").oninput = catalog;
  $("#optimize").onclick = solve;
  solve();
} catch (e) {
  $("#notice").textContent = e.message;
  $("#optimize").disabled = true;
}
if (location.origin === "http://127.0.0.1:8784") {
  try {
    await api("/api/status");
    local = true;
    $("#local-controls").disabled = false;
    $("#download").hidden = true;
    $("#local-message").textContent =
      "Local controls. Switch to Warcraft after starting; input pauses while another window is active.";
    await status();
    setInterval(status, 1000);
  } catch {}
}
