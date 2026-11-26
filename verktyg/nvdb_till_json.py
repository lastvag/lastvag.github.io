#!/usr/bin/env python3
"""
Gör om Trafikverkets höjdhinder (NVDB, från Lastkajen) till data/hinder.json för appen Lastväg.

Användning:
    python3 nvdb_till_json.py <fil.gpkg eller fil.geojson> [data/hinder.json]
    python3 nvdb_till_json.py --bk <fil.gpkg eller fil.geojson> [data/bk.json]

--bk gör om vägsträckor med bärighetsklass (företeelsen "Bärighet") till data/bk.json.
Vägar med BK1 hoppas över, eftersom allmän väg är BK1 om inget annat sägs.
Lägg till --alla för att ta med BK1 också.

    python3 nvdb_till_json.py --adr <fil.gpkg eller fil.geojson> [data/adr.json]

--adr gör om NVDB:s företeelser för farligt gods (rekommenderad väg, förbud/inskränkningar
och tunnelkategori) till data/adr.json. Kategori: R = rekommenderad, B–E = tunnelkategori,
allmänt förbud mot farligt gods räknas som E. Kontrollera resultatet – attributnamnen kan variera.

- Hämta datan gratis på https://lastkajen.trafikverket.se (skapa konto, välj vägdata
  med företeelsen "Höjdhinder upp till 4,5 meter", format GeoPackage eller GeoJSON).
- Koordinater i SWEREF 99 TM (EPSG:3006) räknas om till WGS84.
- Kräver bara Python 3, inga extra paket.
"""
import json, math, re, sqlite3, struct, sys, datetime

HOJD = re.compile(r"fri.?h|h[oö]jd|height", re.I)
NAMN = re.compile(r"^(namn|name|beskrivning|typ)", re.I)
VAG = re.compile(r"v[aä]g.?n|vagnummer|road|^v[aä]g$", re.I)


def sweref99tm_till_wgs84(northing, easting):
    a, f, lon0, k0, fe = 6378137.0, 1 / 298.257222101, math.radians(15.0), 0.9996, 500000.0
    e2 = f * (2 - f); n = f / (2 - f)
    ar = a / (1 + n) * (1 + n**2 / 4 + n**4 / 64)
    d1 = n / 2 - 2 * n**2 / 3 + 37 * n**3 / 96 - n**4 / 360
    d2 = n**2 / 48 + n**3 / 15 - 437 * n**4 / 1440
    d3 = 17 * n**3 / 480 - 37 * n**4 / 840
    d4 = 4397 * n**4 / 161280
    As = e2 + e2**2 + e2**3 + e2**4
    Bs = -(7 * e2**2 + 17 * e2**3 + 30 * e2**4) / 6
    Cs = (224 * e2**3 + 889 * e2**4) / 120
    Ds = -(4279 * e2**4) / 1260
    xi = northing / (k0 * ar); eta = (easting - fe) / (k0 * ar)
    xp = xi - sum(d * math.sin(2 * k * xi) * math.cosh(2 * k * eta) for k, d in enumerate((d1, d2, d3, d4), 1))
    ep = eta - sum(d * math.cos(2 * k * xi) * math.sinh(2 * k * eta) for k, d in enumerate((d1, d2, d3, d4), 1))
    phi = math.asin(math.sin(xp) / math.cosh(ep))
    lon = lon0 + math.atan(math.sinh(ep) / math.cos(xp))
    s = math.sin(phi) ** 2
    lat = phi + math.sin(phi) * math.cos(phi) * (As + Bs * s + Cs * s * s + Ds * s**3)
    return math.degrees(lat), math.degrees(lon)


def till_wgs(x, y):
    """x = öst/longitud, y = nord/latitud."""
    if abs(x) <= 180 and abs(y) <= 90:
        return y, x
    return sweref99tm_till_wgs84(y, x)


def tal(v):
    if v is None or v == "":
        return None
    try:
        t = float(str(v).replace(",", "."))
    except ValueError:
        return None
    return t if 0 < t <= 20 else None


