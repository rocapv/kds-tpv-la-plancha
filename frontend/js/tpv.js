// TPV de sala: PIN → mesas → carta → enviar a cocina → cobrar
let empleado = JSON.parse(sessionStorage.getItem('empleado') || 'null');
let catalogo = [], catActiva = null, pedido = null, productoElegido = null, metodoCobro = 'efectivo';
let pin = '';

// ── PIN ──
function pintarTeclado() {
  const t = $('#teclado');
  t.innerHTML = '';
  [1, 2, 3, 4, 5, 6, 7, 8, 9, 'C', 0, '⏎'].forEach(k => {
    const b = document.createElement('button');
    b.textContent = k;
    b.onclick = () => tecla(String(k));
    t.appendChild(b);
  });
}
async function tecla(k) {
  if (k === 'C') pin = '';
  else if (k === '⏎' || pin.length === 3 && k !== '⏎') {
    if (k !== '⏎') pin += k;
    try {
      empleado = await api('/login', { method: 'POST', body: { pin } });
      sessionStorage.setItem('empleado', JSON.stringify(empleado));
      entrar();
    } catch (e) { aviso(e.message, 'error'); }
    pin = '';
  } else pin += k;
  $('#pin-pantalla').textContent = '•'.repeat(pin.length);
}
document.addEventListener('keydown', e => {
  if (!$('#v-pin').hidden && /^[0-9]$/.test(e.key)) tecla(e.key);
});

async function entrar() {
  $('#v-pin').hidden = true;
  $('#v-trabajo').hidden = false;
  $('#empleado').textContent = `${empleado.nombre} (${empleado.rol})`;
  catalogo = await api('/catalogo');
  catActiva = catalogo[0]?.id;
  verMesas();
}
$('#b-salir').onclick = () => { sessionStorage.removeItem('empleado'); location.reload(); };

// ── Mesas ──
async function verMesas() {
  $('#v-mesas').hidden = false;
  $('#v-carta').hidden = true;
  const mesas = await api('/mesas');
  const abiertos = await api('/pedidos');
  const zonas = {};
  mesas.forEach(m => (zonas[m.zona] ??= []).push(m));
  let html = '';
  for (const [zona, lista] of Object.entries(zonas)) {
    html += `<div class="zona"><h3>${esc(zona)}</h3><div class="mesas">` +
      lista.map(m => `<button class="mesa ${m.pedido_id ? 'ocupada' : ''}" data-mesa="${m.id}">
        ${esc(m.nombre)}<small>${m.pedido_id ? euro(m.total_cent || 0) + ' · ' + minutosDesde(m.abierto_en) + ' min' : m.plazas + ' pax'}</small></button>`).join('') +
      `</div></div>`;
  }
  const llevar = abiertos.filter(p => p.tipo === 'llevar');
  if (llevar.length) {
    html += `<div class="zona"><h3>Para llevar</h3><div class="mesas">` +
      llevar.map(p => `<button class="mesa ocupada" data-pedido="${p.id}">#${p.id}<small>${esc(p.cliente || '')} · ${euro(p.total_cent)}</small></button>`).join('') +
      `</div></div>`;
  }
  $('#v-mesas').innerHTML = html;
  $('#v-mesas').querySelectorAll('[data-mesa]').forEach(b => b.onclick = () => abrirMesa(+b.dataset.mesa));
  $('#v-mesas').querySelectorAll('[data-pedido]').forEach(b => b.onclick = async () => { pedido = await api('/pedidos/' + b.dataset.pedido); verCarta(); });
}
$('#b-mesas').onclick = () => { pedido = null; pintarTicket(); verMesas(); };

async function abrirMesa(mesaId) {
  pedido = await api('/pedidos', { method: 'POST', body: { empleado_id: empleado.id, tipo: 'sala', mesa_id: mesaId } });
  verCarta();
}

// Para llevar
$('#b-llevar').onclick = () => { $('#l-nombre').value = ''; $('#d-llevar').showModal(); };
$('#l-cancelar').onclick = () => $('#d-llevar').close();
$('#l-ok').onclick = async () => {
  pedido = await api('/pedidos', { method: 'POST', body: { empleado_id: empleado.id, tipo: 'llevar', cliente: $('#l-nombre').value || 'Cliente' } });
  $('#d-llevar').close();
  verCarta();
};

