/* Service worker do RDC Inteligente.
 * - Páginas: rede primeiro (com tempo limite, para sinal fraco do dique); sem rede, usa a cópia guardada.
 * - Bootstrap e fontes (CDN): guardados para as telas abrirem formatadas sem sinal.
 * - Envios (POST) não passam por aqui: a caixa de saída (static/js/offline.js) cuida deles.
 */
const RDC_CACHE = "rdc-mobile-cache-v8";
const OFFLINE_URL = "/offline/";
const TEMPO_REDE_MS = 7000;

const APP_SHELL = [
  "/m/",
  "/offline/",
  "/static/manifest.json",
  "/static/favicon.ico",
  "/static/css/dorange.css",
  "/static/js/offline.js",
];
const ORIGENS_EXTERNAS = ["https://cdn.jsdelivr.net", "https://fonts.googleapis.com", "https://fonts.gstatic.com"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(RDC_CACHE).then((cache) => cache.addAll(APP_SHELL)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.map((key) => (key !== RDC_CACHE ? caches.delete(key) : null))))
  );
  self.clients.claim();
});

function comTempo(promessa, ms) {
  return new Promise((ok, erro) => {
    const t = setTimeout(() => erro(new Error("timeout")), ms);
    promessa.then((r) => { clearTimeout(t); ok(r); }, (e) => { clearTimeout(t); erro(e); });
  });
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  const mesmaOrigem = url.origin === self.location.origin;
  const externa = ORIGENS_EXTERNAS.includes(url.origin);
  if (!mesmaOrigem && !externa) return;
  if (mesmaOrigem && (url.pathname.startsWith("/admin/") || url.pathname.startsWith("/accounts/"))) return;

  if (externa) {
    // CDN: cache primeiro (arquivos versionados não mudam)
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request).then((resp) => {
        const copia = resp.clone();
        caches.open(RDC_CACHE).then((cache) => cache.put(request, copia));
        return resp;
      }))
    );
    return;
  }

  event.respondWith(
    comTempo(fetch(request), TEMPO_REDE_MS)
      .then((response) => {
        if (response.ok && !response.redirected) {
          const copia = response.clone();
          caches.open(RDC_CACHE).then((cache) => cache.put(request, copia));
        }
        return response;
      })
      .catch(() => caches.match(request).then((cached) => cached || caches.match(OFFLINE_URL)))
  );
});
