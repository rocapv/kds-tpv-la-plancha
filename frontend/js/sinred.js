// ── Modo sin red del TPV ──────────────────────────────────────────────────────────────────
//
// Si se cae el wifi, el camarero tiene que poder seguir tomando nota. Aquí se apunta lo que
// hace mientras no hay servidor y se reenvía en cuanto vuelve.
//
// Lo que SÍ se puede hacer sin red: abrir mesa, añadir y quitar líneas, poner comensales y
// mandar la comanda a cocina (que saldrá cuando vuelva la red, no antes).
// Lo que NO: cobrar, facturar, arquear ni mirar informes. El dinero lleva numeración
// correlativa y sello del servidor; una factura inventada en una tableta desconectada es un
// problema legal, no una comodidad. Sin red se toma nota, y se cobra al volver.
//
// Cómo no se duplica nada: cada acción lleva una clave (uuid) que se inventa UNA vez, cuando
// el camarero pulsa. Si al reenviar resulta que aquella petición sí había llegado, el servidor
// devuelve la respuesta que ya dio (ver `16_idempotencia.sql`). Reenviar es gratis.
//
// Los identificadores locales son NEGATIVOS (-1, -2…) para que no se confundan nunca con los
// del servidor, y al sincronizar se traducen por los de verdad.