# ---------- GeoPackage ----------
def las_wkb(b, o=0):
    """Returnerar (x, y) för en representativ punkt i en WKB-geometri."""
    end = "<" if b[o] == 1 else ">"
    typ = struct.unpack_from(end + "I", b, o + 1)[0]
    iso = (typ & 0x0FFFFFFF) // 1000          # 0 = 2D, 1 = Z, 2 = M, 3 = ZM
    har_z = bool(typ & 0x80000000) or iso in (1, 3)
    har_m = bool(typ & 0x40000000) or iso in (2, 3)
    bas = (typ & 0x0FFFFFFF) % 1000
    dim = 2 + har_z + har_m
    o += 5
    if bas == 1:  # Point
        return struct.unpack_from(end + "dd", b, o)
    if bas == 2:  # LineString – mittersta punkten
        n = struct.unpack_from(end + "I", b, o)[0]
        i = n // 2
        return struct.unpack_from(end + "dd", b, o + 4 + i * 8 * dim)
    if bas in (4, 5, 6, 7):  # Multi* / GeometryCollection – första delen
        return las_wkb(b, o + 4)
    if bas == 3:  # Polygon – första punkten
        return struct.unpack_from(end + "dd", b, o + 8)
    raise ValueError(f"Okänd geometrityp {typ}")


def las_gpkg_geom(blob):
    if blob is None or blob[:2] != b"GP":
        return None
    flaggor = blob[3]
    env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get((flaggor >> 1) & 0x07, 0)
    if flaggor & 0x10:  # tom geometri
        return None
    return las_wkb(blob, 8 + env)


def las_gpkg(sokvag):
    db = sqlite3.connect(sokvag)
    tabeller = [r[0] for r in db.execute("select table_name from gpkg_contents where data_type='features'")]
    hojdtab = [t for t in tabeller if re.search(r"h[oö]jd", t, re.I)]
    for tab in hojdtab or tabeller:
        geomkol = db.execute("select column_name from gpkg_geometry_columns where table_name=?", (tab,)).fetchone()
        if not geomkol:
            continue
        cur = db.execute(f'select * from "{tab}"')
        kolumner = [d[0] for d in cur.description]
        hkol = next((k for k in kolumner if HOJD.search(k) and k != geomkol[0]), None)
        if not hkol:
            continue
        print(f"  Tabell {tab}: höjd i kolumnen '{hkol}'", file=sys.stderr)
        for rad in cur:
            p = dict(zip(kolumner, rad))
            try:
                xy = las_gpkg_geom(p[geomkol[0]])
            except Exception:
                xy = None
            if xy:
                yield p, xy


# ---------- Linjer (för bärighet) ----------
def las_wkb_linjer(b, o=0):
    """Returnerar (lista med linjer [[(x, y), ...]], ny offset)."""
    end = "<" if b[o] == 1 else ">"
    typ = struct.unpack_from(end + "I", b, o + 1)[0]
    iso = (typ & 0x0FFFFFFF) // 1000
    har_z = bool(typ & 0x80000000) or iso in (1, 3)
    har_m = bool(typ & 0x40000000) or iso in (2, 3)
    bas = (typ & 0x0FFFFFFF) % 1000
    dim = 2 + har_z + har_m
    o += 5
    if bas == 1:
        x, y = struct.unpack_from(end + "dd", b, o)
        return [[(x, y)]], o + 8 * dim
    if bas == 2:
        n = struct.unpack_from(end + "I", b, o)[0]; o += 4
        pts = [struct.unpack_from(end + "dd", b, o + i * 8 * dim) for i in range(n)]
        return [pts], o + n * 8 * dim
    if bas == 3:
        nr = struct.unpack_from(end + "I", b, o)[0]; o += 4; ut = []
        for _ in range(nr):
            n = struct.unpack_from(end + "I", b, o)[0]; o += 4
            ut.append([struct.unpack_from(end + "dd", b, o + i * 8 * dim) for i in range(n)]); o += n * 8 * dim
        return ut, o
    if bas in (4, 5, 6, 7):
        n = struct.unpack_from(end + "I", b, o)[0]; o += 4; ut = []
        for _ in range(n):
            delar, o = las_wkb_linjer(b, o); ut.extend(delar)
        return ut, o
    raise ValueError(f"Okänd geometrityp {typ}")


def gpkg_linjer(blob):
    if blob is None or blob[:2] != b"GP" or blob[3] & 0x10:
        return []
    env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get((blob[3] >> 1) & 0x07, 0)
    return las_wkb_linjer(blob, 8 + env)[0]


