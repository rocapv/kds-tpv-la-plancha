// Trabajador de servicio del TPV: que la pantalla se pueda ABRIR sin red.
//
// `sinred.js` resuelve el trabajo (apuntar comandas y reenviarlas), pero si el camarero recarga
// o bloquea la tableta mientras el wifi está caído, el navegador no tiene ni el HTML que pintar.
// Aquí se guarda una copia de las cuatro piezas del TPV para ese momento.
//
// Regla, porque esta caché ya ha engañado a más de uno: **primero la red, siempre**. Con
// servidor se sirve lo que diga el servidor (y se refresca la copia); la copia solo sale cuando
// la red falla. Al cambiar el número de VERSION se tira la caché anterior entera.
//
// Lo que NUNCA se guarda: nada de `/api`. Una respuesta vieja de la API sería un precio, una
// mesa o una comanda mentirosa; para eso está la cola de `sinred.js`, que sabe lo que apuntó.

const VERSION = 'kds-tpv-v1';
const CONCHA = [
  '/tpv.html',
  '/css/estilo.css',
  '/js/comun.js',
  '/js/sesion.js',
  '/js/documento.js',
  '/js/sinred.js',
  '/js/tpv.js',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(CONCHA)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(claves => Promise.all(claves.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

/** ¿Es una de las piezas del TPV? Se compara sin el `?v=…`, que cambia en cada despliegue. */
function esDelTpv(url) {
  return url.origin === self.location.origin && CONCHA.includes(url.pathname);
}

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  const navegacion = e.request.mode === 'navigate' && url.pathname === '/tpv.html';
  if (e.request.method !== 'GET' || (!navegacion && !esDelTpv(url))) return;   // el resto, sin tocar

  e.respondWith((async () => {
    try {
      const r = await fetch(e.request);
      if (r.ok) caches.open(VERSION).then(c => c.put(e.request, r.clone()));
      return r;
    } catch (fallo) {
      const guardada = await caches.match(e.request, { ignoreSearch: true });
      if (guardada) return guardada;
      throw fallo;
    }
  })());
});
