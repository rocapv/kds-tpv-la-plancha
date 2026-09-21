// Arqueo de caja y cierre Z.
// El informe enseña lo vendido; esta pantalla enseña el descuadre: lo que debería haber en el
// cajón (fondo + ventas en efectivo + entradas - salidas) frente a lo que hay de verdad.
// Como el ticket y la factura, el cierre Z se ve en pantalla y se descarga como .txt: la
// aplicación no llama nunca a la impresora del sistema operativo.

let estado = null;          // última respuesta de /api/arqueo
let diaVisto = null;        // fecha que se está mirando (YYYY-MM-DD)

const hoy = () => new Date().toLocaleDateString('sv');
const esHoy = () => diaVisto === hoy();
const signo = c => (c > 0 ? '+' : '') + euro(c);

/** Convierte lo que teclea el encargado ("12,50" o "12.5") a céntimos. */
function aCentimos(texto) {
  const n = Number(String(texto).replace(/\s|€/g, '').replace(',', '.'));
  return Number.isFinite(n) ? Math.round(n * 100) : NaN;
}

async function cargar(fecha = diaVisto) {
  diaVisto = fecha || hoy();
  estado = await api('/arqueo?fecha=' + diaVisto);
  pintar();
}

// ─────────────── Pintado ───────────────
function pintar() {
  const e = estado, a = e.arqueo;
  const cerrado = a && a.estado === 'cerrado';
  const diferencia = cerrado ? a.diferencia_cent : null;

  $('#kpis').innerHTML = [
    ['Fondo de cambio', euro(e.fondo_cent)],
    ['Ventas en efectivo', euro(e.ventas_efectivo_cent)],
    ['Entradas / salidas', `${euro(e.entradas_cent)} / ${euro(e.salidas_cent)}`],
    ['Debería haber', euro(e.esperado_cent)],
    ...(cerrado ? [['Contado', euro(a.contado_cent)],
                   ['Descuadre', signo(diferencia), diferencia === 0 ? 'ok' : (diferencia < 0 ? 'mal' : 'aviso')]]
                : []),
  ].map(([k, v, color]) => `<div class="kpi"><span class="tenue">${k}</span>
      <b${color ? ` style="color:var(--${color})"` : ''}>${v}</b></div>`).join('');

  $('#estado-caja').innerHTML = !a
    ? '<span class="tenue">La caja de este día no se llegó a abrir.</span>'
    : cerrado
      ? `<b>Cierre ${esc(a.numero_z)}</b> · firmado por ${esc(a.cerrado_por_nombre)}
         el ${new Date(a.cerrado_en).toLocaleString('es-ES')}
         ${a.notas ? `<div class="tenue">${esc(a.notas)}</div>` : ''}`
      : `Caja <b>abierta</b> por ${esc(a.abierto_por_nombre)} a las
         ${new Date(a.abierto_en).toLocaleTimeString('es-ES')}`;

  // Acciones: abrir, anotar movimiento, cerrar. Solo sobre el día de hoy.
  const botones = [];
  if (esHoy() && !a) botones.push('<button data-abrir class="primario">Abrir caja</button>');
  if (esHoy() && a && !cerrado) {
    botones.push('<button data-entrada>Entrada de efectivo</button>',
      '<button data-salida>Salida de efectivo</button>',
      '<button data-cerrar class="primario">Cerrar caja (Z)</button>');
  }
  if (cerrado) botones.push('<button data-ver-z>Ver cierre Z</button>');
  $('#acciones').innerHTML = botones.join(' ');
  $('#acciones').querySelector('[data-abrir]')?.addEventListener('click', abrirCaja);
  $('#acciones').querySelector('[data-entrada]')?.addEventListener('click', () => anotarMovimiento('entrada'));
  $('#acciones').querySelector('[data-salida]')?.addEventListener('click', () => anotarMovimiento('salida'));
  $('#acciones').querySelector('[data-cerrar]')?.addEventListener('click', cerrarCaja);
  $('#acciones').querySelector('[data-ver-z]')?.addEventListener('click', () => mostrarZ(estado));

  $('#metodos').innerHTML =
    '<tr><th>Método</th><th class="num">Cobros</th><th class="num">Importe</th></tr>' +
    (e.por_metodo.map(m => `<tr><td>${esc(m.metodo)}</td><td class="num">${m.pagos}</td>
        <td class="num">${euro(m.total_cent)}</td></tr>`).join('')
     || '<tr><td colspan="3" class="tenue">Sin cobros</td></tr>') +
    `<tr><td><b>Total</b></td><td class="num">${e.tickets} tickets</td>
       <td class="num"><b>${euro(e.ventas_total_cent)}</b></td></tr>
     <tr><td class="tenue">Base imponible</td><td></td><td class="num tenue">${euro(e.base_cent)}</td></tr>
     <tr><td class="tenue">IVA ${e.iva_pct} %</td><td></td><td class="num tenue">${euro(e.iva_cent)}</td></tr>`;

  const puedeBorrar = esHoy() && a && !cerrado;
  $('#movimientos').innerHTML = e.movimientos.length
    ? '<tr><th>Hora</th><th>Motivo</th><th class="num">Importe</th><th></th></tr>' +
      e.movimientos.map(m => `<tr>
        <td>${new Date(m.creado_en).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}</td>
        <td>${esc(m.motivo)} <span class="tenue">· ${esc(m.empleado)}</span></td>
        <td class="num" style="color:var(--${m.tipo === 'entrada' ? 'ok' : 'mal'})">
          ${m.tipo === 'entrada' ? '+' : '−'}${euro(m.importe_cent)}</td>
        <td class="num">${puedeBorrar ? `<button data-borrar="${m.id}">Quitar</button>` : ''}</td></tr>`).join('')
    : '<tr><td class="tenue">Sin entradas ni salidas de efectivo</td></tr>';
  $('#movimientos').querySelectorAll('[data-borrar]').forEach(b => b.onclick = async () => {
    if (!confirm('¿Quitar este movimiento de caja?')) return;
    try { estado = await api('/arqueo/movimientos/' + b.dataset.borrar, { method: 'DELETE' }); pintar(); }
    catch (err) { aviso(err.message, 'error'); }
  });

  $('#pendientes').innerHTML = e.pedidos_abiertos.length
    ? '<tr><th>Pedido</th><th class="num">Importe</th></tr>' + e.pedidos_abiertos.map(p => `<tr>
        <td>#${p.id} · ${esc(p.mesa || ('Para llevar' + (p.cliente ? ' · ' + p.cliente : '')))}</td>
        <td class="num">${euro(p.total_cent)}</td></tr>`).join('')
    : '<tr><td class="tenue">Ningún pedido sin cobrar</td></tr>';

  $('#recuento-z').innerHTML = cerrado && a.recuento
    ? '<tr><th>Valor</th><th class="num">Unidades</th><th class="num">Importe</th></tr>' +
      Object.entries(a.recuento).filter(([, n]) => n > 0)
        .sort((x, y) => y[0] - x[0])
        .map(([v, n]) => `<tr><td>${euro(+v)}</td><td class="num">${n}</td>
          <td class="num">${euro(v * n)}</td></tr>`).join('') +
      `<tr><td><b>Contado</b></td><td></td><td class="num"><b>${euro(a.contado_cent)}</b></td></tr>
       <tr><td class="tenue">Retirada</td><td></td><td class="num tenue">${euro(a.retirada_cent)}</td></tr>
       <tr><td class="tenue">Queda de fondo</td><td></td>
         <td class="num tenue">${euro(a.fondo_siguiente_cent)}</td></tr>`
    : '<tr><td class="tenue">Sin desglose de recuento</td></tr>';
}

