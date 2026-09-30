// Agenda de reservas de la sala: ver el día, coger una por teléfono y resolverlas.
// Lo que decide es el servidor; aquí solo se pinta y se pulsa.
// Dos maneras de mirar lo mismo: la lista («¿qué toca ahora?») y el planning, en planning.js
// («¿dónde meto a estos seis?»). Las dos beben de la misma carga y usan las mismas acciones.
// La fecha de HOY en hora local. `toISOString()` da la de Greenwich: entre las 00:00 y las 02:00
// de aquí la agenda abría el día de ayer.
const hoyLocal = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
                         return d.toISOString().slice(0, 10); };
let dia = hoyLocal();
let DATOS = null;         // lo último que dijo /api/reservas: {fecha, config, reservas}
let vista = 'lista';

const HORA = f => new Date(f).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
const ESTADOS = {
  pendiente: ['por confirmar', 'aviso'],
  confirmada: ['confirmada', 'ok'],
  sentada: ['sentada', 'ok'],
  no_show: ['no vino', 'mal'],
  anulada: ['anulada', 'mal'],
};

function tarjeta(r) {
  const [texto, color] = ESTADOS[r.estado] || [r.estado, ''];
  const lineas = r.lineas.length
    ? `<ul class="adelantado">${r.lineas.map(l =>
        `<li>${l.cantidad}× ${esc(l.nombre)}${l.notas ? ` <em class="tenue">${esc(l.notas)}</em>` : ''}</li>`).join('')}</ul>
       <p class="tenue">${r.soltada_en ? `En cocina desde las ${HORA(r.soltada_en)}` : 'Entra en cocina sola antes de la hora'}
         · ${euro(r.total_cent)}</p>`
    : '<p class="tenue">Sin pedido adelantado</p>';
  const vivos = !['anulada', 'no_show', 'sentada'].includes(r.estado);
  return `<article class="reserva ${r.estado}" data-id="${r.id}">
    <div class="cuando"><b>${HORA(r.hora)}</b><small>${esc(r.mesa || 'sin mesa')}</small></div>
    <div class="quien">
      <b>${esc(r.nombre)}</b> <span class="tenue">· ${r.comensales} pax</span>
      <span class="marca ${color}">${texto}</span>
      ${r.telefono ? `<div class="tenue">${esc(r.telefono)}</div>` : ''}
      ${r.nota ? `<div class="nota">${esc(r.nota)}</div>` : ''}
      ${lineas}
    </div>
    <div class="acciones">
      ${r.estado === 'pendiente' ? '<button data-accion="confirmar">Confirmar</button>' : ''}
      ${vivos ? '<button data-accion="sentar" class="primario">Sentar</button>' : ''}
      ${vivos && r.lineas.length && !r.soltada_en ? '<button data-accion="soltar">A cocina ya</button>' : ''}
      ${vivos ? '<button data-accion="no_show" class="mal">No vino</button>' : ''}
      ${vivos ? '<button data-accion="anular" class="mal">Anular</button>' : ''}
      ${vivos ? '<button data-accion="mesa">Cambiar mesa</button>' : ''}
    </div>
  </article>`;
}

// Los botones de una tarjeta, estén en la lista o en el diálogo del planning.
function enlazarAcciones(raiz, despues = () => {}) {
  raiz.querySelectorAll('[data-accion]').forEach(b => b.onclick = async () => {
    const id = b.closest('.reserva').dataset.id;
    const accion = b.dataset.accion;
    try {
      if (accion === 'mesa') { await cambiarMesa(id); despues(); return cargar(); }
      if (accion === 'anular' && !confirm('¿Anular la reserva?')) return;
      await api(`/reservas/${id}/${accion}`, { method: 'POST' });
      aviso(accion === 'sentar' ? 'Mesa abierta con la reserva dentro' : 'Hecho', 'ok');
      despues();
    } catch (e) { aviso(e.message, 'error'); }
    cargar();
  });
}

