# Lastväg

En webbapp för lastbilsförare som visar höjdhinder (låga broar, viadukter, portaler) på svenska vägar,
enligt Trafikverkets vägdatabas NVDB. Fabler & Fakta Studio.

**Fordon**
- Spara flera fordon/ekipage: namn, regnummer, typ, höjd, bredd, längd, bruttovikt, tjänstevikt,
  axelavstånd och alla axlar/boggier/trippelaxlar med tryck. Byt aktivt fordon under Inställningar.
- Appen räknar ut vilka bärighetsklasser (BK1–BK4) ekipaget får köra på, enligt trafikförordningens
  bruttoviktstabeller (bilaga 1–4) och 4 kap. 12 § (axel-, boggi- och trippelaxeltryck).

**Farligt gods (ADR)**
- Slå på ADR för ett fordon och ange lastens tunnelrestriktionskod (B, B1000C, B/D … E), tank/bulk och
  nettoexplosivmassa. Appen räknar ut vilka tunnelkategorier som är förbjudna (ADR 8.6.4), visar förbjudna
  sträckor och rekommenderade vägar för farligt gods på kartan och varnar i körläget.
- Länkar till lokala trafikföreskrifter (STFS, www.stfs.se) och NVDB på karta finns i Inställningar.

**Tre lägen**
- **Karta** – alla hinder på kartan, färgade efter ditt fordons höjd (röd = för lågt, gul = nära gränsen, grön = OK).
- **Lista** – hindren närmast dig, sorterade på avstånd.
- **Körläge** – slår på av sig självt när du kör (över ca 15 km/h) och stängs när du stått still en minut.
  Visar nästa hinder i färdriktningen med stora siffror och säger till med röst.
  Mörkt läge slås på automatiskt efter solnedgång.

## Riktig data från Trafikverket
Appen levereras med **exempeldata**. Så byter du till riktiga höjdhinder:
1. Skapa ett gratis konto på https://lastkajen.trafikverket.se
2. Beställ vägdata med företeelsen *Höjdhinder upp till 4,5 meter* för hela Sverige, som GeoPackage (.gpkg) eller GeoJSON.
3. Kör: `python3 verktyg/nvdb_till_json.py Hojdhinder.gpkg data/hinder.json`
4. Bärighet: beställ företeelsen *Bärighet* och kör `python3 verktyg/nvdb_till_json.py --bk Barighet.gpkg data/bk.json`
5. Farligt gods: beställ företeelserna för farligt gods (rekommenderad väg, inskränkningar, tunnlar) och kör
   `python3 verktyg/nvdb_till_json.py --adr FarligtGods.gpkg data/adr.json` – kontrollera att kategorierna blev rätt.
6. Publicera om. (Eller ladda filen direkt i appen under Inställningar → Ladda egen datafil.)

Vägdatan är öppen (CC0). Kartan: © OpenStreetMap, © CARTO.

## Begränsningar
- Följ alltid skyltningen. Datan kan vara fel eller inaktuell.
- Hinder högre än 4,5 m och tillfälliga hinder (vägarbeten) finns inte med i NVDB.
- Viktberäkningen tar inte hänsyn till lokala viktbegränsningar på broar, tjällossning, särregler för enskilda fordon eller dispenser.
- Bredd och längd sparas men kontrolleras ännu inte mot vägdata.
- Körläget visar hinder i färdriktningen inom 3 km, men vet inte vilken väg du kommer att ta.

## Publicera
Statisk sajt – fungerar direkt på GitHub Pages. Kan installeras på hemskärmen (PWA).

## Integritet och licenser
- Integritetspolicy: `integritet.html`
- Leaflet 1.9.4 (BSD-2, `lib/leaflet/LICENSE`) och Barlow-typsnitten (SIL OFL 1.1, `lib/fonts/OFL.txt`) ligger i appen – inga anrop till unpkg eller Google Fonts.

## Språk
- Svenska (grund), engelska, polska och rumänska. Språkfilerna ligger i `lang/` och laddas ner när föraren väljer språk.
- Översättningarna redigeras i `verktyg/sprakfiler.py` (en rad per text: svenska, engelska, polska, rumänska). Kör `python3 verktyg/sprakfiler.py` efteråt.
- Polska och rumänska är märkta "Översatt – ej granskat" tills någon med språket som modersmål har granskat dem. Sätt då `granskad: True` i `i18n.js`.
