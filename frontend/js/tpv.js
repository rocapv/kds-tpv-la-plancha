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
    `<button class="producto" data-p="${p.id}" style="border-left-color:${cat.color}" ${p.disponible ? '' : 'disabled title="Agotado"'}>
       ${esc(p.nombre)}<span>${p.disponible ? euro(p.precio_cent) : 'AGOTADO'}</span></button>`).join('');
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
  if (hay && pedido.pagado_cent) $('#b-cobrar').textContent = 'Cobrar (faltan ' + euro(pedido.pendiente_cent) + ')';
  else $('#b-cobrar').textContent = 'Cobrar';
  $('#b-documento').disabled = !hay || pedido.total_cent === 0;
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

// ── Cobro: entero, dividido en partes o por líneas, y con varios métodos ──
let modoCobro = 'todo', lineasElegidas = new Set();

$('#b-cobrar').onclick = () => abrirCobro();

async function abrirCobro() {
  pedido = await api('/pedidos/' + pedido.id);
  modoCobro = 'todo'; lineasElegidas.clear();
  $('#c-pedido').textContent = '#' + pedido.id + (pedido.mesa ? ' · Mesa ' + pedido.mesa : '');
  elegirMetodo('efectivo');
  pintarCobro();
  $('#d-cobro').showModal();
}

function lineasPagables() {
  return pedido.lineas.filter(l => l.estado !== 'anulada' && !l.pago_id);
}

function importeACobrar() {
  if (modoCobro === 'partes') {
    const n = Math.max(2, +$('#c-n').value || 2);
    const parte = Math.floor(pedido.total_cent / n);
    // la última parte absorbe los céntimos que no reparten exactos
    return Math.min(parte, pedido.pendiente_cent) || pedido.pendiente_cent;
  }
  if (modoCobro === 'lineas') {
    return pedido.lineas.filter(l => lineasElegidas.has(l.id))
      .reduce((s, l) => s + l.cantidad * l.precio_cent, 0);
  }
  return pedido.pendiente_cent;
}

function pintarCobro() {
  $('#c-total').textContent = euro(pedido.total_cent);
  $('#c-pagado').textContent = euro(pedido.pagado_cent);
  $('#c-pendiente').textContent = euro(pedido.pendiente_cent);
  $('#c-modos').querySelectorAll('[data-modo]').forEach(b =>
    b.className = b.dataset.modo === modoCobro ? 'primario' : '');
  $('#c-partes').hidden = modoCobro !== 'partes';
  $('#c-lineas').hidden = modoCobro !== 'lineas';

  if (modoCobro === 'partes') {
    const n = Math.max(2, +$('#c-n').value || 2);
    $('#c-parte').textContent = euro(Math.floor(pedido.total_cent / n));
  }
  if (modoCobro === 'lineas') {
    $('#c-lineas').innerHTML = pedido.lineas.filter(l => l.estado !== 'anulada').map(l => `
      <label class="linea-elegible ${l.pago_id ? 'pagada' : ''}">
        <input type="checkbox" data-l="${l.id}" ${l.pago_id ? 'disabled' : ''} ${lineasElegidas.has(l.id) ? 'checked' : ''}>
        <span>${l.cantidad}× ${esc(l.producto)}</span>
        <span class="num">${euro(l.cantidad * l.precio_cent)}</span>
        ${l.pago_id ? '<span class="estado lista">pagada</span>' : ''}
      </label>`).join('');
    $('#c-lineas').querySelectorAll('[data-l]').forEach(ch => ch.onchange = () => {
      ch.checked ? lineasElegidas.add(+ch.dataset.l) : lineasElegidas.delete(+ch.dataset.l);
      pintarCobro();
    });
  }

  const importe = importeACobrar();
  $('#c-importe').textContent = euro(importe);
  $('#c-ok').disabled = importe <= 0 || importe > pedido.pendiente_cent;

  const rapidos = [...new Set([importe, Math.ceil(importe / 500) * 500, Math.ceil(importe / 1000) * 1000,
                               Math.ceil(importe / 2000) * 2000, 5000])].filter(x => x >= importe).slice(0, 4);
  $('#c-rapidos').innerHTML = rapidos.map(x => `<button data-e="${x}">${euro(x)}</button>`).join('');
  $('#c-rapidos').querySelectorAll('button').forEach(b => b.onclick = () => {
    $('#c-entregado').value = (b.dataset.e / 100).toFixed(2); calcCambio();
  });
  calcCambio();

  $('#c-registrados').innerHTML = pedido.pagos.length
    ? '<h4>Pagos registrados</h4>' + pedido.pagos.map(g => `
        <div class="pago-hecho"><span>${esc(g.metodo)}${g.concepto ? ' · ' + esc(g.concepto) : ''}</span>
          <span class="num">${euro(g.importe_cent)}</span>
          <button data-deshacer="${g.id}" class="mal" title="Deshacer">✕</button></div>`).join('')
    : '';
  $('#c-registrados').querySelectorAll('[data-deshacer]').forEach(b => b.onclick = async () => {
    pedido = await api(`/pedidos/${pedido.id}/pagos/${b.dataset.deshacer}`, { method: 'DELETE' });
    lineasElegidas.clear(); pintarCobro(); pintarTicket();
  });
}