async function cargar() {
  const d = await api('/reservas?fecha=' + dia);
  DATOS = d;
  const vivas = d.reservas.filter(r => !['anulada', 'no_show'].includes(r.estado));
  const pax = vivas.reduce((n, r) => n + r.comensales, 0);
  $('#resumen').textContent = vivas.length
    ? `${vivas.length} reservas · ${pax} comensales`
    : 'sin reservas ese día';
  const reglas = `Antelación mínima ${d.config.antelacion_min} min · `
    + `cada mesa se aparta ${d.config.duracion_min} min · `
    + `el pedido adelantado entra en cocina ${d.config.margen_cocina_min} min antes · `
    + `horario ${d.config.horario}`;
  document.querySelectorAll('.reglas').forEach(p => p.textContent = reglas);
  $('#lista').innerHTML = d.reservas.length
    ? d.reservas.map(tarjeta).join('')
    : '<p class="tenue">Nadie ha reservado para ese día.</p>';
  enlazarAcciones($('#lista'));
  if (vista === 'planning' && typeof pintarPlanning === 'function') await pintarPlanning();
}

async function cambiarMesa(id) {
  const mesas = await api('/mesas');
  const libres = mesas.map(m => `${m.id}: ${m.nombre} (${m.plazas} pax${m.pedido_id ? ', ocupada' : ''})`);
  const elegida = prompt('¿A qué mesa?\n\n' + libres.join('\n'));
  if (!elegida) return;
  try {
    await api(`/reservas/${id}/mesa`, { method: 'PATCH', body: { mesa_id: Number(elegida) } });
    aviso('Cambiada de mesa', 'ok');
  } catch (e) { aviso(e.message, 'error'); }
}

// ── Reserva cogida por teléfono (o desde un hueco del planning, con mesa y hora puestas) ──
const aLocal = f => new Date(f.getTime() - f.getTimezoneOffset() * 60e3).toISOString().slice(0, 16);

function abrirNueva({ hora = null, mesa = null } = {}) {
  $('#n-hora').value = aLocal(hora || new Date(Date.now() + 3600e3));
  $('#n-mesa').value = mesa ? mesa.id : '';
  $('#n-mesa-texto').hidden = !mesa;
  $('#n-mesa-texto').textContent = mesa ? `Mesa ${mesa.nombre} · ${mesa.plazas} plazas` : '';
  $('#n-zona-l').hidden = !!mesa;         // con mesa elegida, la zona ya está dicha
  if (mesa) $('#n-comensales').value = Math.min(Number($('#n-comensales').value) || 2, mesa.plazas);
  $('#d-nueva').showModal();
}
$('#b-nueva').onclick = () => abrirNueva();
$('#f-nueva').onsubmit = async ev => {
  if (ev.submitter?.value !== 'guardar') return;
  ev.preventDefault();
  const mesa = Number($('#n-mesa').value) || null;
  try {
    await api('/reservas', { method: 'POST', body: {
      hora: $('#n-hora').value, comensales: Number($('#n-comensales').value),
      nombre: $('#n-nombre').value.trim(), telefono: $('#n-telefono').value.trim() || null,
      zona: mesa ? null : ($('#n-zona').value || null), nota: $('#n-nota').value.trim() || null,
      mesa_id: mesa,
    }});
    $('#d-nueva').close();
    dia = $('#n-hora').value.slice(0, 10);
    $('#fecha').value = dia;
    aviso('Reserva apuntada', 'ok');
    cargar();
  } catch (e) { aviso(e.message, 'error'); }
};

// ── Pestañas: la elegida se recuerda en este aparato ──
function verVista(cual) {
  vista = cual === 'planning' ? 'planning' : 'lista';
  document.querySelectorAll('.pestanas button').forEach(b => b.classList.toggle('activa', b.dataset.vista === vista));
  $('#v-lista').hidden = vista !== 'lista';
  $('#v-planning').hidden = vista !== 'planning';
  try { localStorage.setItem('kds_reservas_vista', vista); } catch {}
  if (DATOS && vista === 'planning' && typeof pintarPlanning === 'function') pintarPlanning();
}
document.querySelectorAll('.pestanas button').forEach(b => b.onclick = () => verVista(b.dataset.vista));

$('#fecha').value = dia;
$('#fecha').onchange = () => { dia = $('#fecha').value; cargar(); };
$('#b-hoy').onclick = () => { dia = hoyLocal(); $('#fecha').value = dia; cargar(); };
setInterval(() => $('#reloj').textContent = new Date().toLocaleTimeString('es-ES'), 1000);

exigirSesion(['camarero', 'encargado']).then(() => {
  let guardada = null;
  try { guardada = localStorage.getItem('kds_reservas_vista'); } catch {}
  const pedida = new URLSearchParams(location.search).get('vista');
  verVista(pedida || guardada || 'lista');
  conectarWS(ev => { if (['reservas', 'mesas', 'reconectado'].includes(ev.tipo)) cargar(); });
  cargar();
});
