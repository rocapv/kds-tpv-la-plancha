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
      ${s.motivo_retencion ? `<p class="motivo">✋ ${esc(s.motivo_retencion)}</p>` : ''}
      ${s.nota ? `<p class="nota">⚠ ${esc(s.nota)}</p>` : ''}
      <ul class="lineas-solicitud">${s.lineas.map(l => `
        <li>
          <input type="number" min="0" max="99" value="${l.cantidad}"
                 data-linea="${l.id}" aria-label="Cantidad de ${esc(l.nombre)}">
          ${esc(l.nombre)} <span class="tenue">${euro(l.precio_cent)}</span>
        </li>`).join('')}</ul>
      <div class="fila">
        <button data-rechazar="${s.id}" class="mal">Rechazar</button>
        <button data-aceptar="${s.id}" class="ok">Aceptar y pasar a cocina</button>
      </div>
    </article>`).join('') || '<p class="tenue">No hay comandas esperando</p>';

  $('#lista-solicitudes').querySelectorAll('[data-aceptar]').forEach(b => b.onclick = async () => {
    // Las cantidades se pueden corregir antes de aceptar: es lo que hace falta cuando alguien
    // ha pedido once aguas queriendo una. A cero, la línea se cae.
    const ajustes = [...b.closest('.solicitud').querySelectorAll('[data-linea]')]
      .map(i => ({ id: +i.dataset.linea, cantidad: +i.value }));
    try {
      pedido = await api(`/solicitudes/${b.dataset.aceptar}/aceptar`,
                         { method: 'POST', body: { lineas: ajustes } });
      aviso('Comanda aceptada · repásala y envíala a cocina', 'ok');
      $('#d-solicitudes').close();
      verCarta();
      cargarSolicitudes();
    } catch (e) { aviso(e.message, 'error'); }
  });
  $('#lista-solicitudes').querySelectorAll('[data-rechazar]').forEach(b => b.onclick = async () => {
    const motivo = prompt('¿Por qué? El cliente lo verá en su teléfono.\n\n'
                         + 'Ej.: «no nos queda», «eso no se sirve en mesa»');
    if (motivo === null) return;
    await api(`/solicitudes/${b.dataset.rechazar}/rechazar`,
              { method: 'POST', body: { motivo: motivo.trim() || null } })
      .catch(e => aviso(e.message, 'error'));
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
    // Solo se pasa el color; qué se pinta con él lo decide la hoja de estilos (.cats button).
    `<button data-cat="${c.id}" class="${c.id === catActiva ? 'activa' : ''}" style="--c:${esc(c.color)}">${esc(c.nombre)}</button>`).join('');
  $('#cats').querySelectorAll('button').forEach(b => b.onclick = () => { catActiva = +b.dataset.cat; verCarta(); });
  const cat = catalogo.find(c => c.id === catActiva);
  $('#productos').innerHTML = cat.productos.map(p =>
    `<button class="producto" data-p="${p.id}" style="--c:${esc(cat.color)}"
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
  $('#b-grupo').hidden = !(pedido && pedido.mesa);
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
  pintarTarjeta(m === 'tarjeta');
}

// ── La tarjeta 3D del cobro ──────────────────────────────────────────────────────────────
// Efecto de «3D card» de robin-dela (CodePen), rehecho con código propio: se inclina siguiendo
// al puntero y el brillo la cruza al revés.
//
// Los datos son INVENTADOS en cada cobro y la tarjeta lleva su sello de «simulación». Este TPV
// no lee tarjetas, no las guarda y no habla con ninguna pasarela: solo apunta que se pagó con
// una. Pintar aquí algo con pinta de tarjeta real haría creer que el sistema tiene los datos
// del cliente, y no los tiene ni debe tenerlos.
const TITULARES = ['A. NAVARRO', 'J. SEGURA', 'M. ITURBE', 'L. CAMPOS', 'R. VILLENA', 'T. ARANDA'];
const MARCAS = ['VESTA PAY', 'ORBITAL', 'CINTURÓN'];
const alAzar = a => a[Math.floor(Math.random() * a.length)];

