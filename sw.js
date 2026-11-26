// Lastväg – enkel offline-cache för appens egna filer (kartbilderna kräver nät)
const CACHE = 'lastvag-v2';
const FILER = ['./', 'index.html', 'style.css', 'app.js', 'vikt.js', 'i18n.js', 'data/hinder.json', 'data/bk.json', 'data/adr.json', 'manifest.webmanifest', 'icon.svg', 'icon-192.png', 'icon-512.png', 'integritet.html', 'lib/leaflet/leaflet.js', 'lib/leaflet/leaflet.css', 'lib/fonts/fonts.css', 'lib/fonts/Barlow-Regular.woff', 'lib/fonts/Barlow-Medium.woff', 'lib/fonts/Barlow-SemiBold.woff', 'lib/fonts/Barlow-Bold.woff', 'lib/fonts/BarlowCondensed-SemiBold.woff', 'lib/fonts/BarlowCondensed-Bold.woff', 'lib/fonts/BarlowCondensed-ExtraBold.woff'];
self.addEventListener('install', (e) => e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILER)).then(() => self.skipWaiting())));
self.addEventListener('activate', (e) => e.waitUntil(caches.keys().then((k) => Promise.all(k.filter((n) => n !== CACHE).map((n) => caches.delete(n)))).then(() => self.clients.claim())));
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  // Nät först, cache som reserv – så att ny data slår igenom direkt
  e.respondWith(fetch(e.request, { cache: 'no-store' }).then((svar) => {
    const kopia = svar.clone();
    caches.open(CACHE).then((c) => c.put(e.request, kopia)).catch(() => {});
    return svar;
  }).catch(() => caches.match(e.request)));
});
