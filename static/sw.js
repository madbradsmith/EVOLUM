const CACHE = 'evolum-v4';
const STATIC = [
  '/static/style.css',
  '/static/main.js',
  '/static/logo.png',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/manifest.json',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = e.request.url;
  // Static assets: cache first, but only cache full 200 responses
  // (skip 206 partial responses from video range requests)
  if (url.includes('/static/')) {
    e.respondWith(
      caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
        if (res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      }))
    );
    return;
  }
  // Everything else: network first, no offline fallback (needs server)
});
