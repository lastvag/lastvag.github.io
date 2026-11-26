/* Lastväg – vikt och bärighetsklass
   Gränsvärden enligt trafikförordningen (1998:1276) 4 kap. 12 § och bilaga 1–4,
   så som de återges i Transportstyrelsens "Lasta lagligt" (2026).
   Appen är ett stöd – föraren ansvarar alltid för att ekipaget är lagligt lastat. */
const Vikt = (() => {
  'use strict';
  const r2 = (x) => Math.round(x * 100) / 100;

  // Bruttoviktstabeller: [övre gräns för axelavstånd (m, "till under"), max bruttovikt (ton)]
  const BK1 = [[1.0, 11.5], [1.3, 16], [1.8, 18], [2.0, 20], [2.6, 21], [4.4, 24], [4.7, 25], [5.2, 26], [5.4, 27], [5.6, 28],
    [5.8, 29], [6.0, 30], [6.2, 31], [8.25, 32], [8.5, 33], [8.75, 34], [9.0, 35], [9.25, 36], [9.5, 37], [9.75, 38], [10.0, 39],
    [10.25, 40], [10.5, 41], [10.75, 42], [11.0, 43], [11.25, 44], [11.5, 45], [11.75, 46], [12.0, 47], [12.5, 48], [13.0, 49],
    [13.5, 50], [14.0, 51], [14.5, 52], [15.0, 53], [15.5, 54], [16.0, 55], [16.5, 56], [17.0, 57], [17.5, 58], [18.0, 59],
    [18.5, 60], [19.0, 61], [19.6, 62], [20.2, 63], [Infinity, 64]];

  const BK2 = [[2.0, 16], [2.6, 20], [4.8, 22]];
  for (let k = 0; k <= 32; k++) BK2.push([r2(4.8 + 0.2 * (k + 1)), r2(22.16 + 0.34 * k)]);   // 4,8–11,4 m
  BK2.push([13.4, 38.0]);                                                                  // 11,4–13,4 m
  for (let k = 0; k <= 24; k++) BK2.push([r2(13.4 + 0.2 * (k + 1)), r2(38.04 + 0.52 * k)]); // 13,4–18,4 m
  BK2.push([18.5, 51.04], [Infinity, 51.4]);

  const BK3 = [[2.0, 12]];
  for (let k = 0; k <= 49; k++) BK3.push([r2(2.0 + 0.4 * (k + 1)), r2(12.5 + 0.5 * k)]);    // 2,0–22,0 m

  const BK4 = [[1.0, 11.5], [1.3, 16], [1.8, 18], [2.0, 20], [2.6, 21], [4.4, 24], [4.7, 25], [5.2, 26], [5.4, 27], [5.6, 28],
    [5.8, 29], [6.0, 30], [6.2, 31], [6.4, 32], [6.8, 33], [7.0, 34], [7.2, 35], [7.6, 36], [7.8, 37], [8.0, 38], [8.2, 39],
    [8.4, 40], [8.6, 41], [8.8, 42], [9.0, 43], [9.2, 44], [9.4, 45], [9.6, 46], [9.8, 47], [10.0, 48], [10.2, 49], [10.6, 50],
    [11.0, 51], [11.4, 52], [11.8, 53], [12.2, 54], [12.6, 55], [13.0, 56], [13.4, 57], [13.8, 58], [14.2, 59], [14.6, 60],
    [15.0, 61], [15.4, 62], [15.8, 63], [16.2, 64], [16.6, 65], [17.0, 66], [17.4, 67], [17.8, 68], [18.2, 69], [18.7, 70],
    [19.2, 71], [19.7, 72], [20.2, 73], [Infinity, 74]];

  const TABELL = { 1: BK1, 2: BK2, 3: BK3, 4: BK4 };

  function bruttograns(bk, avst) {
    if (bk === 3 && avst >= 22.0) return r2(37.5 + Math.floor(r2((avst - 22.0) / 0.2)) * 0.25);
    for (const [upp, v] of TABELL[bk]) if (avst < upp) return v;
    return null;
  }

  // Axel-, boggi- och trippelaxeltryck (12 §), index 1–4 = BK1–BK4
  function gruppGrans(g, bk) {
    const i = bk - 1;
    if (g.typ === 'enkel') return (g.driv ? [11.5, 10, 8, 11.5] : [10, 10, 8, 10])[i];
    if (g.typ === 'boggi') {
      const a = +g.avst || 0;
      if (a < 1.0) return 11.5;
      if (a < 1.3) return [16, 16, 12, 16][i];
      if (a < 1.8) return (g.luft ? [19, 16, 12, 19] : [18, 16, 12, 18])[i];
      return [20, 16, 12, 20][i];
    }
    if (g.typ === 'trippel') {
      const a = +g.avst || 0;
      if (a < 2.6) return [21, 20, 13, 21][i];
      if (a < 4.4) return [24, 22, 13, 24][i];
      if (a < 4.7) return [25, 22, 13, 25][i];
      return [26, 22, 13, 26][i];
    }
    return null;
  }
  const GRUPPNAMN = { enkel: 'Axel', boggi: 'Boggi', trippel: 'Trippelaxel' };

  /* Bedömer ekipaget för varje bärighetsklass.
     fordon = { vikt, axelavst, grupper: [{ typ, driv, avst, luft, tryck }] } */
  function bedom(fordon) {
    const ut = {};
    for (const bk of [1, 2, 3, 4]) {
      const skal = [];
      const vikt = +fordon.vikt || 0, avst = +fordon.axelavst || 0;
      const gb = bruttograns(bk, avst);
      if (vikt > gb) skal.push(`bruttovikt ${fmt(vikt)} t > ${fmt(gb)} t`);
      (fordon.grupper || []).forEach((g, n) => {
        const gg = gruppGrans(g, bk);
        if (gg != null && (+g.tryck || 0) > gg) skal.push(`${GRUPPNAMN[g.typ]} ${n + 1}: ${fmt(+g.tryck)} t > ${fmt(gg)} t`);
      });
      ut[bk] = { ok: skal.length === 0, skal, brutto: gb };
    }
    return ut;
  }
  const fmt = (x) => String(r2(x)).replace('.', ',');

  // Sammanlagt axeltryck – används för att varna om summan inte stämmer med bruttovikten
  const summaTryck = (fordon) => r2((fordon.grupper || []).reduce((s, g) => s + (+g.tryck || 0), 0));

  return { bedom, bruttograns, gruppGrans, summaTryck, GRUPPNAMN };
})();
if (typeof module !== 'undefined') module.exports = Vikt;
