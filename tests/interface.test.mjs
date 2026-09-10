import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
test("dashboard actions render builds, invalidate results and keep public automation disconnected", async () => {
  const html = readFileSync(
    new URL("../web/index.html", import.meta.url),
    "utf8",
  );
  const data = JSON.parse(
    readFileSync(new URL("../web/data.json", import.meta.url)),
  );
  const els = new Map(),
    events = new Map(),
    requests = [];
  for (const [, id] of html.matchAll(/id="([^"]+)"/g))
    els.set("#" + id, {
      value: "",
      checked: false,
      hidden: false,
      disabled: false,
      innerHTML: "",
      textContent: "",
      showModal() {
        this.open = true;
      },
    });
  els.get("#hero").value = "Dark ArchTemplar";
  els.get("#dungeon").value = "11";
  els.get("#count").value = "6";
  els.get("#crit").checked = true;
  const nav = ["items", "automation"].map((page) => ({
    dataset: { page },
    setAttribute(k, v) {
      this[k] = v;
    },
    removeAttribute(k) {
      delete this[k];
    },
  }));
  globalThis.document = {
    querySelector: (s) => els.get(s),
    querySelectorAll: () => nav,
  };
  globalThis.location = { hash: "", origin: "https://example.com" };
  globalThis.window = { addEventListener: (k, fn) => events.set(k, fn) };
  globalThis.fetch = async (url) => {
    requests.push(url);
    assert.equal(url, "./data.json");
    return { ok: true, json: async () => data };
  };
  await import("../web/app.js");
  assert.match(els.get("#result").innerHTML, /Total stats/);
  assert.equal(
    (els.get("#result").innerHTML.match(/class="item"/g) || []).length,
    6,
  );
  els.get("#hero").value = "Grand Templar";
  els.get("#hero").onchange();
  assert.match(els.get("#result").innerHTML, /Settings changed/);
  els.get("#optimize").onclick();
  assert.match(els.get("#result").innerHTML, /Total stats/);
  els.get("#search").value = "no such item";
  els.get("#search").oninput();
  assert.match(els.get("#item-body").innerHTML, /No matching/);
  location.hash = "#automation";
  events.get("hashchange")();
  assert.equal(els.get("#equipment").hidden, true);
  assert.equal(els.get("#automation").hidden, false);
  assert.equal(nav[1]["aria-current"], "page");
  assert.deepEqual(
    requests,
    ["./data.json"],
    "public page must not probe localhost",
  );
  els.get("#info").onclick();
  assert.equal(els.get("#about").open, true);
});
