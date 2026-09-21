// Utilidades compartidas por TPV, KDS e informe
const euro = c => (c / 100).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' });
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));

async function api(ruta, opciones = {}) {
  const cabeceras = { 'Content-Type': 'application/json' };
  const t = typeof tokenActual === 'function' ? tokenActual() : null;
  if (t) cabeceras.Authorization = 'Bearer ' + t;
  const r = await fetch('/api' + ruta, {
    headers: cabeceras,
    ...opciones,
    body: opciones.body ? JSON.stringify(opciones.body) : undefined,
  });
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) {
    const error = new Error(datos.detail?.[0]?.msg || datos.detail || r.statusText);
    error.estado = r.status;
    if (r.status === 401 && typeof borrarSesion === 'function') borrarSesion();
    throw error;
  }
  return datos;
}

// WebSocket con reconexión automática; muestra el estado en #conexion
function conectarWS(alRecibir) {
  const marca = $('#conexion');
  const abrir = () => {
    const t = typeof tokenActual === 'function' ? tokenActual() : null;
    const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws' + (t ? '?token=' + encodeURIComponent(t) : ''));
    ws.onopen = () => { marca && (marca.className = 'conexion ok', marca.title = 'Conectado'); alRecibir({ tipo: 'reconectado' }); };
    ws.onmessage = e => alRecibir(JSON.parse(e.data));
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