$('#c-modos').querySelectorAll('[data-modo]').forEach(b => b.onclick = () => {
  modoCobro = b.dataset.modo; lineasElegidas.clear(); pintarCobro();
});
$('#c-n').oninput = pintarCobro;

function elegirMetodo(m) {
  metodoCobro = m;
  $('#c-metodos').querySelectorAll('[data-m]').forEach(b => b.className = b.dataset.m === m ? 'primario' : '');
  $('#c-efectivo').hidden = m !== 'efectivo';
}
$('#c-metodos').querySelectorAll('[data-m]').forEach(b => b.onclick = () => elegirMetodo(b.dataset.m));

function calcCambio() {
  const e = Math.round(parseFloat($('#c-entregado').value || 0) * 100);
  const importe = importeACobrar();
  $('#c-cambio').textContent = !e ? '—' : e >= importe ? euro(e - importe) : 'insuficiente';
}
$('#c-entregado').oninput = calcCambio;
$('#c-cancelar').onclick = () => $('#d-cobro').close();

$('#c-ok').onclick = async () => {
  const body = { metodo: metodoCobro };
  if (modoCobro === 'lineas') body.lineas = [...lineasElegidas];
  else if (modoCobro === 'partes') { body.importe_cent = importeACobrar(); body.concepto = 'parte'; }
  if (metodoCobro === 'efectivo') {
    const e = Math.round(parseFloat($('#c-entregado').value || 0) * 100);
    if (e) body.entregado_cent = e;
  }
  try {
    const antes = pedido.id;
    pedido = await api(`/pedidos/${pedido.id}/pagos`, { method: 'POST', body });
    const ultimo = pedido.pagos[pedido.pagos.length - 1];
    aviso(`Cobrado ${euro(ultimo.importe_cent)}${ultimo.cambio_cent ? ' · cambio ' + euro(ultimo.cambio_cent) : ''}`, 'ok');
    if (pedido.estado === 'cobrado') {
      $('#d-cobro').close();
      verDocumento(antes);
      pedido = null; pintarTicket(); verMesas();
    } else {
      lineasElegidas.clear();
      $('#c-entregado').value = '';
      pintarCobro(); pintarTicket();
    }
  } catch (e) { aviso(e.message, 'error'); }
};

// ── Ticket y factura: SIEMPRE en pantalla, nunca se llama a la impresora del sistema ──
async function verDocumento(pedidoId, ofrecerFactura = true) {
  const d = await api('/pedidos/' + pedidoId + '/documento');
  mostrarDocumento(d, d.factura, ofrecerFactura ? (dd => pedirFactura(dd)) : null);
}
$('#b-documento').onclick = () => verDocumento(pedido.id, pedido.estado === 'cobrado');

// ── Tiempo real ──
conectarWS(async ev => {
  if (!empleado) return;
  if (ev.tipo === 'carta') { catalogo = await api('/catalogo'); if (!$('#v-carta').hidden) verCarta(); }
  if (ev.tipo === 'listo') aviso(`Pedido #${ev.pedido_id}: hay platos listos en el pase`, 'ok');
  if (pedido && (ev.tipo === 'kds' || ev.tipo === 'listo' || ev.tipo === 'mesas')) {
    try { pedido = await api('/pedidos/' + pedido.id); if (pedido.estado !== 'abierto') pedido = null; } catch { pedido = null; }
    pintarTicket();
  }
  if (!$('#v-mesas').hidden && (ev.tipo === 'mesas' || ev.tipo === 'reconectado')) verMesas();
});

pintarTeclado();
if (empleado) entrar();