const sinRed = (() => {
  const BD = 'kds-sinred';
  let db = null;
  const estado = { cola: [], pedidos: {}, cache: {}, mapa: {}, siguiente: -1 };
  let hayRed = navigator.onLine;
  let sincronizando = false;
  let incidencias = [];

  // ── Almacén: IndexedDB, que aguanta recargas y cierres del navegador ──
  function abrir() {
    return new Promise((ok, mal) => {
      const p = indexedDB.open(BD, 1);
      p.onupgradeneeded = () => {
        const d = p.result;
        if (!d.objectStoreNames.contains('cache')) d.createObjectStore('cache');
        if (!d.objectStoreNames.contains('cola')) d.createObjectStore('cola', { keyPath: 'n' });
        if (!d.objectStoreNames.contains('pedidos')) d.createObjectStore('pedidos', { keyPath: 'id' });
      };
      p.onsuccess = () => ok(p.result);
      p.onerror = () => mal(p.error);
    });
  }

  const tx = (almacen, modo) => db.transaction(almacen, modo).objectStore(almacen);
  const pedir = req => new Promise((ok, mal) => { req.onsuccess = () => ok(req.result); req.onerror = () => mal(req.error); });

  async function guardar(almacen, valor, clave) {
    if (!db) return;
    try { await pedir(tx(almacen, 'readwrite').put(valor, clave)); } catch (e) { console.warn('sinred: no se pudo guardar', e); }
  }
  async function quitar(almacen, clave) {
    if (!db) return;
    try { await pedir(tx(almacen, 'readwrite').delete(clave)); } catch {}
  }

  const listo = (async () => {
    try {
      db = await abrir();
      estado.cola = (await pedir(tx('cola', 'readonly').getAll())).sort((a, b) => a.n - b.n);
      (await pedir(tx('pedidos', 'readonly').getAll())).forEach(p => estado.pedidos[p.id] = p);
      for (const k of ['catalogo', 'mesas', 'pedidos_abiertos', 'sala', 'yo', 'mapa', 'siguiente']) {
        const v = await pedir(tx('cache', 'readonly').get(k));
        if (v === undefined) continue;
        if (k === 'mapa') estado.mapa = v;
        else if (k === 'siguiente') estado.siguiente = v;
        else estado.cache[k] = v;
      }
    } catch (e) {
      // Sin IndexedDB (modo privado, cuota llena) el TPV sigue funcionando CON red; lo único
      // que se pierde es la red de seguridad. Mejor decirlo que fingir que está protegido.
      console.warn('sinred: sin almacén local', e);
      avisarSinAlmacen();
    }
  })();

  const uuid = () => (crypto.randomUUID ? crypto.randomUUID()
    : 'k-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10));
  const nuevoId = () => { const id = estado.siguiente--; guardar('cache', estado.siguiente, 'siguiente'); return id; };

  // ── Estado de la conexión ──
  function marcarRed(valor) {
    if (hayRed === valor) return;
    hayRed = valor;
    pintarBarra();
    if (valor) sincronizar();
  }
  const pendientes = () => estado.cola.length;

  window.addEventListener('online', () => sondear());
  window.addEventListener('offline', () => marcarRed(false));
  // El navegador miente: `online` solo dice que hay tarjeta de red, no que el servidor conteste.
  // Mientras estemos caídos se le pregunta al servidor cada pocos segundos.
  setInterval(() => { if (!hayRed || pendientes()) sondear(); }, 8000);

  async function sondear() {
    try {
      const r = await fetch('/api/salud', { cache: 'no-store' });
      marcarRed(r.ok);
      if (r.ok && pendientes() && !sincronizando) sincronizar();
    } catch { marcarRed(false); }
  }

  // ── Barra de aviso ──
  function barra() {
    let b = document.querySelector('#sinred');
    if (!b) {
      b = document.createElement('div');
      b.id = 'sinred';
      b.hidden = true;
      document.body.appendChild(b);
    }
    return b;
  }
  function pintarBarra(texto = null, clase = '') {
    const b = barra();
    if (texto !== null) { b.className = clase; b.textContent = texto; b.hidden = false; return; }
    const n = pendientes();
    if (!hayRed) {
      b.className = 'caido';
      b.textContent = `Sin conexión con el servidor · se está apuntando aquí${n ? ` (${n} ${n === 1 ? 'acción' : 'acciones'} por enviar)` : ''} · no se puede cobrar`;
      b.hidden = false;
    } else if (n) {
      b.className = 'enviando';
      b.textContent = `Enviando lo apuntado sin red… (${n})`;
      b.hidden = false;
    } else {
      b.hidden = true;
    }
  }
  function avisarSinAlmacen() {
    pintarBarra('Este navegador no guarda nada en local: si cae la red se pierde lo que no esté enviado', 'caido');
  }

  // ── Copia de lo que hace falta para trabajar a ciegas ──
  const esPedido = d => d && typeof d === 'object' && Array.isArray(d.lineas) && 'total_cent' in d;
  function recordar(ruta, datos) {
    const enCache = { '/catalogo': 'catalogo', '/mesas': 'mesas', '/pedidos': 'pedidos_abiertos', '/sala': 'sala', '/yo': 'yo' }[ruta];
    if (enCache) { estado.cache[enCache] = datos; guardar('cache', datos, enCache); }
    if (esPedido(datos) && datos.id > 0) {
      estado.pedidos[datos.id] = datos;
      guardar('pedidos', datos);
    }
  }

  // ── Modelo local: las mismas operaciones, hechas en la tableta ──
  function producto(id) {
    for (const c of estado.cache.catalogo || []) for (const p of c.productos) if (p.id === id) return p;
  }
  function recalcular(p) {
    p.total_cent = p.lineas.filter(l => l.estado !== 'anulada').reduce((s, l) => s + l.cantidad * l.precio_cent, 0);
    p.pagado_cent = (p.pagos || []).reduce((s, g) => s + g.importe_cent, 0);
    p.pendiente_cent = p.total_cent - p.pagado_cent;
    return p;
  }
  function guardarPedido(p) { estado.pedidos[p.id] = p; guardar('pedidos', p); return recalcular(p); }

  function encolar(op) {
    op.n = (estado.cola.length ? estado.cola[estado.cola.length - 1].n : 0) + 1;
    op.clave = op.clave || uuid();
    estado.cola.push(op);
    guardar('cola', op);
    pintarBarra();
    return op;
  }
  function desencolar(op) {
    estado.cola = estado.cola.filter(o => o.n !== op.n);
    quitar('cola', op.n);
  }

  const sinServidor = ruta => {
    const e = new Error('Sin conexión: se puede tomar nota y mandar a cocina, pero no ' +
      (/pagos|cobrar|documento|factura/.test(ruta) ? 'cobrar. El cobro se hace al volver la red.'
        : 'hacer eso. Habrá que esperar a que vuelva.'));
    e.estado = 503;
    return e;
  };

  function local(ruta, opciones) {
    const metodo = (opciones.method || 'GET').toUpperCase();
    const cuerpo = opciones.body || null;

    if (metodo === 'GET') {
      if (ruta === '/yo' && estado.cache.yo) return estado.cache.yo;
      if (ruta === '/catalogo' && estado.cache.catalogo) return estado.cache.catalogo;
      if (ruta === '/solicitudes') return [];          // sin red no llega ninguna del móvil
      if (ruta === '/mesas') return mesasLocales();
      if (ruta === '/pedidos') return abiertosLocales();
      if (ruta === '/sala') return salaLocal();
      const m = ruta.match(/^\/pedidos\/(-?\d+)$/);
      if (m && estado.pedidos[+m[1]]) return recalcular(estado.pedidos[+m[1]]);
      throw sinServidor(ruta);
    }

    // Abrir mesa o pedido para llevar
    if (metodo === 'POST' && ruta === '/pedidos') {
      const yo = estado.cache.yo || {};
      if (cuerpo.tipo === 'sala') {
        const ya = Object.values(estado.pedidos).find(p => p.estado === 'abierto' && p.mesa_id === cuerpo.mesa_id);
        if (ya) return recalcular(ya);               // misma regla que el servidor: no se duplica
      }
      const mesa = (estado.cache.mesas || []).find(m => m.id === cuerpo.mesa_id);
      const p = {
        id: nuevoId(), tipo: cuerpo.tipo, mesa_id: cuerpo.mesa_id || null, mesa: mesa?.nombre || null,
        cliente: cuerpo.cliente || null, comensales: cuerpo.comensales || null, estado: 'abierto',
        camarero: yo.nombre || 'sin identificar', empleado_id: yo.id || null,
        abierto_en: new Date().toISOString(), lineas: [], pagos: [], sin_red: true,
      };
      encolar({ metodo: 'POST', ruta: '/pedidos', cuerpo, crea: 'pedido', localId: p.id });
      return guardarPedido(p);
    }

    let m = ruta.match(/^\/pedidos\/(-?\d+)\/lineas$/);
    if (metodo === 'POST' && m) {
      const p = exigirLocal(+m[1]);
      const pr = producto(cuerpo.producto_id);
      if (!pr) throw Object.assign(new Error('Ese producto no está en la carta guardada'), { estado: 404 });
      if (!pr.disponible) throw Object.assign(new Error(`${pr.nombre} está agotado`), { estado: 409 });
      const linea = {
        id: nuevoId(), pedido_id: p.id, producto_id: pr.id, cantidad: cuerpo.cantidad || 1,
        precio_cent: pr.precio_cent, notas: cuerpo.notas || null, estacion: pr.estacion,
        estado: 'pendiente', producto: pr.nombre, alergenos: pr.alergenos || null, pago_id: null,
      };
      p.lineas.push(linea);
      encolar({ metodo: 'POST', ruta: `/pedidos/${p.id}/lineas`, cuerpo, crea: 'linea', localId: linea.id });
      return guardarPedido(p);
    }

    m = ruta.match(/^\/pedidos\/(-?\d+)\/lineas\/(-?\d+)$/);
    if (metodo === 'DELETE' && m) {
      const p = exigirLocal(+m[1]);
      const lid = +m[2];
      const linea = p.lineas.find(l => l.id === lid);
      if (!linea) throw Object.assign(new Error('Línea no encontrada'), { estado: 404 });
      // Si la línea se añadió también sin red y su alta sigue en la cola, el servidor no sabe
      // nada de ella: se quita el alta y no se manda nada. Es como no haberla pulsado.
      const alta = estado.cola.find(o => o.crea === 'linea' && o.localId === lid);
      if (alta) desencolar(alta);
      else encolar({ metodo: 'DELETE', ruta: `/pedidos/${p.id}/lineas/${lid}` });
      if (linea.estado === 'pendiente') p.lineas = p.lineas.filter(l => l.id !== lid);
      else linea.estado = 'anulada';
      return guardarPedido(p);
    }

    m = ruta.match(/^\/pedidos\/(-?\d+)\/enviar$/);
    if (metodo === 'POST' && m) {
      const p = exigirLocal(+m[1]);
      let n = 0;
      p.lineas.forEach(l => { if (l.estado === 'pendiente') { l.estado = 'enviada'; l.enviada_en = new Date().toISOString(); n++; } });
      if (n) encolar({ metodo: 'POST', ruta: `/pedidos/${p.id}/enviar` });
      return guardarPedido(p);
    }

    m = ruta.match(/^\/pedidos\/(-?\d+)\/comensales$/);
    if (metodo === 'PATCH' && m) {
      const p = exigirLocal(+m[1]);
      p.comensales = cuerpo.comensales;
      encolar({ metodo: 'PATCH', ruta: `/pedidos/${p.id}/comensales`, cuerpo });
      return guardarPedido(p);
    }

    m = ruta.match(/^\/pedidos\/(-?\d+)\/anular$/);
    if (metodo === 'POST' && m) {
      const p = exigirLocal(+m[1]);
      const suyas = estado.cola.filter(o => (o.crea === 'pedido' && o.localId === p.id)
        || o.ruta.startsWith(`/pedidos/${p.id}/`));
      // Un pedido que nació sin red y muere sin red no llega a existir para el servidor.
      if (p.id < 0 && suyas.some(o => o.crea === 'pedido')) suyas.forEach(desencolar);
      else encolar({ metodo: 'POST', ruta: `/pedidos/${p.id}/anular` });
      p.estado = 'anulado';
      guardarPedido(p);
      return { ok: true };
    }

    throw sinServidor(ruta);
  }

  function exigirLocal(id) {
    const p = estado.pedidos[id];
    if (!p) throw Object.assign(new Error('Ese pedido no está guardado en esta tableta'), { estado: 404 });
    if (p.estado !== 'abierto') throw Object.assign(new Error(`El pedido está ${p.estado}`), { estado: 409 });
    return p;
  }

  function mesasLocales() {
    const mesas = (estado.cache.mesas || []).map(m => ({ ...m, pedido_id: null, total_cent: 0, abierto_en: null }));
    for (const p of Object.values(estado.pedidos)) {
      if (p.estado !== 'abierto' || !p.mesa_id) continue;
      const m = mesas.find(x => x.id === p.mesa_id);
      if (m) Object.assign(m, { pedido_id: p.id, total_cent: recalcular(p).total_cent, abierto_en: p.abierto_en });
    }
    return mesas;
  }
  function abiertosLocales() {
    return Object.values(estado.pedidos).filter(p => p.estado === 'abierto')
      .map(p => ({ id: p.id, tipo: p.tipo, cliente: p.cliente, abierto_en: p.abierto_en, mesa: p.mesa, total_cent: recalcular(p).total_cent }));
  }
  function salaLocal() {
    // Sin servidor no hay relojes de espera fiables: se dice lo que se sabe (mesa abierta y
    // comensales) y nada más. Inventar «lleva 20 minutos esperando» sería peor que callar.
    return {
      mesas: Object.values(estado.pedidos).filter(p => p.estado === 'abierto' && p.mesa_id)
        .map(p => ({ id: p.mesa_id, estado: 'ocupada', comensales: p.comensales })),
      sin_red: true,
    };
  }

  // ── Reenvío al volver la red ──
  function traducir(ruta) {
    return ruta.replace(/\/(-\d+)/g, (_, id) => {
      const real = estado.mapa[id];
      if (!real) throw new Error('falta-mapa');
      return '/' + real;
    });
  }

  function apuntarMapa(local, real) {
    estado.mapa[local] = real;
    guardar('cache', estado.mapa, 'mapa');
  }

  async function sincronizar() {
    await listo;
    if (sincronizando || !estado.cola.length) { pintarBarra(); return; }
    sincronizando = true;
    incidencias = [];
    let enviadas = 0;
    try {
      while (estado.cola.length) {
        const op = estado.cola[0];
        let ruta;
        try { ruta = traducir(op.ruta); } catch {
          // Su pedido no llegó a crearse (el alta falló): lo que viene detrás no tiene destino.
          incidencias.push(`${op.ruta}: se perdió porque su pedido no pudo crearse`);
          desencolar(op);
          continue;
        }
        try {
          const datos = await apiRed(ruta, { method: op.metodo, body: op.cuerpo, clave: op.clave });
          if (op.crea === 'pedido' && datos?.id) apuntarMapa(op.localId, datos.id);
          if (op.crea === 'linea' && Array.isArray(datos?.lineas) && datos.lineas.length) {
            apuntarMapa(op.localId, datos.lineas[datos.lineas.length - 1].id);
          }
          if (esPedido(datos)) recordar('', datos);
          desencolar(op);
          enviadas++;
          pintarBarra();
        } catch (e) {
          if (e.red) { marcarRed(false); break; }       // se ha vuelto a caer: se sigue luego
          // El servidor la rechaza (mesa ya cobrada, producto agotado, permiso): no se reintenta
          // eternamente. Se descarta y se DICE, que es lo que permite arreglarlo a mano.
          incidencias.push(`${op.metodo} ${op.ruta}: ${e.message}`);
          desencolar(op);
        }
      }
    } finally {
      sincronizando = false;
    }
    if (!estado.cola.length) await terminarSincronizacion(enviadas);
    else pintarBarra();
  }

  async function terminarSincronizacion(enviadas) {
    // Fuera los pedidos locales: a partir de aquí manda el servidor, que es quien tiene los
    // identificadores buenos y lo que hayan tocado otras pantallas mientras tanto.
    for (const id of Object.keys(estado.pedidos)) if (+id < 0) await quitar('pedidos', +id);
    estado.pedidos = Object.fromEntries(Object.entries(estado.pedidos).filter(([id]) => +id > 0));
    estado.mapa = {};
    await guardar('cache', {}, 'mapa');
    if (enviadas || incidencias.length) {
      const resumen = `${enviadas} ${enviadas === 1 ? 'acción enviada' : 'acciones enviadas'} al volver la red`
        + (incidencias.length ? ` · ${incidencias.length} sin poder enviarse` : '');
      pintarBarra(resumen + (incidencias.length ? ' · ' + incidencias.join(' | ') : ''),
                  incidencias.length ? 'problema' : 'bien');
      if (!incidencias.length) setTimeout(() => pintarBarra(), 6000);
      if (typeof aviso === 'function') aviso(resumen, incidencias.length ? 'error' : 'ok');
    } else pintarBarra();
    window.dispatchEvent(new CustomEvent('sinred-sincronizado', { detail: { enviadas, incidencias } }));
  }

  // ── Puerta de entrada: lo que llama `api()` de comun.js ──
  async function llamar(ruta, opciones = {}) {
    await listo;
    const metodo = (opciones.method || 'GET').toUpperCase();
    const tocaLocal = /\/-\d+(\/|$)/.test(ruta);          // un pedido que solo existe aquí
    if (!hayRed || tocaLocal) {
      if (tocaLocal && hayRed && !sincronizando) sincronizar();
      return local(ruta, opciones);
    }
    // Con red, todo va al servidor; las escrituras llevan clave para que un reintento no
    // duplique nada aunque la respuesta se pierda por el camino.
    const conClave = metodo === 'GET' || opciones.clave ? opciones : { ...opciones, clave: uuid() };
    try {
      const datos = await apiRed(ruta, conClave);
      recordar(ruta, datos);
      return datos;
    } catch (e) {
      if (!e.red) throw e;                                // error del servidor: se propaga tal cual
      marcarRed(false);
      return local(ruta, opciones);
    }
  }

  // Para que la pantalla se pueda ABRIR sin red (recarga, tableta bloqueada, navegador cerrado)
  // hace falta una copia del HTML y del JS: eso es `sw.js`. Sin él, sinred.js solo aguanta
  // mientras la página siga viva. Si el navegador no lo admite, el resto sigue funcionando.
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js')
      .catch(e => console.warn('sinred: sin copia de la pantalla', e)));
  }

  document.addEventListener('DOMContentLoaded', () => { pintarBarra(); listo.then(() => pendientes() && sondear()); });

  return { llamar, sincronizar, pendientes, hayRed: () => hayRed, estado };
})();
