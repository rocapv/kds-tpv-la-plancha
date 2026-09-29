// Agenda de reservas de la sala: ver el día, coger una por teléfono y resolverlas.
// Lo que decide es el servidor; aquí solo se pinta y se pulsa.
let dia = new Date().toISOString().slice(0, 10);

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

async function cargar() {
  const d = await api('/reservas?fecha=' + dia);
  const vivas = d.reservas.filter(r => !['anulada', 'no_show'].includes(r.estado));
  const pax = vivas.reduce((n, r) => n + r.comensales, 0);
  $('#resumen').textContent = vivas.length
    ? `${vivas.length} reservas · ${pax} comensales`
    : 'sin reservas ese día';
  $('#reglas').textContent = `Antelación mínima ${d.config.antelacion_min} min · `
    + `cada mesa se aparta ${d.config.duracion_min} min · `
    + `el pedido adelantado entra en cocina ${d.config.margen_cocina_min} min antes · `
    + `horario ${d.config.horario}`;
  $('#lista').innerHTML = d.reservas.length
    ? d.reservas.map(tarjeta).join('')
    : '<p class="tenue">Nadie ha reservado para ese día.</p>';

  $('#lista').querySelectorAll('[data-accion]').forEach(b => b.onclick = async () => {
    const id = b.closest('.reserva').dataset.id;
    const accion = b.dataset.accion;
    try {
      if (accion === 'mesa') return await cambiarMesa(id);
      if (accion === 'anular' && !confirm('¿Anular la reserva?')) return;
      await api(`/reservas/${id}/${accion}`, { method: 'POST' });
      aviso(accion === 'sentar' ? 'Mesa abierta con la reserva dentro' : 'Hecho', 'ok');
    } catch (e) { aviso(e.message, 'error'); }
    cargar();
  });
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

// ── Reserva cogida por teléfono ──
$('#b-nueva').onclick = () => {
  const dentro_de_una_hora = new Date(Date.now() + 3600e3 - new Date().getTimezoneOffset() * 60e3);
  $('#n-hora').value = dentro_de_una_hora.toISOString().slice(0, 16);
  $('#d-nueva').showModal();
};
$('#f-nueva').onsubmit = async ev => {
  if (ev.submitter?.value !== 'guardar') return;
  ev.preventDefault();
  try {
    await api('/reservas', { method: 'POST', body: {
      hora: $('#n-hora').value, comensales: Number($('#n-comensales').value),
      nombre: $('#n-nombre').value.trim(), telefono: $('#n-telefono').value.trim() || null,
      zona: $('#n-zona').value || null, nota: $('#n-nota').value.trim() || null,
    }});
    $('#d-nueva').close();
    dia = $('#n-hora').value.slice(0, 10);
    $('#fecha').value = dia;
    aviso('Reserva apuntada', 'ok');
    cargar();
  } catch (e) { aviso(e.message, 'error'); }
};

$('#fecha').value = dia;
$('#fecha').onchange = () => { dia = $('#fecha').value; cargar(); };
$('#b-hoy').onclick = () => { dia = new Date().toISOString().slice(0, 10); $('#fecha').value = dia; cargar(); };
setInterval(() => $('#reloj').textContent = new Date().toLocaleTimeString('es-ES'), 1000);

exigirSesion(['camarero', 'encargado']).then(() => {
  conectarWS(ev => { if (['reservas', 'mesas', 'reconectado'].includes(ev.tipo)) cargar(); });
  cargar();
});
