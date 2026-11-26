/* Lastväg – språk
   Appen skrivs på svenska. Andra språk är filer i lang/<kod>.json som laddas ner när föraren
   väljer språket (och sparas sedan i telefonen). Filen har två delar:
     "text":    svensk text → översättning (exakt matchning)
     "monster": svensk text med {platshållare} → översättning, för texter med siffror och namn
   All text som visas i appen översätts automatiskt när den hamnar på skärmen. */
const I18N = (() => {
  'use strict';
  const SPRAK = {
    sv: { namn: 'Svenska', granskad: true },
    en: { namn: 'English', granskad: true },
    pl: { namn: 'Polski', granskad: false },
    ro: { namn: 'Română', granskad: false }
  };
  const NYCKEL = 'lastvag.sprak';
  let sprak = 'sv', text = {}, monster = [];
  const ATTR = ['aria-label', 'placeholder', 'title'];
  const HOPPA = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'svg', 'SVG', 'CODE']);

  function kompilera(lista) {
    return Object.entries(lista || {}).map(([fran, till]) => {
      const namn = [];
      const re = fran.replace(/[.*+?^${}()|[\]\\]/g, (c) => '\\' + c)
        .replace(/\\\{(\w+)\\\}/g, (m, n) => { namn.push(n); return '(.+?)'; });
      return { re: new RegExp('^' + re + '$'), namn, till };
    });
  }
  function oversatt(s) {
    if (sprak === 'sv' || !s) return s;
    const trim = s.trim().replace(/\s+/g, ' ');
    if (!trim || !/[A-Za-zÅÄÖåäö]/.test(trim)) return s;
    let ut = text[trim];
    if (ut == null) {
      for (const m of monster) {
        const traff = trim.match(m.re);
        if (traff) {
          const varden = {};
          m.namn.forEach((n, i) => { varden[n] = oversatt(traff[i + 1]); });
          ut = m.till.replace(/\{(\w+)\}/g, (x, n) => (n in varden ? varden[n] : x));
          break;
        }
      }
    }
    if (ut == null) {
      // Sammansatta texter: översätt varje del för sig (delar med " · " eller ", ")
      const delar = trim.split(/(\s+·\s*|\s*·\s+|,\s+)/);
      if (delar.length > 1) {
        let andrad = false;
        const ny = delar.map((d, i) => { if (i % 2) return d; const o = oversatt(d); if (o !== d) andrad = true; return o; }).join('');
        if (andrad) ut = ny;
      }
    }
    if (ut == null) return s;
    const fore = s.match(/^\s*/)[0], efter = s.match(/\s*$/)[0];
    return fore + ut + efter;
  }
  function nod(n) {
    if (n.nodeType === 3) {
      const p = n.parentNode;
      if (!p || HOPPA.has(p.nodeName) || (p.closest && p.closest('[data-ingen-oversattning]'))) return;
      if (n.__sv === undefined || (n.__ut !== undefined && n.nodeValue !== n.__ut)) n.__sv = n.nodeValue;
      const ny = oversatt(n.__sv);
      n.__ut = ny;
      if (n.nodeValue !== ny) n.nodeValue = ny;
    } else if (n.nodeType === 1) {
      if (HOPPA.has(n.nodeName) || n.hasAttribute('data-ingen-oversattning')) return;
      for (const a of ATTR) {
        if (!n.hasAttribute(a)) continue;
        const k = 'sv' + a.replace(/-./g, (x) => x[1].toUpperCase()).replace(/^./, (x) => x.toUpperCase());
        const nu = n.getAttribute(a);
        if (n.dataset[k] === undefined || n.dataset[k + 'Ut'] !== nu) n.dataset[k] = nu;
        const ny = oversatt(n.dataset[k]);
        n.dataset[k + 'Ut'] = ny;
        if (nu !== ny) n.setAttribute(a, ny);
      }
      for (const c of n.childNodes) nod(c);
    }
  }
  let observer = null, upptagen = false;
  function bevaka() {
    if (observer) return;
    observer = new MutationObserver((lista) => {
      if (upptagen || sprak === 'sv') return;
      upptagen = true;
      try {
        for (const m of lista) {
          if (m.type === 'characterData') nod(m.target);
          else if (m.type === 'attributes') nod(m.target);
          else m.addedNodes.forEach(nod);
        }
      } finally { upptagen = false; }
    });
    observer.observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTR });
  }
  async function valj(kod) {
    if (!SPRAK[kod]) kod = 'sv';
    if (kod === 'sv') { text = {}; monster = []; }
    else {
      const svar = await fetch(`lang/${kod}.json?v=1`, { cache: 'no-cache' });
      if (!svar.ok) throw new Error('Språkfilen kunde inte laddas');
      const fil = await svar.json();
      text = {};
      for (const [k, v] of Object.entries(fil.text || {})) text[k.trim().replace(/\s+/g, ' ')] = v;
      monster = kompilera(fil.monster);
    }
    sprak = kod;
    try { localStorage.setItem(NYCKEL, kod); } catch (e) {}
    document.documentElement.lang = kod;
    upptagen = true;
    try { nod(document.body); document.title = 'Lastväg'; } finally { upptagen = false; }
    bevaka();
    return kod;
  }
  function sparat() {
    let k = null;
    try { k = localStorage.getItem(NYCKEL); } catch (e) {}
    if (k && SPRAK[k]) return k;
    const telefon = (navigator.language || 'sv').slice(0, 2).toLowerCase();
    return SPRAK[telefon] ? telefon : 'sv';
  }
  return { SPRAK, valj, sparat, t: oversatt, get sprak() { return sprak; } };
})();