function datosInventados() {
  const ultimos = String(Math.floor(Math.random() * 10000)).padStart(4, '0');
  const mes = String(1 + Math.floor(Math.random() * 12)).padStart(2, '0');
  const anyo = String(new Date().getFullYear() % 100 + 1 + Math.floor(Math.random() * 4));
  return { ultimos, caduca: `${mes}/${anyo}`, titular: alAzar(TITULARES), marca: alAzar(MARCAS) };
}

function pintarTarjeta(visible) {
  const caja = $('#c-tarjeta');
  if (!caja) return;
  caja.hidden = !visible;
  if (!visible) { caja.innerHTML = ''; return; }
  const d = datosInventados();
  caja.innerHTML = `
    <div class="tarjeta3d" id="la-tarjeta">
      <span class="falsa">simulación</span>
      <span class="chip"></span>
      <div class="pan">•••• •••• •••• ${d.ultimos}</div>
      <div class="pie">
        <span><small>Titular</small><b>${esc(d.titular)}</b></span>
        <span><small>Caduca</small><b>${d.caduca}</b></span>
        <span class="marca">${esc(d.marca)}</span>
      </div>
    </div>`;

  // La inclinación sigue al puntero sobre el diálogo. Con el dedo también: en la tableta se
  // arrastra por encima y la tarjeta acompaña, que es justo lo que hace gracia enseñar.
  const tarjeta = caja.querySelector('.tarjeta3d');
  const dialogo = $('#d-cobro');
  const mover = e => {
    const r = tarjeta.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - .5;
    const y = (e.clientY - r.top) / r.height - .5;
    tarjeta.classList.add('siguiendo');
    tarjeta.style.setProperty('--ry', (x * 18).toFixed(2) + 'deg');
    tarjeta.style.setProperty('--rx', (-y * 14).toFixed(2) + 'deg');
    tarjeta.style.setProperty('--bx', (50 + x * 90) + '%');
    tarjeta.style.setProperty('--by', (30 + y * 80) + '%');
  };
  const soltar = () => {
    tarjeta.classList.remove('siguiendo');
    tarjeta.style.setProperty('--ry', '0deg'); tarjeta.style.setProperty('--rx', '0deg');
    tarjeta.style.setProperty('--bx', '50%'); tarjeta.style.setProperty('--by', '0%');
  };
  dialogo.addEventListener('pointermove', mover);
  dialogo.addEventListener('pointerleave', soltar);
  // Al cerrar el diálogo se quitan los oyentes: si no, cada cobro dejaría uno más pegado.
  dialogo.addEventListener('close', () => {
    dialogo.removeEventListener('pointermove', mover);
    dialogo.removeEventListener('pointerleave', soltar);
  }, { once: true });
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
// La bandeja de comandas del móvil SOLO se llenaba cuando llegaba el aviso por el socket. Si
// el socket estaba caído en ese instante —un reinicio del servidor, el wifi de la sala, los dos
// segundos que tarda en abrirse— la comanda se quedaba en el servidor sin que nadie la viera y
// el cliente esperando en la mesa. Así que también se vuelve a preguntar al reconectar.
function escucharEventos() {
  conectarWS(async ev => {
    if (!empleado) return;
    if (ev.tipo === 'solicitudes' || ev.tipo === 'reconectado') {
      cargarSolicitudes();
      if (ev.solicitud_id) aviso('Nueva comanda desde una mesa', 'ok');
    }
    if (ev.tipo === 'carta') { catalogo = await api('/catalogo'); if (!$('#v-carta').hidden) verCarta(); }
    if (ev.tipo === 'listo') aviso(`Pedido #${ev.pedido_id}: hay platos listos en el pase`, 'ok');
    if (pedido && (ev.tipo === 'kds' || ev.tipo === 'listo' || ev.tipo === 'mesas')) {
      try { pedido = await api('/pedidos/' + pedido.id); if (pedido.estado !== 'abierto') pedido = null; } catch { pedido = null; }
      pintarTicket();
    }
    if (!$('#v-mesas').hidden && (ev.tipo === 'mesas' || ev.tipo === 'reconectado')) verMesas();
  });
}

// Al volver la red, `sinred.js` reenvía lo apuntado y los identificadores locales mueren:
// se vuelve a las mesas para trabajar ya con los del servidor.
window.addEventListener('sinred-sincronizado', async () => {
  catalogo = await api('/catalogo').catch(() => catalogo);
  if (pedido && pedido.id < 0) { pedido = null; pintarTicket(); }
  if (!$('#v-mesas').hidden) verMesas(); else verCarta();
  cargarSolicitudes();
});

// El socket se abre con la sesión YA hecha: abrirlo antes es un 403 seguro del servidor (que
// hace bien: un socket sin sesión no es nadie) y deja la pantalla sorda mientras reintenta.
entrar().then(() => { escucharEventos(); cargarSolicitudes(); prepararMovil(); });

// ── El grupo de la mesa: quién se sienta dónde y de quién es cada plato ──
// Se abre desde el ticket y se cierra al pulsar fuera, como cualquier diálogo del navegador.
// La rejilla tiene el tamaño de la mesa: una de seis se pinta 2×3.
let grupoElegido = null;          // a quién se le van a asignar los platos que se toquen

async function cargarGrupo() {
  if (!pedido) return;
  const d = await api(`/pedidos/${pedido.id}/grupo`);
  // La cuenta va aparte del reparto: una cosa es de quién es cada plato y otra quién ha pagado.
  const cuenta = await api(`/pedidos/${pedido.id}/cuenta`).catch(() => null);
  const suCuenta = id => cuenta?.cuentas.find(c => c.comensal_id === id);
  const deuda = s => {
    const c = suCuenta(s.id);
    if (!c) return '';
    if (c.pagado && !c.a_pagar_cent) return '<p class="pagado">✓ pagado</p>';
    const parte = c.compartido_cent
      ? ` <small class="tenue">(incluye ${euro(c.compartido_cent)} de la mesa)</small>` : '';
    return `<button class="cobrar ok" data-cobrar="${s.id}">Cobrar ${euro(c.a_pagar_cent)}</button>${parte}`;
  };
  $('#g-titulo').textContent = `Mesa ${d.mesa || ''} · ${euro(d.total_cent)}`;
  const sitio = s => {
    if (s.libre) return `<button class="sitio libre" data-sentar="${s.sitio}">
        <span class="hueco-sitio">+</span><small>sitio ${s.sitio}</small></button>`;
    const elegido = grupoElegido === s.id ? ' elegido' : '';
    return `<div class="sitio${elegido}" data-comensal="${s.id}">
      <header><b>${esc(s.nombre || 'Sin nombre')}</b>
        ${s.con_movil ? '<span title="Pide desde su móvil">📱</span>' : ''}
        <button class="sutil" data-renombrar="${s.id}" title="Cambiar el nombre">✎</button>
        <button class="sutil" data-levantar="${s.id}" title="Se ha ido">✕</button>
      </header>
      <ul>${s.lineas.map(l => `<li><button data-suelta="${l.id}">${l.cantidad}× ${esc(l.producto)}</button></li>`).join('')
           || '<li class="tenue">Sin nada suyo</li>'}</ul>
      <b class="importe">${euro(s.total_cent)}</b>
      ${deuda(s)}
    </div>`;
  };
  $('#g-rejilla').style.gridTemplateColumns = `repeat(${d.columnas}, 1fr)`;
  $('#g-rejilla').innerHTML = d.rejilla.map(sitio).join('');
  $('#g-mesa').innerHTML = `
    <h4>De la mesa <span class="tenue">${euro(d.de_la_mesa.total_cent)}</span></h4>
    <ul>${d.de_la_mesa.lineas.map(l =>
      `<li><button data-coger="${l.id}">${l.cantidad}× ${esc(l.producto)}</button></li>`).join('')
      || '<li class="tenue">Todo repartido</li>'}</ul>
    ${grupoElegido ? '<p class="tenue">Toca un plato para pasárselo a quien tienes elegido.</p>'
                   : '<p class="tenue">Elige primero a alguien de la rejilla.</p>'}`;

  const recargar = () => cargarGrupo();
  $('#g-rejilla').querySelectorAll('[data-sentar]').forEach(b => b.onclick = async () => {
    const nombre = prompt('¿Quién se sienta ahí? (puedes dejarlo en blanco)');
    if (nombre === null) return;
    await api(`/pedidos/${pedido.id}/grupo`, { method: 'POST',
      body: { sitio: +b.dataset.sentar, nombre: nombre.trim() || null } })
      .catch(e => aviso(e.message, 'error'));
    recargar();
  });
  $('#g-rejilla').querySelectorAll('[data-comensal]').forEach(caja => caja.onclick = ev => {
    if (ev.target.closest('button')) return;               // los botones de dentro mandan
    grupoElegido = grupoElegido === +caja.dataset.comensal ? null : +caja.dataset.comensal;
    recargar();
  });
  $('#g-rejilla').querySelectorAll('[data-renombrar]').forEach(b => b.onclick = async () => {
    const nombre = prompt('Nombre');
    if (nombre === null) return;
    await api(`/grupo/${b.dataset.renombrar}`, { method: 'PATCH', body: { nombre: nombre.trim() || null } })
      .catch(e => aviso(e.message, 'error'));
    recargar();
  });
  $('#g-rejilla').querySelectorAll('[data-levantar]').forEach(b => b.onclick = async () => {
    if (!confirm('¿Se ha ido? Lo que pidió pasa a ser de la mesa.')) return;
    await api(`/grupo/${b.dataset.levantar}`, { method: 'DELETE' }).catch(e => aviso(e.message, 'error'));
    grupoElegido = null;
    recargar();
  });
  // Un plato suyo vuelve a la mesa; un plato de la mesa se le pasa a quien esté elegido.
  $('#g-rejilla').querySelectorAll('[data-suelta]').forEach(b => b.onclick = async () => {
    await api(`/lineas/${b.dataset.suelta}/comensal`, { method: 'PATCH', body: { comensal_id: null } })
      .catch(e => aviso(e.message, 'error'));
    recargar();
  });
  $('#g-rejilla').querySelectorAll('[data-cobrar]').forEach(b => b.onclick = async () => {
    await cobrarAComensal(+b.dataset.cobrar);
  });
  $('#g-mesa').querySelectorAll('[data-coger]').forEach(b => b.onclick = async () => {
    if (!grupoElegido) return aviso('Elige antes a quién se lo pasas', 'error');
    await api(`/lineas/${b.dataset.coger}/comensal`, { method: 'PATCH', body: { comensal_id: grupoElegido } })
      .catch(e => aviso(e.message, 'error'));
    recargar();
  });
}

$('#b-grupo').onclick = () => { grupoElegido = null; cargarGrupo().then(() => $('#d-grupo').showModal()); };
$('#g-cerrar').onclick = () => $('#d-grupo').close();

/** Cobra a uno lo suyo. Si paga en efectivo se pregunta con cuánto, para dar el cambio. */
async function cobrarAComensal(cid) {
  const metodo = prompt('¿Cómo paga?\n\n1 efectivo · 2 tarjeta · 3 bizum', '2');
  if (!metodo) return;
  const metodos = { 1: 'efectivo', 2: 'tarjeta', 3: 'bizum' };
  const elegido = metodos[metodo.trim()] || metodo.trim();
  const cuerpo = { metodo: elegido };
  if (elegido === 'efectivo') {
    const con = prompt('¿Con cuánto paga? (en euros, vacío = justo)');
    if (con === null) return;
    if (con.trim()) cuerpo.entregado_cent = Math.round(parseFloat(con.replace(',', '.')) * 100);
  }
  try {
    const r = await api(`/pedidos/${pedido.id}/grupo/${cid}/cobrar`, { method: 'POST', body: cuerpo });
    aviso(`Cobrado ${euro(r.importe_cent)} a ${r.concepto}`, 'ok');
    if (confirm('¿Enseñar su ticket?')) verTicketDePago(r.pago_id);
    pedido = await api(`/pedidos/${pedido.id}`).catch(() => pedido);
    if (pedido.estado !== 'abierto') { $('#d-grupo').close(); verMesas(); return; }
    cargarGrupo();
  } catch (e) { aviso(e.message, 'error'); }
}

/** El ticket de un pago suelto, con el aviso de que la cuenta iba dividida. */
async function verTicketDePago(pagoId) {
  const d = await api(`/pagos/${pagoId}/documento`);
  const lineas = d.lineas.map(l =>
    `${String(l.cantidad).padStart(2)}× ${l.producto.padEnd(22).slice(0, 22)} ${euro(l.cantidad * l.precio_cent).padStart(9)}`).join('\n');
  ticketEnPantalla([
    d.local.local_nombre, d.local.local_direccion, '',
    `Ticket de ${d.pago.concepto || 'un comensal'}${d.pago.mesa ? ' · mesa ' + d.pago.mesa : ''}`,
    ''.padEnd(34, '-'), lineas, ''.padEnd(34, '-'),
    `TOTAL${euro(d.pago.importe_cent).padStart(29)}`,
    `Base${euro(d.base_cent).padStart(30)}`,
    `IVA ${d.iva_pct}%${euro(d.iva_cent).padStart(24)}`,
    d.de_varios ? `\nEsta cuenta se pagó en ${d.pagos_de_la_mesa} tickets.` : '',
  ].join('\n'), { texto: 'Emitir factura', alPulsar: () => facturarUnCobro(pagoId) });
}

/** La factura de este cobro, con los datos fiscales de quien la reclama.
 *
 * El diálogo y el texto viven en `documento.js`, que es de donde salen todos los justificantes de
 * esta casa: una segunda manera de imprimir una factura es una segunda manera de imprimirla mal.
 */
async function facturarUnCobro(pagoId) {
  const f = await pedirFacturaDeCobro(pagoId);
  if (f) ticketEnPantalla(textoFacturaDeCobro(f.documento));
}

/** Enseña un texto como ticket, con el mismo visor que ya usa el ticket de la mesa.
 *
 * `extra` añade un botón más (por ejemplo «Emitir factura»). Se vuelve a crear en cada llamada
 * porque su acción cambia con el cobro que se está enseñando: reutilizar el botón de antes
 * facturaría el pago anterior, que es la clase de error que nadie ve hasta que está emitido.
 */
function ticketEnPantalla(texto, extra = null) {
  document.querySelector('#visor-ticket-pago')?.remove();
  const visor = document.createElement('div');
  visor.id = 'visor-ticket-pago';
  visor.className = 'visor';
  visor.innerHTML = `<div class="papel"><pre></pre><div class="acciones">
      ${extra ? `<button data-extra>${esc(extra.texto)}</button>` : ''}
      <button data-imprimir>Imprimir</button>
      <button class="primario" data-cerrar>Cerrar</button></div></div>`;
  document.body.appendChild(visor);
  visor.querySelector('pre').textContent = texto;
  visor.querySelector('[data-cerrar]').onclick = () => visor.remove();
  visor.querySelector('[data-imprimir]').onclick = () => window.print();
  visor.onclick = ev => { if (ev.target === visor) visor.remove(); };
  if (extra) visor.querySelector('[data-extra]').onclick = () => extra.alPulsar();
}