// ─────────────── Apertura y movimientos ───────────────
async function abrirCaja() {
  const texto = prompt('Fondo de cambio con el que empieza el servicio (€):',
    (estado.fondo_sugerido_cent / 100).toFixed(2));
  if (texto === null) return;
  const cent = aCentimos(texto);
  if (!(cent >= 0)) return aviso('Importe no válido', 'error');
  try {
    estado = await api('/arqueo/apertura', { method: 'POST', body: { fondo_cent: cent } });
    aviso('Caja abierta con ' + euro(cent), 'ok');
    pintar();
  } catch (e) { aviso(e.message, 'error'); }
}

function anotarMovimiento(tipo) {
  const dlg = document.createElement('dialog');
  dlg.innerHTML = `
    <h3>${tipo === 'entrada' ? 'Entrada' : 'Salida'} de efectivo</h3>
    <p class="tenue">${tipo === 'entrada' ? 'Dinero que entra en el cajón sin ser una venta (reponer cambio).'
                                          : 'Dinero que sale del cajón (pago a un proveedor, retirada al banco).'}</p>
    <div class="fila"><input id="m-importe" placeholder="Importe €" inputmode="decimal" style="width:8em">
      <input id="m-motivo" placeholder="Motivo" maxlength="80" style="flex:1"></div>
    <div class="fila"><button data-cancelar>Cancelar</button>
      <button data-ok class="primario">Anotar</button></div>`;
  document.body.appendChild(dlg);
  dlg.showModal();
  dlg.querySelector('#m-importe').focus();
  dlg.querySelector('[data-cancelar]').onclick = () => { dlg.close(); dlg.remove(); };
  dlg.querySelector('[data-ok]').onclick = async () => {
    const cent = aCentimos(dlg.querySelector('#m-importe').value);
    const motivo = dlg.querySelector('#m-motivo').value.trim();
    if (!(cent > 0)) return aviso('Importe no válido', 'error');
    if (!motivo) return aviso('Escribe el motivo: sin él, el arqueo no explica nada', 'error');
    try {
      estado = await api('/arqueo/movimientos', { method: 'POST', body: { tipo, importe_cent: cent, motivo } });
      dlg.close(); dlg.remove();
      pintar();
    } catch (e) { aviso(e.message, 'error'); }
  };
}

