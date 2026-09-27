// Almacén: lo que entra del proveedor, lo que sale al vender y lo que queda.
//
// La pantalla está pensada para dos momentos muy distintos del día: el repartidor esperando en
// la puerta (entrada rápida, varias líneas de golpe) y el encargado cuadrando al cerrar
// (recuento y mermas). Por eso la entrada es un diálogo con líneas que se añaden y el ajuste
// vive en cada fila, donde ya estás mirando el número que no cuadra.

let ARTICULOS = [], ajustando = null, motivoAjuste = 'merma';

const num = n => Number(n).toLocaleString('es-ES', { maximumFractionDigits: 2 });

async function cargar() {
  const d = await api('/almacen');
  ARTICULOS = d.articulos;
  pintarKpis(d);
  pintarTabla();
}

function pintarKpis(d) {
  const sin = ARTICULOS.filter(a => a.sin).length;
  const bajo = ARTICULOS.filter(a => a.bajo && !a.sin).length;
  const descuadres = ARTICULOS.filter(a => !a.cuadra).length;
  $('#kpis').innerHTML = `
    <div class="kpi"><span>Artículos</span><b>${ARTICULOS.length}</b></div>
    <div class="kpi"><span>Sin existencias</span><b style="color:${sin ? 'var(--mal-tinta)' : 'var(--ok-tinta)'}">${sin}</b></div>
    <div class="kpi"><span>Bajo mínimo</span><b style="color:${bajo ? 'var(--aviso-tinta)' : 'var(--tenue)'}">${bajo}</b></div>
    <div class="kpi"><span>Descuento al vender</span><b>${d.descuento_activo ? 'sí' : 'no'}</b></div>
    <div class="kpi"><span>Agota la carta sola</span><b>${d.agota_carta ? 'sí' : 'no'}</b></div>
    ${descuadres ? `<div class="kpi"><span>Saldos que no cuadran</span><b style="color:var(--mal-tinta)">${descuadres}</b></div>` : ''}`;
}

function pintarTabla() {
  $('#tabla').innerHTML =
    '<tr><th>Artículo</th><th class="num">Existencias</th><th class="num">Mínimo</th>'
    + '<th class="num">Coste</th><th>Proveedor</th><th>Platos</th><th></th></tr>'
    + ARTICULOS.map(a => `
      <tr>
        <td data-col="Artículo"><b>${esc(a.nombre)}</b><br><small class="tenue">${esc(a.sku)}</small></td>
        <td class="num" data-col="Existencias">
          <b style="color:${a.sin ? 'var(--mal-tinta)' : a.bajo ? 'var(--aviso-tinta)' : 'inherit'}">
            ${num(a.stock)}</b> ${esc(a.unidad)}
          ${a.sin ? '<span class="estado anulada">agotado</span>' : a.bajo ? '<span class="estado preparando">bajo mínimo</span>' : ''}
          ${a.cuadra ? '' : '<span class="estado anulada" title="El saldo no coincide con sus movimientos">descuadre</span>'}
        </td>
        <td class="num" data-col="Mínimo">${num(a.minimo)}</td>
        <td class="num" data-col="Coste">${euro(a.coste_cent)}</td>
        <td data-col="Proveedor">${esc(a.proveedor || '—')}</td>
        <td data-col="Platos">${a.platos || '—'}</td>
        <td class="num">
          <button data-movs="${a.id}">Movimientos</button>
          <button data-ajuste="${a.id}">Corregir</button>
        </td>
      </tr>`).join('');

  $('#tabla').querySelectorAll('[data-movs]').forEach(b => b.onclick = () => verMovimientos(+b.dataset.movs));
  $('#tabla').querySelectorAll('[data-ajuste]').forEach(b => b.onclick = () => abrirAjuste(+b.dataset.ajuste));
}

// ── El libro de un artículo ──
const MOTIVOS = { albaran: 'entrada de proveedor', consumo: 'vendido', merma: 'merma',
                  ajuste: 'ajuste', recuento: 'recuento' };

