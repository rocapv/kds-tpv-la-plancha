// Estar sentado en una mesa: canjear el QR, quedarse unido y poder irse.
//
// El token de la visita se guarda en el móvil y lo manda `comun.js` en cada petición
// (`X-Visita`). Muere cuando el camarero cierra la mesa, así que nadie sigue «en la mesa 3»
// desde su casa al día siguiente.
const LLAVE_VISITA = 'kds_mi_mesa';

let visita = null;
try { visita = JSON.parse(localStorage.getItem(LLAVE_VISITA) || 'null'); } catch { visita = null; }

function tokenVisita() { return visita?.token || null; }

function guardarVisita(v) {
  visita = v;
  try { localStorage.setItem(LLAVE_VISITA, JSON.stringify(v)); } catch {}
  pintarMesa();
}
function olvidarVisita() {
  visita = null;
  try { localStorage.removeItem(LLAVE_VISITA); } catch {}
  pintarMesa();
}

function pintarMesa() {
  const caja = $('#mi-mesa');
  if (!caja) return;
  if (!visita) { caja.hidden = true; return; }
  caja.hidden = false;
  caja.innerHTML = `
    <div class="cab"><b>Estás en la mesa ${esc(visita.mesa)}</b>
      <button id="mm-salir" class="sutil">Salir de la mesa</button></div>
    <p class="tenue">Lo que pidas va a esta mesa.
      ${visita.comensales > 1 ? `Sois ${visita.comensales} con el móvil en la mesa.` : ''}
      Para que se una alguien más, que teclee <b>${esc(visita.codigo_union || '')}</b>
      o lea el código de la pantalla.</p>`;
  $('#mm-salir').onclick = async () => {
    try { await api('/publico/visita/salir', { method: 'POST' }); } catch {}
    olvidarVisita();
    aviso('Has salido de la mesa', 'ok');
  };
}

/** Canjea el código del QR (o el de unirse, que es más corto). */
async function entrarEnMesa(codigo) {
  const ruta = codigo.length > 8 ? '/publico/mesa/canjear' : '/publico/mesa/unirse';
  try {
    const v = await api(ruta, { method: 'POST', body: { codigo } });
    guardarVisita(v);
    aviso(`Mesa ${v.mesa}: ya puedes pedir`, 'ok');
    return true;
  } catch (e) {
    aviso(e.message, 'error');
    return false;
  }
}

/** Comprueba que la mesa sigue abierta; si el camarero la cerró, se olvida sin dar la lata. */
async function comprobarMesa() {
  if (!visita) return;
  try {
    guardarVisita({ ...visita, ...(await api('/publico/visita')) });
  } catch (e) {
    if (e.estado === 401) olvidarVisita();
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const codigo = new URLSearchParams(location.search).get('m');
  if (codigo) {
    await entrarEnMesa(codigo.trim().toUpperCase());
    history.replaceState(null, '', '/cliente.html');   // que no se quede el código en la barra
  } else {
    comprobarMesa();
  }
  const b = $('#b-unirme');
  if (b) b.onclick = async () => {
    const c = prompt('Teclea el código que hay en la pantalla de tu mesa');
    if (c) await entrarEnMesa(c.trim().toUpperCase());
  };
});
