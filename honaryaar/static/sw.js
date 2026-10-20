/* Minimal PWA worker: enough for installability, no offline cache, no request delay. */
self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

// Chrome installability requires a fetch listener. Do not call respondWith —
// the browser handles the network directly (no SW proxy delay).
self.addEventListener("fetch", () => {});
