// Utilidades compartidas por TPV, KDS e informe
const euro = c => (c / 100).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' });
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));

// Llamada directa al servidor. `opciones.clave` es la clave de idempotencia: repetir una
// petición con la misma clave NO repite el trabajo, devuelve la respuesta de la primera vez.
// Por eso el TPV sin red puede reenviar sin miedo lo que apuntó mientras estaba caído.
async function apiRed(ruta, opciones = {}) {
  const cabeceras = { 'Content-Type': 'application/json' };
  const t = typeof tokenActual === 'function' ? tokenActual() : null;
  if (t) cabeceras.Authorization = 'Bearer ' + t;
  if (opciones.clave) cabeceras['Idempotency-Key'] = opciones.clave;
  let r;
  try {
    r = await fetch('/api' + ruta, {
      headers: cabeceras,
      ...opciones,
      body: opciones.body ? JSON.stringify(opciones.body) : undefined,
    });
  } catch (fallo) {
    // fetch solo falla así cuando no se ha llegado al servidor: wifi caído, servidor apagado.
    // Se marca para que quien sepa trabajar sin red (el TPV) lo distinga de un error suyo.
    const error = new Error('No hay conexión con el servidor');
    error.red = true;
    error.causa = fallo;
    throw error;
  }
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) {
    const error = new Error(datos.detail?.[0]?.msg || datos.detail || r.statusText);
    error.estado = r.status;
    if (r.status === 401 && typeof borrarSesion === 'function') borrarSesion();
    throw error;
  }
  return datos;
}

// Punto por el que pasan TODAS las pantallas. Si la pantalla ha cargado `sinred.js` (hoy solo
// el TPV), es él quien decide si la petición va al servidor o se apunta para luego.
async function api(ruta, opciones = {}) {
  return typeof sinRed === 'object' ? sinRed.llamar(ruta, opciones) : apiRed(ruta, opciones);
}

// WebSocket con reconexión automática; muestra el estado en #conexion
function conectarWS(alRecibir) {
  const marca = $('#conexion');
  const abrir = () => {
    const t = typeof tokenActual === 'function' ? tokenActual() : null;
    const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws' + (t ? '?token=' + encodeURIComponent(t) : ''));
    ws.onopen = () => { marca && (marca.className = 'conexion ok', marca.title = 'Conectado'); alRecibir({ tipo: 'reconectado' }); };
    ws.onmessage = e => {
      const ev = JSON.parse(e.data);
      // cualquier trozo de pantalla puede escuchar el WS sin pelearse por la única devolución
      window.dispatchEvent(new CustomEvent('evento-ws', { detail: ev }));
      alRecibir(ev);
    };
    ws.onclose = () => { marca && (marca.className = 'conexion ko', marca.title = 'Sin conexión'); setTimeout(abrir, 2000); };
    setInterval(() => ws.readyState === 1 && ws.send('ping'), 25000);
  };
  abrir();
}

function aviso(texto, tipo = 'info') {
  const d = document.createElement('div');
  d.className = 'toast ' + tipo;
  d.textContent = texto;
  document.body.appendChild(d);
  setTimeout(() => d.remove(), 3000);
}

function minutosDesde(fecha, ahora = new Date()) {
  return Math.floor((ahora - new Date(fecha)) / 60000);
}

// Rótulos del decorado: en la base de datos las zonas siguen siendo sala, terraza y
// barra; aquí se les pone el nombre que usa la tripulación de la estación.
const ZONAS = { sala: 'Comedor presurizado', terraza: 'Mirador de la fractura', barra: 'Atraque' };
const zonaNombre = z => ZONAS[z] || z;