// ─────────────── Cierre Z ───────────────
/** Diálogo de recuento: se teclea cuántos billetes y monedas hay de cada valor. */
function cerrarCaja() {
  const dlg = document.createElement('dialog');
  dlg.innerHTML = `
    <h3>Cierre de caja del ${new Date(diaVisto).toLocaleDateString('es-ES')}</h3>
    <p class="tenue">Cuenta el cajón. Debería haber <b>${euro(estado.esperado_cent)}</b>.</p>
    <div class="recuento">${estado.denominaciones.map(v => `<label>${euro(v)}
        <input type="number" min="0" step="1" data-valor="${v}" placeholder="0"></label>`).join('')}</div>
    <p>Contado: <b id="z-contado">${euro(0)}</b> · Descuadre: <b id="z-dif">—</b></p>
    <div class="fila"><input id="z-retirada" placeholder="Retirada al banco €" inputmode="decimal" style="width:12em">
      <input id="z-notas" placeholder="Notas del cierre" maxlength="200" style="flex:1"></div>
    <div class="fila"><button data-cancelar>Cancelar</button>
      <button data-ok class="primario">Cerrar caja y firmar Z</button></div>`;
  document.body.appendChild(dlg);
  dlg.showModal();

  const campos = [...dlg.querySelectorAll('[data-valor]')];
  const contado = () => campos.reduce((s, c) => s + (+c.dataset.valor) * (+c.value || 0), 0);
  const recalcular = () => {
    const c = contado(), dif = c - estado.esperado_cent;
    dlg.querySelector('#z-contado').textContent = euro(c);
    const marca = dlg.querySelector('#z-dif');
    marca.textContent = signo(dif);
    marca.style.color = `var(--${dif === 0 ? 'ok' : (dif < 0 ? 'mal' : 'aviso')})`;
  };
  campos.forEach(c => c.oninput = recalcular);
  recalcular();
  campos[0].focus();

  dlg.querySelector('[data-cancelar]').onclick = () => { dlg.close(); dlg.remove(); };
  dlg.querySelector('[data-ok]').onclick = async () => {
    const recuento = Object.fromEntries(campos.filter(c => +c.value > 0).map(c => [c.dataset.valor, +c.value]));
    const contado_cent = contado();
    const retirada = dlg.querySelector('#z-retirada').value.trim();
    const retirada_cent = retirada ? aCentimos(retirada) : 0;
    if (!(retirada_cent >= 0)) return aviso('Retirada no válida', 'error');
    const dif = contado_cent - estado.esperado_cent;
    if (!confirm(`Se cierra el día con ${euro(contado_cent)} contados y un descuadre de ${signo(dif)}.\n` +
                 'El cierre Z no tiene vuelta atrás. ¿Firmar?')) return;
    const body = { contado_cent, retirada_cent, recuento, notas: dlg.querySelector('#z-notas').value.trim() || null };
    try {
      estado = await api('/arqueo/cierre', { method: 'POST', body });
    } catch (e) {
      // Pedidos sin cobrar: el encargado decide si los deja para mañana.
      if (e.estado === 409 && /sin cobrar/.test(e.message)) {
        if (!confirm(e.message + '\n\n¿Cerrar igualmente?')) return;
        try { estado = await api('/arqueo/cierre?forzar=true', { method: 'POST', body }); }
        catch (e2) { return aviso(e2.message, 'error'); }
      } else { return aviso(e.message, 'error'); }
    }
    dlg.close(); dlg.remove();
    aviso('Caja cerrada · ' + estado.arqueo.numero_z, 'ok');
    pintar();
    mostrarZ(estado);
  };
}

