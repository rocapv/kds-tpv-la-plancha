// TPV de sala: PIN → mesas → carta → enviar a cocina → cobrar
let empleado = null;
let catalogo = [], catActiva = null, pedido = null, productoElegido = null, metodoCobro = 'efectivo';

// ── Arranque: la sesión la lleva sesion.js (PIN una sola vez, luego token) ──
async function entrar() {
  empleado = await exigirSesion(['camarero', 'encargado']);
  catalogo = await api('/catalogo');
  catActiva = catalogo[0]?.id;
  verMesas();
}


// ── Comandas que los clientes piden desde su móvil ──
// Llegan a una bandeja, no a cocina: el camarero las mira, las acepta y entonces se convierten
// en un pedido normal. Así el QR de la mesa no es una puerta abierta a la cocina.
async function cargarSolicitudes() {
  let lista = [];
  try { lista = await api('/solicitudes'); } catch { return; }
  const boton = $('#b-solicitudes');
  boton.hidden = !lista.length;
  boton.classList.toggle('urgente', lista.length > 0);
  $('#n-solicitudes').textContent = lista.length;
  $('#lista-solicitudes').innerHTML = lista.map(s => `
    <article class="solicitud">
      <header>
        <b>${s.mesa ? 'Mesa ' + esc(s.mesa) : '🛍 ' + esc(s.cliente || 'Para llevar')}</b>
        <span class="tenue">hace ${minutosDesde(s.creada_en)} min · ${euro(s.total_cent)}</span>
      </header>
      ${s.nota ? `<p class="nota">⚠ ${esc(s.nota)}</p>` : ''}
      <ul>${s.lineas.map(l => `<li>${l.cantidad}× ${esc(l.nombre)}</li>`).join('')}</ul>
      <div class="fila">
        <button data-rechazar="${s.id}" class="mal">Rechazar</button>
        <button data-aceptar="${s.id}" class="ok">Aceptar y pasar a cocina</button>
      </div>
    </article>`).join('') || '<p class="tenue">No hay comandas esperando</p>';

  $('#lista-solicitudes').querySelectorAll('[data-aceptar]').forEach(b => b.onclick = async () => {
    try {
      pedido = await api(`/solicitudes/${b.dataset.aceptar}/aceptar`, { method: 'POST' });
      aviso('Comanda aceptada · repásala y envíala a cocina', 'ok');
      $('#d-solicitudes').close();
      verCarta();
      cargarSolicitudes();
    } catch (e) { aviso(e.message, 'error'); }
  });
  $('#lista-solicitudes').querySelectorAll('[data-rechazar]').forEach(b => b.onclick = async () => {
    if (!confirm('¿Rechazar esta comanda? El cliente lo verá en su teléfono.')) return;
    await api(`/solicitudes/${b.dataset.rechazar}/rechazar`, { method: 'POST' }).catch(e => aviso(e.message, 'error'));
    cargarSolicitudes();
  });
}
$('#b-solicitudes').onclick = () => { cargarSolicitudes(); $('#d-solicitudes').showModal(); };
$('#s-cerrar').onclick = () => $('#d-solicitudes').close();

// ── Móvil: el ticket es una hoja que sube desde abajo ──
function prepararMovil() {
  const cabecera = document.querySelector('.ticket-cab');
  if (!cabecera || cabecera.dataset.movil) return;
  cabecera.dataset.movil = '1';
  cabecera.onclick = () => {
    if (window.innerWidth > 800) return;          // en pantalla grande no hay nada que plegar
    document.body.classList.toggle('ticket-abierto');
  };
}

// ── Mesas ──
// Cómo se lee cada estado en el plano. El texto va en la propia mesa: un color sin leyenda
// obliga a recordar, y en hora punta nadie recuerda.
const SERVICIO = {
  libre: '', ocupada: 'abierta', sin_pedir: 'sin pedir', tomando_nota: 'tomando nota',
  en_cocina: 'en cocina', pase: 'listo en el pase', esperando_cuenta: 'esperando cuenta',
};

