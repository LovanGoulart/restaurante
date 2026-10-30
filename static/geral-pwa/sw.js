"use strict";

const SCOPE = new URL(self.registration.scope);
const CACHE_PREFIX = "manager-owner-pwa-" + SCOPE.pathname + "-";
const CACHE = CACHE_PREFIX + "v1";
const OFFLINE = new URL("pwa/offline.html", SCOPE).href;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.add(OFFLINE)).then(() => self.skipWaiting()),
  );
});
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) => Promise.all(
      names.filter((name) => name.startsWith(CACHE_PREFIX) && name !== CACHE)
        .map((name) => caches.delete(name)),
    )).then(() => self.clients.claim()),
  );
});
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || event.request.mode !== "navigate" ||
      url.origin !== SCOPE.origin || !url.pathname.startsWith(SCOPE.pathname)) return;
  // Apenas o aviso genérico fica em cache. Nunca guardar sessões, páginas ou dados.
  event.respondWith(fetch(event.request).catch(async () => {
    const offline = await caches.match(OFFLINE);
    return offline || new Response("Sem conexão. Reconecte para acessar o painel geral.", {
      status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }));
});
