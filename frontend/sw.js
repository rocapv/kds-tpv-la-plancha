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

const VERSION = 'kds-tpv-v9';
const CONCHA = [
  '/tpv.html',
  '/css/estilo.css',
  '/js/comun.js',
  '/js/sesion.js',
  '/js/documento.js',
  '/js/sinred.js',
  '/js/tpv.js',
];

// La carta del cliente se instala en el móvil («Añadir a pantalla de inicio»), así que también
// necesita poder abrirse sin esperar a la red. Va en el mismo trabajador porque solo puede haber
// uno por sitio, pero con su propia lista y su propia manera de responder:
//
//   · el TPV es **red primero**: una comanda o un precio viejos hacen daño.
//   · las piezas del cliente son **caché primero y refresco por detrás**
//     (stale-while-revalidate): la app abre al instante y se actualiza sola para la próxima vez.
//     Como el HTML pide los recursos con `?v=<sello del despliegue>`, una versión nueva es otra
//     URL: no hay manera de quedarse clavado en la vieja.
//
// Lo que NUNCA se guarda, ni aquí ni allí: nada de `/api`.
const CONCHA_CLIENTE = [
  '/cliente.html',
  '/css/estilo.css',
  '/js/comun.js',
  '/js/cuenta.js',
  '/js/cliente_mesa.js',
  '/js/cliente.js',
  '/js/cliente_reservas.js',
  '/js/app_cliente.js',
  '/app.webmanifest',
  '/img/icono-192.png',
  '/img/icono-512.png',
];

self.addEventListener('install', e => {
  // `addAll` falla entero si una sola pieza falla, y eso dejaría la app sin caché por un icono:
  // se piden una a una y lo que no esté, no está.
  e.waitUntil(caches.open(VERSION).then(async c => {
    for (const pieza of [...CONCHA, ...CONCHA_CLIENTE]) {
      try { await c.add(pieza); } catch {}
    }
  }).then(() => self.skipWaiting()));
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

function esDelCliente(url) {
  return url.origin === self.location.origin
    && (CONCHA_CLIENTE.includes(url.pathname) || url.pathname.startsWith('/img/'));
}

/** Caché primero y refresco por detrás: se responde con lo guardado y se pide lo nuevo para la
    próxima visita. Si no hay nada guardado, se espera a la red como siempre. */
async function deLaCacheYRefrescar(peticion) {
  const cache = await caches.open(VERSION);
  // Coincidencia EXACTA, con su `?v=<sello>`: si se busca ignorando la query, una versión nueva
  // se responde con la copia vieja y la pantalla se queda con el CSS o el JavaScript de antes.
  // Pasó con el estilo de la pantalla de mesa: el QR se pintaba sin su fondo blanco.
  const guardada = await cache.match(peticion);
  const dePaso = fetch(peticion).then(r => {
    if (r.ok) cache.put(peticion, r.clone());
    return r;
  }).catch(() => null);
  return guardada || (await dePaso) || Response.error();
}

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.pathname.startsWith('/api')) return;

  const navegacion = e.request.mode === 'navigate';
  // La app del cliente: sus piezas salen de la caché al instante. La página, de la red cuando
  // la hay (para que un cambio de carta se vea), y de la copia cuando no.
  if (esDelCliente(url) && !navegacion) {
    e.respondWith(deLaCacheYRefrescar(e.request));
    return;
  }
  const esCliente = navegacion && url.pathname === '/cliente.html';
  const esTpv = navegacion && url.pathname === '/tpv.html';
  if (!esCliente && !esTpv && !esDelTpv(url)) return;              // el resto, sin tocar

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
