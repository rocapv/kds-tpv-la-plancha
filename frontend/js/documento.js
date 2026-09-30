// Ticket y factura EN PANTALLA: no se llama nunca a la impresora del sistema operativo.
// El documento se ve, se puede ampliar y se descarga como .txt; imprimirlo es decisión del usuario
// desde su navegador, no algo que dispare la aplicación.

function lineasDocumento(d) {
  return d.pedido.lineas.filter(l => l.estado !== 'anulada');
}

function textoDocumento(d, factura = null) {
  const ancho = 40, raya = '-'.repeat(ancho);
  const col = (izq, der) => String(izq).slice(0, ancho - der.length - 1).padEnd(ancho - der.length) + der;
  const L = d.local, p = d.pedido;
  const filas = [
    L.local_nombre.toUpperCase(), L.local_direccion, `NIF ${L.local_nif} · Tel. ${L.local_telefono}`, raya,
    factura ? `FACTURA ${factura.tipo === 'completa' ? '' : 'SIMPLIFICADA '}${factura.numero_completo}`
            : `TICKET pedido #${p.id}`,
    new Date(factura ? factura.emitida_en : (p.cerrado_en || Date.now())).toLocaleString('es-ES'),
    `${p.mesa ? 'Mesa ' + p.mesa : 'Para llevar' + (p.cliente ? ' · ' + p.cliente : '')} · Atiende: ${p.camarero}`,
  ];
  if (factura && factura.cliente_nombre) {
    filas.push(raya, 'CLIENTE', factura.cliente_nombre,
      ...(factura.cliente_nif ? [`NIF ${factura.cliente_nif}`] : []),
      ...(factura.cliente_direccion ? [factura.cliente_direccion] : []));
  }
  filas.push(raya, col('CONCEPTO', 'IMPORTE'));
  lineasDocumento(d).forEach(l => filas.push(
    col(`${l.cantidad} x ${l.producto}`, euro(l.cantidad * l.precio_cent)),
    ...(l.notas ? [`    (${l.notas})`] : [])));
  filas.push(raya,
    col(`Base imponible`, euro(factura ? factura.base_cent : d.base_cent)),
    col(`IVA ${d.iva_pct} %`, euro(factura ? factura.iva_cent : d.iva_cent)),
    col('TOTAL', euro(p.total_cent)));
  (p.pagos || []).forEach(pg => {
    filas.push(col(`Pago: ${pg.metodo}`, euro(pg.entregado_cent ?? pg.importe_cent)));
    if (pg.cambio_cent) filas.push(col('Cambio', euro(pg.cambio_cent)));
  });
  filas.push(raya, factura ? 'Documento con validez fiscal' : 'Ticket sin validez fiscal · pida su factura',
    'Gracias por su visita');
  return filas.join('\n');
}

