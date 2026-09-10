import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { optimize } from "../web/optimizer.js";
const data = JSON.parse(
  readFileSync(new URL("../web/data.json", import.meta.url)),
);
test("all original classes produce legal six-item builds at dungeon 11", () => {
  for (const hero of data.classes) {
    const r = optimize(data, { hero, dungeon: 11 });
    assert.equal(r.items.length, 6);
    assert.equal(new Set(r.items.map((i) => i.id)).size, 6);
    assert.ok(
      r.items.every((i) => i.classes.includes(hero) && i.stats.Dungeon <= 11),
    );
    assert.ok(
      r.items.filter((i) => i.stats.CC > 0 || i.stats.CX > 0).length <= 1,
    );
    assert.ok(Number.isFinite(r.score));
  }
});
test("dynamic program equals exhaustive search across every constraint combination", () => {
  for (let seed = 1; seed <= 8; seed++) {
    const items = Array.from({ length: 9 }, (_, id) => ({
      id,
      name: String(id),
      classes: ["Hero"],
      stats: {
        Dungeon: 1,
        Total_DMG_Str: ((id + 1) * seed * 7) % 23,
        Total_DMG_Agi: 9999,
        CC: id % 3 === 0 ? 1 : 0,
        CX: 0,
        MR: id % 4 === 0 ? 1 : 0,
        CDS: id % 5 === 0 ? 1 : 0,
      },
    }));
    const d = {
      items,
      classes: ["Hero"],
      primary: { Hero: "Str" },
      weights: { Hero: { Total_DMG_Str: 1, Total_DMG_Agi: 100 } },
    };
    for (const crit of [false, true])
      for (const mr of [false, true])
        for (const cdr of [false, true]) {
          let best = -Infinity;
          for (let mask = 0; mask < 512; mask++) {
            const rows = items.filter((_, i) => mask & (1 << i));
            if (
              rows.length !== 3 ||
              (crit && rows.filter((i) => i.stats.CC > 0).length > 1) ||
              (mr && !rows.some((i) => i.stats.MR > 0)) ||
              (cdr && !rows.some((i) => i.stats.CDS > 0))
            )
              continue;
            best = Math.max(
              best,
              rows.reduce((s, i) => s + i.stats.Total_DMG_Str, 0),
            );
          }
          const r = optimize(d, {
            hero: "Hero",
            dungeon: 1,
            count: 3,
            crit,
            mr,
            cdr,
          });
          assert.equal(r.score, best);
        }
  }
});
test("missing eligible items, impossible joint constraints and bad count fail", () => {
  assert.throws(
    () => optimize(data, { hero: data.classes[0], dungeon: 0 }),
    /Not enough/,
  );
  assert.throws(
    () => optimize(data, { hero: data.classes[0], dungeon: 11, count: 0 }),
    /one and six/,
  );
  const d = {
    classes: ["H"],
    primary: { H: "Str" },
    weights: { H: { MR: 1, CDS: 1 } },
    items: [
      { id: 1, classes: ["H"], stats: { Dungeon: 1, MR: 1, CDS: 0 } },
      { id: 2, classes: ["H"], stats: { Dungeon: 1, MR: 0, CDS: 1 } },
    ],
  };
  assert.throws(
    () => optimize(d, { hero: "H", dungeon: 1, count: 1, mr: true, cdr: true }),
    /No build/,
  );
  d.items[1].stats.CDS = 0;
  assert.equal(
    optimize(d, { hero: "H", dungeon: 1, count: 1, mr: true, cdr: true })
      .items[0].id,
    1,
  );
});
