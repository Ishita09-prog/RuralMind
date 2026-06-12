// RuralMind service worker — caches the app shell so it loads offline.
const CACHE = "ruralmind-v1";
const SHELL = ["/", "/index.html", "/manifest.webmanifest", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // Never cache the AI/API calls (they need the live server + Ollama).
  if (url.port === "8000" || url.pathname.startsWith("/ask") ||
      url.pathname.startsWith("/quiz") || url.pathname.startsWith("/diagram") ||
      url.pathname.startsWith("/ocr") || url.pathname.startsWith("/translate") ||
      url.pathname.startsWith("/worksheet") || url.pathname.startsWith("/audio")) {
    return; // let the browser handle it normally
  }

  // App shell + static assets: serve from cache, fall back to network.
  e.respondWith(
    caches.match(e.request).then((hit) =>
      hit || fetch(e.request).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
        return res;
      }).catch(() => hit)
    )
  );
});
