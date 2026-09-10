// Exact dynamic program for the notebook's additive score and binary constraints.
export function eligible(data, hero, dungeon) {
  if (!data.classes.includes(hero) || !Number.isInteger(dungeon))
    throw Error("Choose a valid class and dungeon.");
  return data.items.filter(
    (i) => i.classes.includes(hero) && i.stats.Dungeon <= dungeon,
  );
}
export function optimize(
  data,
  { hero, dungeon, count = 6, crit = true, mr = false, cdr = false },
) {
  if (!Number.isInteger(count) || count < 1 || count > 6)
    throw Error("Choose between one and six items.");
  const items = eligible(data, hero, dungeon);
  if (items.length < count)
    throw Error("Not enough eligible items for this build.");
  const primary = "Total_DMG_" + data.primary[hero];
  const weights = Object.fromEntries(
    Object.entries(data.weights[hero]).filter(
      ([k]) => !k.startsWith("Total_DMG_") || k === primary,
    ),
  );
  const needMr = mr && items.some((i) => i.stats.MR > 0),
    needCdr = cdr && items.some((i) => i.stats.CDS > 0);
  let states = new Map([
    ["0,0,0,0", { score: 0, ids: [], count: 0, crit: 0, mr: 0, cdr: 0 }],
  ]);
  for (const item of items) {
    const value = Object.entries(weights).reduce(
      (sum, [k, w]) => sum + (item.stats[k] || 0) * w,
      0,
    );
    if (!Number.isFinite(value)) throw Error("Invalid item score.");
    const next = new Map(states);
    for (const prior of states.values()) {
      const n = prior.count + 1,
        c = prior.crit + Number(item.stats.CC > 0 || item.stats.CX > 0);
      if (n > count || (crit && c > 1)) continue;
      const m = Math.max(prior.mr, Number(item.stats.MR > 0)),
        d = Math.max(prior.cdr, Number(item.stats.CDS > 0));
      const key = [n, crit ? c : 0, m, d].join(",");
      const score = prior.score + value;
      if (!next.has(key) || score > next.get(key).score)
        next.set(key, {
          score,
          ids: [...prior.ids, item.id],
          count: n,
          crit: crit ? c : 0,
          mr: m,
          cdr: d,
        });
    }
    states = next;
  }
  const valid = [...states.values()].filter(
    (s) => s.count === count && (!needMr || s.mr) && (!needCdr || s.cdr),
  );
  valid.sort((a, b) => b.score - a.score);
  if (!valid.length) throw Error("No build satisfies these constraints.");
  const best = valid[0],
    selected = best.ids.map((id) => items.find((i) => i.id === id));
  const totals = {};
  for (const item of selected)
    for (const [key, value] of Object.entries(item.stats))
      if (key !== "Dungeon") totals[key] = (totals[key] || 0) + value;
  return { items: selected, totals, weights, score: best.score };
}