// ── Carta ──
function verCarta() {
  $('#v-mesas').hidden = true;
  $('#v-carta').hidden = false;
  $('#cats').innerHTML = catalogo.map(c =>
    `<button data-cat="${c.id}" class="${c.id === catActiva ? 'activa' : ''}" style="background:${c.color}">${esc(c.nombre)}</button>`).join('');
  $('#cats').querySelectorAll('button').forEach(b => b.onclick = () => { catActiva = +b.dataset.cat; verCarta(); });
  const cat = catalogo.find(c => c.id === catActiva);
  $('#productos').innerHTML = cat.productos.map(p =>
    `<button class="producto" data-p="${p.id}" style="border-left-color:${cat.color}">${esc(p.nombre)}<span>${euro(p.precio_cent)}</span></button>`).join('');
  $('#productos').querySelectorAll('button').forEach(b => {
    b.onclick = () => anadir(+b.dataset.p);                       // clic = añadir directo
    b.oncontextmenu = e => { e.preventDefault(); pedirNota(+b.dataset.p); }; // clic derecho = con nota
    let t; b.onpointerdown = () => t = setTimeout(() => pedirNota(+b.dataset.p), 600); // pulsación larga en táctil
    b.onpointerup = b.onpointerleave = () => clearTimeout(t);
  });
  pintarTicket();
}

function buscarProducto(id) {
  for (const c of catalogo) for (const p of c.productos) if (p.id === id) return p;
}
function pedirNota(id) {
  productoElegido = id;
  $('#n-titulo').textContent = buscarProducto(id).nombre;
  $('#n-texto').value = '';
  $('#n-cant').value = 1;
  $('#d-nota').showModal();
}
$('#d-nota').querySelectorAll('[data-n]').forEach(b => b.onclick = () => {
  const t = $('#n-texto');
  t.value = t.value ? t.value + ', ' + b.dataset.n : b.dataset.n;
});
$('#n-cancelar').onclick = () => $('#d-nota').close();
$('#n-ok').onclick = async () => {
  await anadir(productoElegido, +$('#n-cant').value || 1, $('#n-texto').value.trim());
  $('#d-nota').close();
};

async function anadir(productoId, cantidad = 1, notas = null) {
  if (!pedido) return;
  try {
    pedido = await api(`/pedidos/${pedido.id}/lineas`, { method: 'POST', body: { producto_id: productoId, cantidad, notas } });
    pintarTicket();
  } catch (e) { aviso(e.message, 'error'); }
}

// ── Ticket ──
function pintarTicket() {
  const hay = !!pedido;
  $('#t-titulo').textContent = !hay ? 'Selecciona una mesa' : pedido.tipo === 'llevar' ? `Llevar #${pedido.id} · ${pedido.cliente || ''}` : `Mesa ${pedido.mesa}`;
  $('#t-sub').textContent = hay ? `Pedido #${pedido.id} · ${pedido.camarero}` : '';
  const lineas = hay ? pedido.lineas : [];
  $('#lineas').innerHTML = lineas.map(l => `
    <div class="linea">
      <b>${l.cantidad}×</b>
      <span>${esc(l.producto)} <span class="estado ${l.estado}">${l.estado}</span></span>
      <span>${euro(l.cantidad * l.precio_cent)}</span>
      ${l.estado === 'anulada' || l.estado === 'servida' ? '<span></span>' : `<button data-borrar="${l.id}" title="Quitar">✕</button>`}
      ${l.notas ? `<span class="nota">${esc(l.notas)}</span>` : ''}
    </div>`).join('') || '<p class="tenue">Sin productos</p>';
  $('#lineas').querySelectorAll('[data-borrar]').forEach(b => b.onclick = async () => {
    pedido = await api(`/pedidos/${pedido.id}/lineas/${b.dataset.borrar}`, { method: 'DELETE' });
    pintarTicket();
  });
  $('#t-total').textContent = euro(hay ? pedido.total_cent : 0);
  const pendientes = lineas.some(l => l.estado === 'pendiente');
  $('#b-enviar').disabled = !pendientes;
  $('#b-cobrar').disabled = !hay || pendientes || pedido.total_cent === 0;
  $('#b-imprimir').disabled = !hay || pedido.total_cent === 0;
  $('#b-anular').disabled = !hay;
}

$('#b-enviar').onclick = async () => {
  pedido = await api(`/pedidos/${pedido.id}/enviar`, { method: 'POST' });
  aviso('Comanda enviada a cocina', 'ok');
  pintarTicket();
};
$('#b-anular').onclick = async () => {
  if (!confirm('¿Anular el pedido completo?')) return;
  await api(`/pedidos/${pedido.id}/anular`, { method: 'POST' });
  pedido = null; pintarTicket(); verMesas();
};

