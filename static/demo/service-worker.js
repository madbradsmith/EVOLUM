// service-worker.js — Simutum PWA shell
// Caches all static assets so the demo runs offline once visited.

const CACHE_NAME = 'simutum-v1';
const ASSETS = [
  'index.html',
  'editor.html',
  'signup.html',
  'tribe-finder.html',
  'store.html',
  'visitor-dashboard.html',
  'press.html',
  '404.html',
  'roadmap.html',
  'avatar-card.html',
  'world-card.html',
  'replay-viewer.html',
  'manifest.json',
  'og-preview.png',
  // runtime modules
  'geometry.js',
  'scene-build.js',
  'scene-stops.js',
  'scene-entities.js',
  'scene-audio.js',
  'scene-runtime.js',
  'tweaks-panel.jsx',
  'app.jsx',
  // editor modules
  'editor-styles.css',
  'editor-state.js',
  'editor-export.js',
  'editor-preview.js',
  'editor-map.jsx',
  'editor-inspector.jsx',
  'editor-entities.jsx',
  'editor-wizard.jsx',
  'editor-play.jsx',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS).catch(() => null))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  // Only handle GET to our origin
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then((hit) => {
      if (hit) return hit;
      return fetch(e.request).then((res) => {
        // Cache successful same-origin responses
        if (res.ok && new URL(e.request.url).origin === location.origin) {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(e.request, copy));
        }
        return res;
      }).catch(() => caches.match('index.html'));
    })
  );
});