def forenkla(pts, tol):
    """Douglas–Peucker."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1; l = math.hypot(dx, dy) or 1e-12
    imax, dmax = 0, -1
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / l
        if d > dmax:
            imax, dmax = i, d
    if dmax <= tol:
        return [pts[0], pts[-1]]
    return forenkla(pts[:imax + 1], tol)[:-1] + forenkla(pts[imax:], tol)


BK = re.compile(r"b[aä]righet|^bk$", re.I)
TJAL = re.compile(r"tj[aä]l", re.I)


def bk_varde(v):
    m = re.search(r"[1-4]", str(v if v is not None else ""))
    return int(m.group()) if m else None


def bk_kalla(sokvag):
    if sokvag.lower().endswith(".gpkg"):
        db = sqlite3.connect(sokvag)
        tabeller = [r[0] for r in db.execute("select table_name from gpkg_contents where data_type='features'")]
        for tab in [t for t in tabeller if re.search(r"b[aä]righet", t, re.I)] or tabeller:
            gk = db.execute("select column_name from gpkg_geometry_columns where table_name=?", (tab,)).fetchone()
            if not gk:
                continue
            cur = db.execute(f'select * from "{tab}"')
            kol = [d[0] for d in cur.description]
            bkol = next((k for k in kol if BK.search(k) and not TJAL.search(k)), None)
            if not bkol:
                continue
            print(f"  Tabell {tab}: bärighetsklass i kolumnen '{bkol}'", file=sys.stderr)
            for rad in cur:
                p = dict(zip(kol, rad))
                try:
                    linjer = gpkg_linjer(p[gk[0]])
                except Exception:
                    linjer = []
                yield bk_varde(p[bkol]), linjer
    else:
        with open(sokvag, encoding="utf-8") as f:
            fc = json.load(f)
        for ft in fc.get("features", []):
            p = ft.get("properties") or {}
            v = next((v for k, v in p.items() if BK.search(k) and not TJAL.search(k)), None)
            g = ft.get("geometry") or {}
            c = g.get("coordinates") or []
            linjer = [c] if g.get("type") == "LineString" else c if g.get("type") == "MultiLineString" else []
            yield bk_varde(v), [[(pt[0], pt[1]) for pt in l] for l in linjer]


def main_bk(inn, ut, alla):
    segment = []
    for bk, linjer in bk_kalla(inn):
        if not bk or (bk == 1 and not alla):
            continue
        for l in linjer:
            if len(l) < 2:
                continue
            projicerad = abs(l[0][0]) > 180
            l = forenkla(l, 5.0 if projicerad else 0.00005)
            platt = []
            for x, y in l:
                lat, lon = till_wgs(x, y)
                platt += [round(lat, 5), round(lon, 5)]
            segment.append([bk, platt])
    if not segment:
        print("Hittade inga vägsträckor med bärighetsklass.", file=sys.stderr)
        sys.exit(2)
    with open(ut, "w", encoding="utf-8") as f:
        json.dump({"kalla": "Trafikverket NVDB via Lastkajen (CC0)", "uppdaterad": datetime.date.today().isoformat(),
                   "exempel": False, "segment": segment}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Klart: {len(segment)} vägsträckor sparade i {ut}", file=sys.stderr)


# ---------- Farligt gods ----------
TUNNELKAT = re.compile(r"tunnel.?kat|kategori", re.I)
NAMNKOL = re.compile(r"^(namn|name|tunnelnamn|benamning|beskrivning)$", re.I)


def adr_kategori(tabell, p):
    for k, v in p.items():
        if TUNNELKAT.search(k) and v not in (None, ""):
            m = re.search(r"\b([B-E])\b", str(v).upper())
            if m:
                return m.group(1)
    if re.search(r"rek", tabell, re.I) or any(re.search(r"rek", str(k), re.I) and v not in (None, "", 0, "0", "Nej") for k, v in p.items()):
        return "R"
    return "E"


def adr_kalla(sokvag):
    if sokvag.lower().endswith(".gpkg"):
        db = sqlite3.connect(sokvag)
        tabeller = [r[0] for r in db.execute("select table_name from gpkg_contents where data_type='features'")]
        for tab in [t for t in tabeller if re.search(r"farl|gods|tunnel|adr", t, re.I)] or tabeller:
            gk = db.execute("select column_name from gpkg_geometry_columns where table_name=?", (tab,)).fetchone()
            if not gk:
                continue
            cur = db.execute(f'select * from "{tab}"')
            kol = [d[0] for d in cur.description]
            print(f"  Tabell {tab}", file=sys.stderr)
            for rad in cur:
                p = dict(zip(kol, rad))
                geom = p.pop(gk[0])
                try:
                    linjer = gpkg_linjer(geom)
                except Exception:
                    linjer = []
                yield adr_kategori(tab, p), next((str(v) for k, v in p.items() if NAMNKOL.search(k) and v), ""), linjer
    else:
        with open(sokvag, encoding="utf-8") as f:
            fc = json.load(f)
        for ft in fc.get("features", []):
            p = ft.get("properties") or {}
            g = ft.get("geometry") or {}
            c = g.get("coordinates") or []
            linjer = [c] if g.get("type") == "LineString" else c if g.get("type") == "MultiLineString" else []
            yield adr_kategori(sokvag, p), next((str(v) for k, v in p.items() if NAMNKOL.search(k) and v), ""), \
                [[(pt[0], pt[1]) for pt in l] for l in linjer]


def main_adr(inn, ut):
    rader = []
    for kat, namn, linjer in adr_kalla(inn):
        for l in linjer:
            if len(l) < 2:
                continue
            l = forenkla(l, 5.0 if abs(l[0][0]) > 180 else 0.00005)
            platt = []
            for x, y in l:
                lat, lon = till_wgs(x, y)
                platt += [round(lat, 5), round(lon, 5)]
            rader.append([kat, platt, namn] if namn else [kat, platt])
    if not rader:
        print("Hittade inga sträckor för farligt gods.", file=sys.stderr)
        sys.exit(2)
    with open(ut, "w", encoding="utf-8") as f:
        json.dump({"kalla": "Trafikverket NVDB via Lastkajen (CC0)", "uppdaterad": datetime.date.today().isoformat(),
                   "exempel": False, "adr": rader}, f, ensure_ascii=False, separators=(",", ":"))
    from collections import Counter
    print(f"Klart: {len(rader)} sträckor sparade i {ut} – {dict(Counter(r[0] for r in rader))}", file=sys.stderr)


# ---------- GeoJSON ----------
def forsta_punkt(g):
    t, c = g.get("type"), g.get("coordinates")
    if t == "Point": return c
    if t == "LineString": return c[len(c) // 2]
    if t in ("MultiPoint",): return c[0]
    if t in ("MultiLineString", "Polygon"): return c[0][0]
    if t == "MultiPolygon": return c[0][0][0]
    return None


def las_geojson(sokvag):
    with open(sokvag, encoding="utf-8") as f:
        fc = json.load(f)
    for ft in fc.get("features", []):
        g = ft.get("geometry")
        c = forsta_punkt(g) if g else None
        if c:
            yield ft.get("properties") or {}, (c[0], c[1])


def main():
    arg = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not arg:
        print(__doc__); sys.exit(1)
    if "--adr" in sys.argv:
        main_adr(arg[0], arg[1] if len(arg) > 1 else "adr.json")
        return
    if "--bk" in sys.argv:
        main_bk(arg[0], arg[1] if len(arg) > 1 else "bk.json", "--alla" in sys.argv)
        return
    inn = arg[0]
    ut = arg[1] if len(arg) > 1 else "hinder.json"
    kalla = las_gpkg(inn) if inn.lower().endswith(".gpkg") else las_geojson(inn)
    hinder, sedda = [], set()
    for i, (p, (x, y)) in enumerate(kalla):
        h = tal(next((v for k, v in p.items() if HOJD.search(k)), None))
        if h is None:
            continue
        lat, lon = till_wgs(x, y)
        nyckel = (round(lat, 5), round(lon, 5), h)
        if nyckel in sedda:
            continue
        sedda.add(nyckel)
        namn = next((v for k, v in p.items() if NAMN.search(k) and v), None)
        vag = next((v for k, v in p.items() if VAG.search(k) and v not in (None, "")), None)
        hinder.append({"id": str(p.get("fid", p.get("id", i))), "lat": round(lat, 6), "lon": round(lon, 6),
                       "h": round(h, 2), "namn": str(namn) if namn else "Höjdhinder",
                       "vag": str(vag) if vag is not None else ""})
    if not hinder:
        print("Hittade inga höjdhinder med fri höjd. Kontrollera att filen innehåller företeelsen Höjdhinder.", file=sys.stderr)
        sys.exit(2)
    with open(ut, "w", encoding="utf-8") as f:
        json.dump({"kalla": "Trafikverket NVDB via Lastkajen (CC0)",
                   "uppdaterad": datetime.date.today().isoformat(),
                   "exempel": False, "hinder": hinder}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Klart: {len(hinder)} höjdhinder sparade i {ut}", file=sys.stderr)


if __name__ == "__main__":
    main()