/** Muestra el documento en un panel de la propia página. */
function mostrarDocumento(d, factura = null, alPedirFactura = null) {
  document.querySelector('#visor-doc')?.remove();
  const texto = textoDocumento(d, factura);
  // Con facturas por cabeza emitidas, la de la cuenta entera cobraría dos veces lo mismo sobre el
  // papel y el servidor la rechaza. El botón no se pinta: enseñarlo para que dé error al pulsarlo
  // deja al camarero delante del cliente sin saber qué ha hecho mal.
  const porCabeza = (d.facturas_por_cabeza || []).length;
  const caja = document.createElement('div');
  caja.id = 'visor-doc';
  caja.className = 'visor';
  caja.innerHTML = `
    <div class="papel">
      <pre>${esc(texto)}</pre>
      ${porCabeza && !factura ? `<p class="tenue">Esta cuenta ya tiene ${porCabeza} factura(s) de
        quien pagó su parte, así que no puede hacerse además una de la cuenta entera. La de cada
        cobro se saca desde su ticket.</p>` : ''}
      <div class="acciones">
        <button data-cerrar>Cerrar</button>
        <button data-descargar>Descargar .txt</button>
        ${!factura && alPedirFactura && !porCabeza
          ? '<button data-factura class="primario">Emitir factura</button>' : ''}
      </div>
    </div>`;
  document.body.appendChild(caja);
  const cerrar = () => caja.remove();
  caja.onclick = e => { if (e.target === caja) cerrar(); };
  caja.querySelector('[data-cerrar]').onclick = cerrar;
  caja.querySelector('[data-descargar]').onclick = () => {
    const nombre = (factura ? 'factura_' + factura.numero_completo.replace('/', '-') : 'ticket_' + d.pedido.id) + '.txt';
    const url = URL.createObjectURL(new Blob([texto], { type: 'text/plain;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url; a.download = nombre; a.click();
    URL.revokeObjectURL(url);
  };
  caja.querySelector('[data-factura]')?.addEventListener('click', () => { cerrar(); alPedirFactura(d); });
  return caja;
}

/** Enseña un texto como documento, con lo justo: cerrar y descargar.
 *
 * No se llama a la impresora del sistema, igual que en el resto de la casa: el documento se ve y
 * se descarga, e imprimirlo es decisión de quien lo tiene delante.
 */
function visorDeTexto(texto, nombre) {
  document.querySelector('#visor-doc')?.remove();
  const caja = document.createElement('div');
  caja.id = 'visor-doc';
  caja.className = 'visor';
  caja.innerHTML = `<div class="papel"><pre>${esc(texto)}</pre>
      <div class="acciones"><button data-cerrar>Cerrar</button>
        <button data-descargar>Descargar .txt</button></div></div>`;
  document.body.appendChild(caja);
  const cerrar = () => caja.remove();
  caja.onclick = e => { if (e.target === caja) cerrar(); };
  caja.querySelector('[data-cerrar]').onclick = cerrar;
  caja.querySelector('[data-descargar]').onclick = () => {
    const url = URL.createObjectURL(new Blob([texto], { type: 'text/plain;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url; a.download = (nombre || 'documento') + '.txt'; a.click();
    URL.revokeObjectURL(url);
  };
  return caja;
}

/** Pregunta los datos fiscales y llama a `emitir`. Devuelve lo que responda, o null si se cancela.
 *
 * El diálogo NO se cierra cuando el servidor rechaza: casi siempre es un dato mal puesto o una
 * regla que hay que leer («esta mesa ya tiene factura por cabeza»), y cerrarlo obligaría a
 * teclear otra vez el NIF entero para volver a intentarlo.
 */
function pedirDatosFiscales(titulo, emitir) {
  const dlg = document.createElement('dialog');
  dlg.innerHTML = `
    <h3>${esc(titulo)}</h3>
    <p class="tenue">Sin datos del cliente se emite una factura simplificada.</p>
    <div class="fila"><input data-f-nombre placeholder="Nombre o razón social" maxlength="80" style="flex:1"></div>
    <div class="fila"><input data-f-nif placeholder="NIF/CIF" maxlength="20" style="width:10em">
      <input data-f-dir placeholder="Dirección" maxlength="120" style="flex:1"></div>
    <div class="fila"><button data-cancelar>Cancelar</button><button data-ok class="primario">Emitir</button></div>`;
  document.body.appendChild(dlg);
  dlg.showModal();
  return new Promise(resolve => {
    const fuera = () => { dlg.close(); dlg.remove(); };
    dlg.querySelector('[data-cancelar]').onclick = () => { fuera(); resolve(null); };
    dlg.querySelector('[data-ok]').onclick = async () => {
      const nombre = dlg.querySelector('[data-f-nombre]').value.trim();
      const nif = dlg.querySelector('[data-f-nif]').value.trim();
      const dir = dlg.querySelector('[data-f-dir]').value.trim();
      const body = { tipo: nombre && nif ? 'completa' : 'simplificada' };
      if (nombre) body.cliente_nombre = nombre;
      if (nif) body.cliente_nif = nif;
      if (dir) body.cliente_direccion = dir;
      try {
        const r = await emitir(body);
        fuera();
        resolve(r);
      } catch (e) { aviso(e.message, 'error'); }
    };
  });
}

/** Pide los datos del cliente y emite la factura de la cuenta entera. */
async function pedirFactura(d) {
  const f = await pedirDatosFiscales(`Emitir factura del pedido #${d.pedido.id}`,
    body => api(`/pedidos/${d.pedido.id}/factura`, { method: 'POST', body }));
  if (!f) return null;
  aviso('Factura ' + f.numero_completo + ' emitida', 'ok');
  mostrarDocumento(d, f);
  return f;
}

/** La factura de UN cobro: lo que puso esa persona, no lo que cenó la mesa.
 *
 * Hace falta porque en una mesa a escote la factura de la cuenta entera no le sirve a nadie:
 * ninguno de los cuatro pagó eso. Es la que reclama quien pagó su parte, y el reglamento de
 * facturación obliga a expedirla cuando la pide, también al día siguiente.
 */
async function pedirFacturaDeCobro(pagoId) {
  const f = await pedirDatosFiscales(`Emitir factura del cobro #${pagoId}`,
    body => api(`/pagos/${pagoId}/factura`, { method: 'POST', body }));
  if (f) aviso('Factura ' + f.numero_completo + ' emitida', 'ok');
  return f;
}

/** El texto de la factura de un cobro, con el mismo ancho de ticket que el resto. */
function textoFacturaDeCobro(doc) {
  const ancho = 40;
  const col = (izq, der) => String(izq).slice(0, ancho - der.length - 1).padEnd(ancho - der.length) + der;
  const raya = '-'.repeat(ancho);
  const filas = [
    doc.local.nombre.toUpperCase(), doc.local.direccion,
    `NIF ${doc.local.nif}${doc.local.telefono ? ' · Tel. ' + doc.local.telefono : ''}`, raya,
    `FACTURA ${doc.tipo === 'completa' ? '' : 'SIMPLIFICADA '}${doc.numero_completo}`,
    new Date(doc.emitida_en).toLocaleString('es-ES'),
  ];
  // Las dos fechas, que es lo que distingue una factura hecha en el momento de una hecha después
  // a petición del cliente. El reglamento las pide cuando no coinciden.
  if (doc.fuera_de_fecha) filas.push(`Operación: ${new Date(doc.operacion_en).toLocaleString('es-ES')}`);
  filas.push(doc.mesa ? `Mesa ${doc.mesa} · ${doc.alcance === 'mesa' ? 'cuenta entera' : 'un cobro'}`
                      : 'Un cobro de la cuenta');
  if (doc.cliente_nombre) {
    filas.push(raya, 'CLIENTE', doc.cliente_nombre,
      ...(doc.cliente_nif ? [`NIF ${doc.cliente_nif}`] : []),
      ...(doc.cliente_direccion ? [doc.cliente_direccion] : []));
  }
  filas.push(raya, col('CONCEPTO', 'IMPORTE'));
  doc.lineas.forEach(l => filas.push(col(`${l.cantidad ? l.cantidad + ' x ' : ''}${l.producto}`,
    euro(l.importe_cent))));
  filas.push(raya, col('Base imponible', euro(doc.base_cent)),
    col(`IVA ${doc.iva_pct} %`, euro(doc.iva_cent)), col('TOTAL', euro(doc.total_cent)),
    raya, 'Documento con validez fiscal', 'Gracias por su visita');
  return filas.join('\n');
}
