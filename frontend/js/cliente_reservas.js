// Reservar mesa desde el móvil, y seguir la reserva ya hecha.
// Va aparte de cliente.js a propósito: la carta funciona igual aunque las reservas estén
// cerradas, y así una cosa no puede romper la otra.
const LLAVE_RESERVA = 'kds_mi_reserva';

const zonaTexto = { sala: 'Comedor presurizado', terraza: 'Mirador de la fractura', barra: 'Atraque' };
const horaCorta = f => new Date(f).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
const diaLargo = f => new Date(f).toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' });

function miReserva() {
  try { return JSON.parse(localStorage.getItem(LLAVE_RESERVA) || 'null'); } catch { return null; }
}
function guardarReserva(r) {
  try { localStorage.setItem(LLAVE_RESERVA, JSON.stringify(r)); } catch {}
}
function olvidarReserva() {
  try { localStorage.removeItem(LLAVE_RESERVA); } catch {}
}

// ── Huecos ──
async function pintarHuecos() {
  const fecha = $('#r-fecha').value;
  const pax = Number($('#r-pax').value) || 2;
  const zona = $('#r-zona').value;
  const caja = $('#r-horas');
  caja.innerHTML = '<p class="tenue">Mirando…</p>';
  try {
    const d = await api(`/publico/reservas/huecos?fecha=${fecha}&comensales=${pax}`
                        + (zona ? `&zona=${zona}` : ''));
    if (!d.horas.length) {
      caja.innerHTML = `<p class="tenue">No queda hueco ese día para ${pax}.
        Horario: ${esc(d.horario)}. Se reserva con ${d.antelacion_min} minutos de antelación.</p>`;
      return;
    }
    caja.innerHTML = d.horas.map(h =>
      `<button class="hueco" data-hora="${h.hora}">${horaCorta(h.hora)}
         <small>${esc(zonaTexto[h.zona] || h.zona)}</small></button>`).join('');
    caja.querySelectorAll('.hueco').forEach(b => b.onclick = () => {
      caja.querySelectorAll('.hueco').forEach(o => o.classList.remove('elegida'));
      b.classList.add('elegida');
      $('#r-hora').value = b.dataset.hora;
    });
  } catch (e) {
    caja.innerHTML = `<p class="tenue">${esc(e.message)}</p>`;
  }
}

// ── Reservar ──
async function reservar() {
  if (!$('#r-hora').value) return aviso('Elige una hora', 'error');
  if (!$('#r-nombre').value.trim()) return aviso('Hace falta un nombre', 'error');
  const adelantar = $('#r-adelantar').checked && typeof cesta !== 'undefined' && cesta.length;
  try {
    const r = await api('/publico/reservas', { method: 'POST', body: {
      hora: $('#r-hora').value,
      comensales: Number($('#r-pax').value) || 2,
      nombre: $('#r-nombre').value.trim(),
      telefono: $('#r-telefono').value.trim() || null,
      zona: $('#r-zona').value || null,
      nota: $('#r-nota').value.trim() || null,
      lineas: adelantar ? cesta.map(l => ({ producto_id: l.producto_id, cantidad: l.cantidad })) : [],
    }});
    guardarReserva({ token: r.token, hora: r.hora });
    if (adelantar) {                       // lo pedido ya está en la reserva: la cesta se vacía
      cesta.length = 0;
      guardarCesta();
      pintarCesta();
    }
    $('#d-reservar').close();
    verMiReserva();
    aviso('Mesa reservada', 'ok');
  } catch (e) { aviso(e.message, 'error'); }
}

// ── La reserva que ya tengo ──
async function verMiReserva() {
  const guardada = miReserva();
  const caja = $('#mi-reserva');
  if (!guardada) { caja.hidden = true; return; }
  let r;
  try {
    r = await api('/publico/reservas/' + guardada.token);
  } catch {
    olvidarReserva(); caja.hidden = true; return;     // ya no existe: se deja de enseñar
  }
  if (['anulada', 'no_show'].includes(r.estado)) { olvidarReserva(); caja.hidden = true; return; }
  caja.hidden = false;
  const adelantado = r.lineas.length
    ? `<p>Dejaste pedido: ${r.lineas.map(l => `${l.cantidad}× ${esc(l.nombre)}`).join(', ')}
         <b>${euro(r.total_cent)}</b>.
         ${r.soltada_en ? 'Ya se está preparando.' : 'Se empieza a preparar poco antes de tu hora.'}</p>`
    : '';
  caja.innerHTML = `
    <div class="cab"><b>Tu mesa está reservada</b>
      <button id="mr-anular" class="sutil">Anular</button></div>
    <p><b>${diaLargo(r.hora)} a las ${horaCorta(r.hora)}</b> · ${r.comensales} personas
       ${r.mesa ? `· mesa ${esc(r.mesa)}` : ''}</p>
    ${adelantado}`;
  $('#mr-anular').onclick = async () => {
    if (!confirm('¿Anular tu reserva?')) return;
    try {
      await api(`/publico/reservas/${guardada.token}/anular`, { method: 'POST' });
      olvidarReserva();
      caja.hidden = true;
      aviso('Reserva anulada', 'ok');
    } catch (e) { aviso(e.message, 'error'); }
  };
}

// ── Enganches ──
$('#b-reservar').onclick = () => {
  const hoy = new Date();
  $('#r-fecha').value = hoy.toISOString().slice(0, 10);
  $('#r-hora').value = '';
  const hayCesta = typeof cesta !== 'undefined' && cesta.length;
  $('#r-con-cesta').hidden = !hayCesta;
  $('#r-adelantar').checked = Boolean(hayCesta);
  if (hayCesta) $('#r-cesta-texto').textContent =
    `${cesta.reduce((n, l) => n + l.cantidad, 0)} productos · ${euro(totalCesta())}`;
  $('#d-reservar').showModal();
  pintarHuecos();
};
['#r-fecha', '#r-pax', '#r-zona'].forEach(s => $(s).onchange = pintarHuecos);
$('#r-cancelar').onclick = () => $('#d-reservar').close();
$('#r-ok').onclick = reservar;

verMiReserva();
