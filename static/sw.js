const ROOT = new URL(self.registration.scope).pathname.replace(/\/$/, "");
const CACHE_PREFIX = "restaurant-scope-" + ROOT + "-";
const CACHE = CACHE_PREFIX + "v1";
function safeOrderURL(value) {
  try {
    const url = new URL(value, self.location.origin);
    const local =
      ROOT && url.pathname.startsWith(ROOT + "/")
        ? url.pathname.slice(ROOT.length)
        : url.pathname;
    if (
      url.origin !== self.location.origin ||
      (ROOT && !url.pathname.startsWith(ROOT + "/")) ||
      !["/pedidos", "/meus-pedidos", "/entregas", "/salao/meus-pedidos"].includes(local)
    )
      return ROOT + "/pedidos";
    const id = url.searchParams.get("pedido");
    return ROOT + local + (id && /^\d+$/.test(id) ? "?pedido=" + id : "");
  } catch {
    return ROOT + "/pedidos";
  }
}
const ASSETS = [
  "/static/js/restaurant_scope.js",
  "/static/css/operations.css",
  "/static/js/br-fields.js",
  "/static/css/appearance.css",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/js/sound.js",
  "/static/js/entregas.js",
  "/static/js/acerto_entregadores.js",
  "/static/js/pdv.js",
  "/static/js/pwa.js",
  "/static/js/cardapio.js",
  "/static/js/customer_forms.js",
  "/static/offline.html",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
].map((path) => ROOT + path);
self.addEventListener("install", (e) => {
  e.waitUntil(
    caches
      .open(CACHE)
      .then((c) => c.addAll(ASSETS))
      .then(() => self.skipWaiting()),
  );
});
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k.startsWith(CACHE_PREFIX) && k !== CACHE)
            .map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== self.location.origin) return;
  if (e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request).catch(() => caches.match(ROOT + "/static/offline.html")),
    );
    return;
  }
  // Nunca armazenar HTML autenticado, APIs, pedidos ou dados pessoais.
  if (ASSETS.includes(url.pathname))
    e.respondWith(
      fetch(e.request)
        .then((r) => {
          if (r.ok) {
            let copy = r.clone();
            caches.open(CACHE).then((c) => c.put(url.pathname, copy));
          }
          return r;
        })
        .catch(() => caches.match(url.pathname)),
    );
});
self.addEventListener("push", (e) => {
  e.waitUntil(
    (async () => {
      let data;
      try {
        data = e.data.json();
      } catch {
        return;
      }
      const windows = await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });
      const scopedWindows = windows.filter((c) =>
        new URL(c.url).pathname.startsWith(ROOT + "/"),
      );
      const shown = scopedWindows.some((c) => c.visibilityState === "visible");
      scopedWindows.forEach((c) =>
        c.postMessage({ type: "push-update", data }),
      );
      // O aviso nativo continua sendo exibido para cumprir as regras de push do navegador.
      await self.registration.showNotification(
        data.title || "Restaurante Manager",
        {
          body: data.body || "Há uma atualização no atendimento.",
          icon: ROOT + "/static/icons/icon-192.png",
          badge: ROOT + "/static/icons/icon-192.png",
          tag: "pedido-" + data.id,
          data: {
            url: safeOrderURL(data.url),
          },
          silent: shown,
        },
      );
    })(),
  );
});
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  e.waitUntil(
    (async () => {
      const windows = await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });
      const url = safeOrderURL(e.notification.data?.url);
      const target = windows.find(
        (c) =>
          new URL(c.url).origin === self.location.origin &&
          new URL(c.url).pathname.startsWith(ROOT + "/"),
      );
      if (target) {
        await target.navigate(url);
        return target.focus();
      }
      return self.clients.openWindow(url);
    })(),
  );
});
