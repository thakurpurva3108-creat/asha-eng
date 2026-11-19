// Saves Vaani on the phone so it opens without internet.
const CACHE = 'vaani-v3';
const FILES = ['./', 'index.html', 'lessons.js', 'manifest.webmanifest', 'logo.webp', 'coach.webp', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});
// Open from the saved copy first (fast, works offline), and refresh it quietly in the background.
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(cached => {
      const net = fetch(e.request).then(r => {
        if (r && r.status === 200) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
        return r;
      }).catch(() => cached || (e.request.mode === 'navigate' ? caches.match('index.html') : undefined));
      return cached || net;
    })
  );
});