async function verMesas() {
  $('#v-mesas').hidden = false;
  $('#v-carta').hidden = true;
  let mesas, abiertos, estados = {};
  try {
    [mesas, abiertos] = await Promise.all([api('/mesas'), api('/pedidos')]);
    // Una mesa ocupada no dice nada: lo que el camarero necesita saber de un vistazo es si
    // están sin pedir, si hay algo listo en el pase o si llevan rato esperando la cuenta.
    const sala = await api('/sala').catch(() => null);
    if (sala) sala.mesas.forEach(m => estados[m.id] = m);
  } catch (e) {
    // Si el servidor dice que no, hay que decirlo: una sala vacía se lee como «no hay mesas»
    // y el camarero se queda mirando la pantalla sin saber que es su puesto.
    $('#v-mesas').innerHTML = `<div class="vacio"><p>${esc(e.message)}</p>
      <p class="tenue">Las mesas son del personal de sala. Si tu puesto está en cocina o fuera de
      servicio, el encargado tiene que moverte en <b>Usuarios → Mapa de la cantina</b>.</p></div>`;
    return;
  }
  const zonas = {};
  mesas.forEach(m => (zonas[m.zona] ??= []).push(m));
  let html = '';
  for (const [zona, lista] of Object.entries(zonas)) {
    html += `<div class="zona"><h3>${esc(zonaNombre(zona))}</h3><div class="mesas">` +
      lista.map(m => {
        const e = estados[m.id] || {};
        const servicio = m.pedido_id ? (e.estado || 'ocupada') : 'libre';
        const pie = m.pedido_id
          ? `${euro(m.total_cent || 0)} · ${minutosDesde(m.abierto_en)} min`
          : `${m.plazas} pax`;
        return `<button class="mesa ${m.pedido_id ? 'ocupada' : ''} ${m.pedido_id < 0 ? 'sin-red' : ''} srv-${servicio}" data-mesa="${m.id}"
                        title="${esc(SERVICIO[servicio] || '')}">
          ${esc(m.nombre)}
          ${m.pedido_id ? `<em class="srv">${esc(SERVICIO[servicio] || '')}</em>` : ''}
          <small>${pie}${e.comensales ? ' · ' + e.comensales + ' pax' : ''}</small>
        </button>`;
      }).join('') +
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
  pedido = await api('/pedidos', { method: 'POST', body: { tipo: 'sala', mesa_id: mesaId } });
  verCarta();
}

// Para llevar
$('#b-llevar').onclick = () => { $('#l-nombre').value = ''; $('#d-llevar').showModal(); };
$('#l-cancelar').onclick = () => $('#d-llevar').close();
$('#l-ok').onclick = async () => {
  pedido = await api('/pedidos', { method: 'POST', body: { tipo: 'llevar', cliente: $('#l-nombre').value || 'Cliente' } });
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
    `<button class="producto" data-p="${p.id}" style="border-left-color:${cat.color}"
              ${p.disponible ? '' : 'disabled'} title="${p.disponible ? '' : 'Agotado. '}${p.alergenos ? 'Alérgenos: ' + esc(p.alergenos) : 'Sin alérgenos declarados'}">
       ${esc(p.nombre)}${p.alergenos ? `<span class="alerg">⚠ ${esc(p.alergenos)}</span>` : ''}
       <span>${p.disponible ? euro(p.precio_cent) : 'AGOTADO'}</span></button>`).join('');
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
  const pr = buscarProducto(id);
  $('#n-titulo').textContent = pr.nombre;
  const av = $('#n-alergenos');
  av.textContent = pr.alergenos ? '⚠ Alérgenos: ' + pr.alergenos : '';
  av.hidden = !pr.alergenos;
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
  // Un pedido con id negativo se abrió sin red: solo existe en esta tableta hasta que vuelva.
  const soloAqui = hay && pedido.id < 0;
  $('#t-sub').textContent = hay
    ? (soloAqui ? `Sin enviar al servidor · ${pedido.camarero}` : `Pedido #${pedido.id} · ${pedido.camarero}`)
    : '';
  const lineas = hay ? pedido.lineas : [];
  $('#lineas').innerHTML = lineas.map(l => `
    <div class="linea">
      <b>${l.cantidad}×</b>
      <span>${esc(l.producto)} <span class="estado ${l.estado}">${l.estado}</span></span>
      <span>${euro(l.cantidad * l.precio_cent)}</span>
      ${l.estado === 'anulada' || l.estado === 'servida' ? '<span></span>' : `<button data-borrar="${l.id}" title="Quitar">✕</button>`}
      ${l.alergenos ? `<span class="alerg">⚠ ${esc(l.alergenos)}</span>` : ''}
      ${l.notas ? `<span class="nota">${esc(l.notas)}</span>` : ''}
    </div>`).join('') || '<p class="tenue">Sin productos</p>';
  $('#lineas').querySelectorAll('[data-borrar]').forEach(b => b.onclick = async () => {
    pedido = await api(`/pedidos/${pedido.id}/lineas/${b.dataset.borrar}`, { method: 'DELETE' });
    pintarTicket();
  });
  pintarComensales();
  $('#t-total').textContent = euro(hay ? pedido.total_cent : 0);
  const pendientes = lineas.some(l => l.estado === 'pendiente');
  $('#b-enviar').disabled = !pendientes;
  // Sin servidor no se cobra: la numeración de tickets y facturas es suya, y dos tabletas
  // desconectadas emitirían el mismo número. Se toma nota ahora y se cobra al volver la red.
  const sinServidor = typeof sinRed === 'object' && (!sinRed.hayRed() || soloAqui);
  $('#b-cobrar').disabled = !hay || pendientes || pedido.total_cent === 0 || sinServidor;
  $('#b-cobrar').title = sinServidor ? 'Sin conexión: se podrá cobrar cuando vuelva la red' : '';
  if (hay && pedido.pagado_cent) $('#b-cobrar').textContent = 'Cobrar (faltan ' + euro(pedido.pendiente_cent) + ')';
  else $('#b-cobrar').textContent = 'Cobrar';
  $('#b-documento').disabled = !hay || pedido.total_cent === 0 || sinServidor;
  $('#b-anular').disabled = !hay;
}

