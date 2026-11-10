// Service worker minimal : met le site en cache pour qu'il marche hors ligne.
// Changer CACHE force le renouvellement complet du cache.
const CACHE = 'swing-do-samba-v1';
const SHELL = ['./manifest.webmanifest', './icon.svg', './icon-192.png', './icon-512.png'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      // Les fichiers JS/CSS ont un nom haché : on les lit dans index.html.
      const response = await fetch('./index.html', { cache: 'no-cache' });
      const html = await response.clone().text();
      const assets = [...html.matchAll(/(?:src|href)="(\.\/assets\/[^"]+)"/g)].map((m) => m[1]);
      await cache.put('./index.html', response);
      await cache.addAll([...assets, ...SHELL]);

      // Retire les fichiers d'une version précédente.
      const keep = new Set(
        ['./index.html', ...assets, ...SHELL].map((path) => new URL(path, self.location).href),
      );
      for (const request of await cache.keys()) {
        if (!keep.has(request.url)) await cache.delete(request);
      }
      await self.skipWaiting();
    })(),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(names.filter((name) => name !== CACHE).map((name) => caches.delete(name)));
      await self.clients.claim();
    })(),
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;

  event.respondWith(
    (async () => {
      const cache = await caches.open(CACHE);
      if (request.mode === 'navigate') {
        // Page : réseau d'abord pour récupérer les mises à jour, cache sinon.
        try {
          const fresh = await fetch(request);
          if (fresh.ok) await cache.put('./index.html', fresh.clone());
          return fresh;
        } catch {
          return (await cache.match('./index.html')) ?? Response.error();
        }
      }
      // Fichiers : cache d'abord (leur nom change à chaque build).
      return (await cache.match(request)) ?? fetch(request);
    })(),
  );
});