// ── Cobro ──
$('#b-cobrar').onclick = () => {
  $('#c-total').textContent = euro(pedido.total_cent);
  $('#c-entregado').value = '';
  $('#c-cambio').textContent = '—';
  const t = pedido.total_cent;
  const rapidos = [...new Set([t, Math.ceil(t / 500) * 500, Math.ceil(t / 1000) * 1000, Math.ceil(t / 2000) * 2000, 5000])].filter(x => x >= t).slice(0, 4);
  $('#c-rapidos').innerHTML = rapidos.map(x => `<button data-e="${x}">${euro(x)}</button>`).join('');
  $('#c-rapidos').querySelectorAll('button').forEach(b => b.onclick = () => { $('#c-entregado').value = (b.dataset.e / 100).toFixed(2); calcCambio(); });
  elegirMetodo('efectivo');
  $('#d-cobro').showModal();
};
function elegirMetodo(m) {
  metodoCobro = m;
  $('#d-cobro').querySelectorAll('[data-m]').forEach(b => b.className = b.dataset.m === m ? 'primario' : '');
  $('#c-efectivo').hidden = m !== 'efectivo';
}
$('#d-cobro').querySelectorAll('[data-m]').forEach(b => b.onclick = () => elegirMetodo(b.dataset.m));
function calcCambio() {
  const e = Math.round(parseFloat($('#c-entregado').value || 0) * 100);
  $('#c-cambio').textContent = e >= pedido.total_cent ? euro(e - pedido.total_cent) : 'insuficiente';
}
$('#c-entregado').oninput = calcCambio;
$('#c-cancelar').onclick = () => $('#d-cobro').close();
$('#c-ok').onclick = async () => {
  const body = { metodo: metodoCobro };
  if (metodoCobro === 'efectivo') body.entregado_cent = Math.round(parseFloat($('#c-entregado').value || 0) * 100);
  try {
    const cerrado = await api(`/pedidos/${pedido.id}/cobrar`, { method: 'POST', body });
    $('#d-cobro').close();
    const pago = cerrado.pagos[0];
    aviso(`Cobrado ${euro(pago.importe_cent)}${pago.cambio_cent ? ' · cambio ' + euro(pago.cambio_cent) : ''}`, 'ok');
    imprimir(cerrado);
    pedido = null; pintarTicket(); verMesas();
  } catch (e) { aviso(e.message, 'error'); }
};

// ── Ticket impreso (80 mm) ──
function imprimir(p = pedido) {
  const ancho = 32, linea = '-'.repeat(ancho);
  const col = (izq, der) => izq.slice(0, ancho - der.length - 1).padEnd(ancho - der.length) + der;
  const base = Math.round(p.total_cent / 1.10);
  const txt = [
    'LA PLANCHA - Hamburgueseria'.padStart(30), 'NIF B00000000 - Ticket simplificado', linea,
    `Pedido #${p.id}  ${p.mesa ? 'Mesa ' + p.mesa : 'Llevar'}`, new Date().toLocaleString('es-ES'), `Atiende: ${p.camarero}`, linea,
    ...p.lineas.filter(l => l.estado !== 'anulada').map(l => col(`${l.cantidad} ${l.producto}`, euro(l.cantidad * l.precio_cent))),
    linea, col('Base imponible', euro(base)), col('IVA 10%', euro(p.total_cent - base)), col('TOTAL', euro(p.total_cent)),
    ...(p.pagos || []).map(pg => col(pg.metodo.toUpperCase(), euro(pg.entregado_cent ?? pg.importe_cent)) + (pg.cambio_cent ? '\n' + col('Cambio', euro(pg.cambio_cent)) : '')),
    linea, 'Gracias por su visita'.padStart(26),
  ].join('\n');
  $('#ticket-impreso').textContent = txt;
  // Los TPV imprimen en una ventana propia: no depende del CSS de impresion de la pagina
  // y deja el ticket a la vista aunque no haya impresora configurada.
  const v = window.open('', 'ticket', 'width=380,height=640');
  if (!v) { window.print(); return; }   // si el navegador bloquea la ventana, imprimimos la pagina
  v.document.write('<!doctype html><meta charset="utf-8"><title>Ticket ' + p.id +
    '</title><style>@page{size:72mm auto;margin:3mm}body{font:12px/1.35 monospace;white-space:pre}</style>' +
    '<body>' + txt.replace(/[&<>]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[ch])));
  v.document.close();
  v.focus();
  v.print();            // abre el dialogo de impresion del sistema
}
$('#b-imprimir').onclick = () => imprimir();

// ── Tiempo real ──
conectarWS(async ev => {
  if (!empleado) return;
  if (ev.tipo === 'listo') aviso(`Pedido #${ev.pedido_id}: hay platos listos en el pase`, 'ok');
  if (pedido && (ev.tipo === 'kds' || ev.tipo === 'listo' || ev.tipo === 'mesas')) {
    try { pedido = await api('/pedidos/' + pedido.id); if (pedido.estado !== 'abierto') pedido = null; } catch { pedido = null; }
    pintarTicket();
  }
  if (!$('#v-mesas').hidden && (ev.tipo === 'mesas' || ev.tipo === 'reconectado')) verMesas();
});

pintarTeclado();
if (empleado) entrar();
