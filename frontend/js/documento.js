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
  const caja = document.createElement('div');
  caja.id = 'visor-doc';
  caja.className = 'visor';
  caja.innerHTML = `
    <div class="papel">
      <pre>${esc(texto)}</pre>
      <div class="acciones">
        <button data-cerrar>Cerrar</button>
        <button data-descargar>Descargar .txt</button>
        ${!factura && alPedirFactura ? '<button data-factura class="primario">Emitir factura</button>' : ''}
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

/** Pide los datos del cliente y emite la factura. Devuelve la factura emitida. */
async function pedirFactura(d) {
  const dlg = document.createElement('dialog');
  dlg.innerHTML = `
    <h3>Emitir factura del pedido #${d.pedido.id}</h3>
    <p class="tenue">Sin datos del cliente se emite una factura simplificada.</p>
    <div class="fila"><input id="f-nombre" placeholder="Nombre o razón social" maxlength="80" style="flex:1"></div>
    <div class="fila"><input id="f-nif" placeholder="NIF/CIF" maxlength="20" style="width:10em">
      <input id="f-dir" placeholder="Dirección" maxlength="120" style="flex:1"></div>
    <div class="fila"><button data-cancelar>Cancelar</button><button data-ok class="primario">Emitir</button></div>`;
  document.body.appendChild(dlg);
  dlg.showModal();
  return new Promise(resolve => {
    dlg.querySelector('[data-cancelar]').onclick = () => { dlg.close(); dlg.remove(); resolve(null); };
    dlg.querySelector('[data-ok]').onclick = async () => {
      const nombre = dlg.querySelector('#f-nombre').value.trim();
      const nif = dlg.querySelector('#f-nif').value.trim();
      const body = { tipo: nombre && nif ? 'completa' : 'simplificada' };
      if (nombre) body.cliente_nombre = nombre;
      if (nif) body.cliente_nif = nif;
      const dir = dlg.querySelector('#f-dir').value.trim();
      if (dir) body.cliente_direccion = dir;
      try {
        const f = await api(`/pedidos/${d.pedido.id}/factura`, { method: 'POST', body });
        dlg.close(); dlg.remove();
        aviso('Factura ' + f.numero_completo + ' emitida', 'ok');
        mostrarDocumento(d, f);
        resolve(f);
      } catch (e) { aviso(e.message, 'error'); }
    };
  });
}