// Cuántos se sientan en la mesa. Nadie lo apuntaba, y sin ese dato la sala no puede decir
// cuánta gente hay dentro ni cuánto gasta cada comensal.
function pintarComensales() {
  const caja = $('#comensales');
  if (!caja) return;
  const hay = pedido && pedido.tipo === 'sala';
  caja.hidden = !hay;
  if (!hay) return;
  $('#b-comensales').innerHTML = [1, 2, 3, 4, 5, 6, 8].map(n =>
    `<button data-pax="${n}" class="${pedido.comensales === n ? 'primario' : ''}">${n}</button>`).join('');
  $('#b-comensales').querySelectorAll('[data-pax]').forEach(b => b.onclick = async () => {
    try {
      pedido = await api(`/pedidos/${pedido.id}/comensales`, { method: 'PATCH',
                                                              body: { comensales: +b.dataset.pax } });
      pintarTicket();
    } catch (e) { aviso(e.message, 'error'); }
  });
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
  if (ev.tipo === 'solicitudes') { cargarSolicitudes(); if (ev.solicitud_id) aviso('Nueva comanda desde una mesa', 'ok'); }
  if (ev.tipo === 'carta') { catalogo = await api('/catalogo'); if (!$('#v-carta').hidden) verCarta(); }
  if (ev.tipo === 'listo') aviso(`Pedido #${ev.pedido_id}: hay platos listos en el pase`, 'ok');
  if (pedido && (ev.tipo === 'kds' || ev.tipo === 'listo' || ev.tipo === 'mesas')) {
    try { pedido = await api('/pedidos/' + pedido.id); if (pedido.estado !== 'abierto') pedido = null; } catch { pedido = null; }
    pintarTicket();
  }
  if (!$('#v-mesas').hidden && (ev.tipo === 'mesas' || ev.tipo === 'reconectado')) verMesas();
});

// Al volver la red, `sinred.js` reenvía lo apuntado y los identificadores locales mueren:
// se vuelve a las mesas para trabajar ya con los del servidor.
window.addEventListener('sinred-sincronizado', async () => {
  catalogo = await api('/catalogo').catch(() => catalogo);
  if (pedido && pedido.id < 0) { pedido = null; pintarTicket(); }
  if (!$('#v-mesas').hidden) verMesas(); else verCarta();
  cargarSolicitudes();
});

entrar().then(() => { cargarSolicitudes(); prepararMovil(); });