async function verMovimientos(aid) {
  const d = await api(`/almacen/${aid}/movimientos`);
  $('#caja-movs').hidden = false;
  $('#m-titulo').textContent = 'Movimientos · ' + d.articulo.nombre;
  $('#m-cuadre').innerHTML = d.cuadra
    ? `Saldo <b>${num(d.saldo)}</b> ${esc(d.articulo.unidad)}, y la suma de los movimientos da lo mismo.`
    : `<b style="color:var(--mal-tinta)">El saldo (${num(d.saldo)}) no coincide con sus movimientos (${num(d.libro)}).</b>
       Manda el libro: hazle un recuento.`;
  $('#movimientos').innerHTML =
    '<tr><th>Cuándo</th><th>Motivo</th><th class="num">Cantidad</th><th>Quién</th><th>Detalle</th></tr>'
    + d.movimientos.map(m => `
      <tr>
        <td>${new Date(m.creado_en).toLocaleString('es-ES')}</td>
        <td>${esc(MOTIVOS[m.motivo] || m.motivo)}</td>
        <td class="num" style="color:${m.cantidad < 0 ? 'var(--mal-tinta)' : 'var(--ok-tinta)'}">
          ${m.cantidad > 0 ? '+' : ''}${num(m.cantidad)}</td>
        <td>${esc(m.quien)}</td>
        <td class="tenue">${esc(m.proveedor || '')}${m.documento ? ' · ' + esc(m.documento) : ''}${m.nota ? ' · ' + esc(m.nota) : ''}</td>
      </tr>`).join('');
  $('#caja-movs').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
$('#m-cerrar').onclick = () => $('#caja-movs').hidden = true;

// ── Entrada de proveedor ──
function lineaEntrada() {
  const fila = document.createElement('div');
  fila.className = 'fila';
  fila.innerHTML = `
    <select class="art" style="flex:1">${ARTICULOS.map(a =>
      `<option value="${a.id}">${esc(a.nombre)} (${esc(a.unidad)})</option>`).join('')}</select>
    <input class="cant" type="number" step="0.01" min="0.01" placeholder="Cantidad" style="width:8em">
    <input class="coste" type="number" step="0.01" min="0" placeholder="€/ud (opcional)" style="width:9em">
    <button class="mal quitar" title="Quitar esta línea">✕</button>`;
  fila.querySelector('.quitar').onclick = () => fila.remove();
  return fila;
}

$('#b-entrada').onclick = () => {
  $('#e-proveedor').value = ''; $('#e-documento').value = '';
  $('#e-lineas').innerHTML = '';
  $('#e-lineas').appendChild(lineaEntrada());
  $('#d-entrada').showModal();
};
$('#e-mas').onclick = () => $('#e-lineas').appendChild(lineaEntrada());
$('#e-cancelar').onclick = () => $('#d-entrada').close();

$('#e-ok').onclick = async () => {
  const proveedor = $('#e-proveedor').value.trim();
  if (!proveedor) return aviso('Falta el proveedor', 'error');
  const lineas = [...$('#e-lineas').querySelectorAll('.fila')].map(f => {
    const cantidad = parseFloat(f.querySelector('.cant').value);
    const coste = f.querySelector('.coste').value;
    return { inventario_id: +f.querySelector('.art').value, cantidad,
             coste_cent: coste === '' ? null : Math.round(parseFloat(coste) * 100) };
  }).filter(l => l.cantidad > 0);
  if (!lineas.length) return aviso('Ninguna línea con cantidad', 'error');
  try {
    const r = await api('/almacen/entrada', { method: 'POST', body: { proveedor, documento: $('#e-documento').value.trim() || null, lineas } });
    $('#d-entrada').close();
    aviso(`Entrada apuntada · ${r.lineas} líneas`
          + (r.repuestos ? ` · ${r.repuestos} productos vuelven a la carta` : ''), 'ok');
    cargar();
  } catch (e) { aviso(e.message, 'error'); }
};

// ── Merma y recuento ──
function abrirAjuste(aid) {
  ajustando = ARTICULOS.find(a => a.id === aid);
  motivoAjuste = 'merma';
  $('#a-titulo').textContent = 'Corregir · ' + ajustando.nombre;
  $('#a-cantidad').value = ''; $('#a-nota').value = '';
  pintarMotivo();
  $('#d-ajuste').showModal();
}
function pintarMotivo() {
  $('#a-motivos').querySelectorAll('[data-motivo]').forEach(b =>
    b.classList.toggle('activa', b.dataset.motivo === motivoAjuste));
  // En un recuento se escribe lo que HAY; en una merma, lo que se pierde. Confundir las dos
  // cosas es la manera más fácil de descuadrar un almacén, así que la etiqueta lo dice.
  $('#a-etiqueta').firstChild.textContent = motivoAjuste === 'recuento'
    ? `Existencias contadas (ahora constan ${num(ajustando.stock)} ${ajustando.unidad}) `
    : 'Cantidad que se pierde ';
}
$('#a-motivos').querySelectorAll('[data-motivo]').forEach(b => b.onclick = () => {
  motivoAjuste = b.dataset.motivo; pintarMotivo();
});
$('#a-cancelar').onclick = () => $('#d-ajuste').close();

$('#a-ok').onclick = async () => {
  const v = parseFloat($('#a-cantidad').value);
  if (!(v >= 0)) return aviso('Pon una cantidad', 'error');
  const cantidad = motivoAjuste === 'merma' ? -Math.abs(v) : v;
  try {
    const r = await api(`/almacen/${ajustando.id}/ajuste`,
                        { method: 'POST', body: { cantidad, motivo: motivoAjuste, nota: $('#a-nota').value.trim() || null } });
    $('#d-ajuste').close();
    aviso(`Apuntado · quedan ${num(r.stock)} ${ajustando.unidad}`
          + (r.agotados ? ` · ${r.agotados} productos se caen de la carta` : ''), 'ok');
    cargar();
  } catch (e) { aviso(e.message, 'error'); }
};

exigirSesion(['encargado']).then(() => {
  cargar();
  // El almacén se mueve solo cada vez que una comanda entra en cocina: la pantalla se entera.
  conectarWS(ev => { if (['carta', 'kds', 'reconectado'].includes(ev.tipo)) cargar(); });
});
