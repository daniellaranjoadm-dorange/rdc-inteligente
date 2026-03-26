const RDC_CACHE = "rdc-mobile-cache-v6";
const OFFLINE_URL = "/offline/";

const APP_SHELL = [
  "/m/",
  "/offline/",
  "/static/manifest.json",
  "/static/favicon.ico"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(RDC_CACHE).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== RDC_CACHE) {
            return caches.delete(key);
          }
        })
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;

  if (request.method !== "GET") return;

  event.respondWith(
    fetch(request)
      .then((response) => {
        const clone = response.clone();

        if (response.ok && request.url.startsWith(self.location.origin)) {
          caches.open(RDC_CACHE).then((cache) => {
            cache.put(request, clone);
          });
        }

        return response;
      })
      .catch(() => {
        return caches.match(request).then((cached) => {
          return cached || caches.match(OFFLINE_URL);
        });
      })
  );
});