/** Texto del cierre Z a 40 columnas, igual que el ticket y la factura. */
function textoCierreZ(e) {
  const ancho = 40, raya = '-'.repeat(ancho), doble = '='.repeat(ancho);
  const col = (izq, der) => String(izq).slice(0, ancho - der.length - 1).padEnd(ancho - der.length) + der;
  const a = e.arqueo, L = e.local;
  const filas = [
    L.local_nombre.toUpperCase(), L.local_direccion, `NIF ${L.local_nif}`, doble,
    `CIERRE DE CAJA ${a.numero_z}`,
    `Servicio del ${new Date(e.fecha).toLocaleDateString('es-ES')}`,
    `Cerrado el ${new Date(a.cerrado_en).toLocaleString('es-ES')}`, raya,
    'VENTAS',
    ...e.por_metodo.map(m => col(`  ${m.metodo} (${m.pagos})`, euro(m.total_cent))),
    col('  TOTAL VENDIDO', euro(a.ventas_total_cent)),
    col(`  Tickets`, String(a.tickets)),
    col('  Base imponible', euro(e.base_cent)),
    col(`  IVA ${e.iva_pct} %`, euro(e.iva_cent)),
    ...(e.anulados ? [col('  Pedidos anulados', String(e.anulados))] : []),
    ...(e.facturas.emitidas
      ? [col('  Facturas emitidas', String(e.facturas.emitidas)),
         `  ${e.facturas.primera} .. ${e.facturas.ultima}`]
      : ['  Sin facturas emitidas']),
    raya, 'EFECTIVO',
    col('  Fondo inicial', euro(a.fondo_cent)),
    col('  Ventas en efectivo', euro(a.ventas_efectivo_cent)),
    col('  Entradas', euro(e.entradas_cent)),
    col('  Salidas', e.salidas_cent ? '-' + euro(e.salidas_cent) : euro(0)),
    col('  DEBERIA HABER', euro(a.esperado_cent)),
    col('  CONTADO', euro(a.contado_cent)),
    col('  DESCUADRE', signo(a.diferencia_cent)),
  ];
  if (e.movimientos.length) {
    filas.push(raya, 'MOVIMIENTOS DE CAJA');
    e.movimientos.forEach(m => filas.push(
      col(`  ${m.motivo}`, (m.tipo === 'entrada' ? '+' : '-') + euro(m.importe_cent))));
  }
  if (a.recuento) {
    filas.push(raya, 'RECUENTO');
    Object.entries(a.recuento).sort((x, y) => y[0] - x[0])
      .forEach(([v, n]) => filas.push(col(`  ${euro(+v)} x ${n}`, euro(v * n))));
  }
  filas.push(raya,
    col('Retirada', euro(a.retirada_cent)),
    col('Queda de fondo', euro(a.fondo_siguiente_cent)));
  if (a.notas) filas.push(raya, 'NOTAS', ...a.notas.match(/.{1,40}/g));
  filas.push(doble, `Firmado: ${a.cerrado_por_nombre} (encargado)`,
    'Documento interno de control de caja');
  return filas.join('\n');
}

/** Muestra el cierre Z en pantalla y deja descargarlo; nunca se llama a la impresora. */
function mostrarZ(e) {
  document.querySelector('#visor-doc')?.remove();
  const texto = textoCierreZ(e);
  const caja = document.createElement('div');
  caja.id = 'visor-doc';
  caja.className = 'visor';
  caja.innerHTML = `<div class="papel"><pre>${esc(texto)}</pre>
    <div class="acciones"><button data-cerrar>Cerrar</button>
      <button data-descargar class="primario">Descargar .txt</button></div></div>`;
  document.body.appendChild(caja);
  const cerrar = () => caja.remove();
  caja.onclick = ev => { if (ev.target === caja) cerrar(); };
  caja.querySelector('[data-cerrar]').onclick = cerrar;
  caja.querySelector('[data-descargar]').onclick = () => {
    const url = URL.createObjectURL(new Blob([texto], { type: 'text/plain;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'cierre_' + e.arqueo.numero_z.replace('/', '-') + '.txt';
    a.click();
    URL.revokeObjectURL(url);
  };
}

// ─────────────── Histórico ───────────────
async function cargarHistorico() {
  const filas = await api('/arqueos');
  $('#historico').innerHTML = filas.length
    ? `<tr><th>Fecha</th><th>Cierre</th><th class="num">Ventas</th><th class="num">Descuadre</th></tr>` +
      filas.map(f => `<tr>
        <td><a href="#" data-dia="${f.fecha}">${new Date(f.fecha).toLocaleDateString('es-ES')}</a></td>
        <td>${f.numero_z ? esc(f.numero_z) + ' <span class="tenue">· ' + esc(f.cerrado_por_nombre) + '</span>'
                         : '<span class="tenue">abierta</span>'}</td>
        <td class="num">${f.ventas_total_cent === null ? '—' : euro(f.ventas_total_cent)}</td>
        <td class="num" style="color:var(--${f.diferencia_cent === null ? 'tenue'
          : (f.diferencia_cent === 0 ? 'ok' : (f.diferencia_cent < 0 ? 'mal' : 'aviso'))})">
          ${f.diferencia_cent === null ? '—' : signo(f.diferencia_cent)}</td></tr>`).join('')
    : '<tr><td class="tenue">Todavía no hay cierres</td></tr>';
  $('#historico').querySelectorAll('[data-dia]').forEach(a => a.onclick = ev => {
    ev.preventDefault();
    $('#fecha').value = a.dataset.dia;
    cargar(a.dataset.dia);
  });
}
