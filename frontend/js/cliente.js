// Carta en el móvil del cliente. Sin PIN y sin sesión: solo la carta, la cesta y el estado
// de la propia comanda. Nada de lo que se pulse aquí llega a cocina por sí solo: entra en una
// bandeja y un camarero la acepta, igual que si el cliente levantara la mano.
const mesaDelQR = new URLSearchParams(location.search).get('mesa');   // …/cliente.html?mesa=3
const LLAVE_CESTA = 'kds_cesta';
const LLAVE_COMANDA = 'kds_mi_comanda';

let carta = [], catActiva = null, cesta = [], local = {};
let alergenos = [], destacados = [], destacado = 0;
let cuentaDeLaMesa = null;         // lo último que dijo el servidor de la cuenta de esta mesa
try { cesta = JSON.parse(localStorage.getItem(LLAVE_CESTA) || '[]'); } catch { cesta = []; }

const LLAVE_TEMA = 'kds_tema';

function aplicarTema(t) {
  document.body.dataset.tema = t;
  try { localStorage.setItem(LLAVE_TEMA, t); } catch {}
  $('#b-tema').classList.toggle('dia', t === 'claro');
}
(function temaInicial() {
  let t = null;
  try { t = localStorage.getItem(LLAVE_TEMA); } catch {}
  if (!t) t = matchMedia('(prefers-color-scheme: light)').matches ? 'claro' : 'oscuro';
  document.addEventListener('DOMContentLoaded', () => aplicarTema(t), { once: true });
  if (document.readyState !== 'loading') aplicarTema(t);
})();

// La cinta de categorías se queda pegada justo debajo de la cabecera, y para eso necesita saber
// cuánto mide. En el CSS estaba escrito «60px» a mano, que es lo que mide con UNA fila: en un móvil
// estrecho la cabecera baja de línea, mide casi el doble, y las categorías se quedaban escondidas
// detrás de ella. Así que se mide de verdad, y se vuelve a medir cuando cambia: al girar el
// teléfono, o cuando aparece el botón de instalar la app.
(function altoDeLaBarra() {
  const arrancar = () => {
    const barra = document.querySelector('header.barra-cliente');
    if (!barra) return;
    const medir = () => document.documentElement.style.setProperty('--alto-barra', barra.offsetHeight + 'px');
    medir();
    new ResizeObserver(medir).observe(barra);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar, { once: true });
  else arrancar();
})();

const guardarCesta = () => { try { localStorage.setItem(LLAVE_CESTA, JSON.stringify(cesta)); } catch {} };
const totalCesta = () => cesta.reduce((s, l) => s + l.cantidad * l.precio_cent, 0);

// ── Carta ──
async function cargar() {
  [local, carta, alergenos, destacados] = await Promise.all([
    api('/publico/local'), api('/publico/carta'),
    api('/publico/alergenos').catch(() => []),
    api('/publico/destacados').catch(() => []),
  ]);
  $('#local').textContent = local.nombre || 'Cantina';
  document.title = 'Carta · ' + (local.nombre || '');
  $('#mensaje').textContent = local.mensaje || '';
  $('#mensaje').hidden = !local.mensaje;
  catActiva = catActiva || carta[0]?.id;

  const mesas = await api('/publico/mesas').catch(() => []);
  $('#c-mesa').innerHTML = '<option value="">Me lo llevo</option>' +
    mesas.map(m => `<option value="${m.id}" ${String(m.id) === mesaDelQR ? 'selected' : ''}>
        ${esc(m.nombre)} · ${esc(m.zona)}</option>`).join('');
  const mia = mesas.find(m => String(m.id) === mesaDelQR);
  $('#donde').textContent = mia ? 'Mesa ' + mia.nombre : 'Carta';

  pintarLeyenda();
  pintarDestacados();
  pintarCategorias();
  pintarCarta();
  pintarCesta();
}

function pintarCategorias() {
  $('#cats').innerHTML = carta.map(c =>
    `<button data-cat="${c.id}" class="${c.id === catActiva ? 'activa' : ''}"
             style="--color:${esc(c.color)}">${esc(c.nombre)}</button>`).join('');
  $('#cats').querySelectorAll('button').forEach(b => b.onclick = () => {
    catActiva = +b.dataset.cat;
    pintarCategorias();
    document.getElementById('cat-' + catActiva)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}

function pintarCarta() {
  $('#carta').innerHTML = carta.map(c => `
    <section id="cat-${c.id}">
      <h2 style="border-color:${esc(c.color)}">${esc(c.nombre)}</h2>
      ${c.productos.map(p => `
        <article class="plato ${p.disponible ? '' : 'agotado'}">
          <div class="datos">
            <b>${esc(p.nombre)}</b>
            ${chipsDe(p)}
            ${p.disponible ? '' : '<small class="tenue">hoy no queda</small>'}
          </div>
          <div class="precio">${euro(p.precio_cent)}</div>
          ${p.disponible ? `<button class="sumar" data-p="${p.id}" aria-label="Añadir ${esc(p.nombre)}">+</button>` : ''}
        </article>`).join('')}
    </section>`).join('');
  $('#carta').querySelectorAll('[data-p]').forEach(b => b.onclick = () => anadir(+b.dataset.p, b));
}

const GRAVEDAD = { muy_grave: 'roja', grave: 'ambar', leve: 'suave' };

function pintarLeyenda() {
  if (!alergenos.length) { $('#leyenda').hidden = true; return; }
  $('#leyenda-lista').innerHTML = alergenos.map(a =>
    `<span class="chip ${GRAVEDAD[a.gravedad] || 'suave'}">${esc(a.icono)} ${esc(a.nombre)}</span>`).join('');
}

function chipsDe(p) {
  const suyos = (p.alergeno_claves || []).map(k => alergenos.find(a => a.clave === k)).filter(Boolean);
  if (suyos.length) {
    return `<span class="chips">${suyos.map(a =>
      `<span class="chip ${GRAVEDAD[a.gravedad] || 'suave'}" title="${esc(a.nombre)}">${esc(a.icono)}</span>`).join('')}</span>`;
  }
  return p.alergenos ? `<small class="alerg">⚠ ${esc(p.alergenos)}</small>` : '';
}

// Destacados: una pila de tarjetas que se pasa con el dedo. La tarjeta es un escaparate —foto y
// nombre, nada más— y al pulsarla se abre la ficha con el precio, los alérgenos y el botón de
// pedir. Antes cada tarjeta llevaba su precio y su «Añadir» encima, que es mucho cartel para algo
// que se pasa con el dedo.
function pintarDestacados() {
  const caja = $('#destacados');
  if (!destacados.length) { caja.hidden = true; return; }
  caja.hidden = false;
  $('#pila').innerHTML = destacados.map((d, i) => `
    <button type="button" class="tarjeta" data-ficha="${d.id}" data-i="${i}"
            style="--color:${esc(d.color || '#e67e22')}"
            aria-label="Ver ${esc(d.nombre)}">
      ${fotoDe(d)}
      <b>${esc(d.nombre)}</b>
    </button>`).join('');
  colocarPila();
}

// Los oyentes del dedo van sobre `#pila`, que NO se rehace nunca: dentro de `pintarDestacados()`
// se acumulaba uno por cada repintado, y la carta se repinta sola cada minuto y cada vez que el
// servidor avisa. Al cuarto de hora, un solo barrido pasaba quince tarjetas. Por eso se enganchan
// UNA vez, aquí, y las tarjetas —que sí se rehacen— se atienden por delegación.
//
// El barrido y la pulsación salen del mismo dedo, así que hay que distinguirlos: se mide cuánto
// se ha movido entre `pointerdown` y `pointerup`, y por encima de 10 px ya no cuenta como
// pulsación. Sin eso, cada barrido terminaba abriendo la ficha de la tarjeta recién apartada.
// `pointercancel` cuenta tanto como `pointerup`: si el sistema se queda el gesto a medias, el
// punto de partida no puede quedarse puesto esperando al toque siguiente.
(function gestosDeLaPila() {
  const pila = $('#pila');
  if (!pila) return;
  let x0 = null, arrastrado = false;
  pila.addEventListener('pointerdown', e => { x0 = e.clientX; arrastrado = false; });
  pila.addEventListener('pointercancel', () => { x0 = null; arrastrado = true; });
  pila.addEventListener('pointerup', e => {
    if (x0 === null) return;
    const dx = e.clientX - x0;
    x0 = null;
    arrastrado = Math.abs(dx) > 10;
    if (Math.abs(dx) > 40) girar(dx < 0 ? 1 : -1);
  });
  pila.addEventListener('click', e => {
    const t = e.target.closest('[data-ficha]');
    if (t && !arrastrado) verFicha(+t.dataset.ficha);
  });
})();

// Hoy ningún producto del local tiene foto subida, y una tarjeta que solo enseña imagen y nombre
// sin imagen no enseña nada. Pero la imagen ya existía: el servidor dibuja cada plato en
// `/api/productos/{id}/foto.svg` —un cuenco con formas, estable por nombre— y las pantallas del
// personal llevan tiempo usándolo. Lo que faltaba era que la carta pública lo sirviera, y eso se
// arregla en el backend, no aquí. Así que esto se limita a preferir la foto de verdad y caer en
// la dibujada; la inicial sobre el color de la categoría queda de último recurso, para cuando el
// servidor no manda ni una cosa ni la otra.
// `draggable="false"` no es adorno: una imagen se arrastra de fábrica, y el navegador tomaba el
// barrido por un arrastre nativo de imagen. Entonces manda `dragstart`, detrás `pointercancel`, y
// el `pointerup` que hace girar la pila NO LLEGA NUNCA: con la inicial de texto el carrusel se
// pasaba con el dedo, y en cuanto hubo imágenes de verdad dejó de pasarse. Medido, no supuesto.
function fotoDe(d) {
  const src = d.foto_url || d.foto;
  if (src) return `<img src="${esc(src)}" alt="" loading="lazy" draggable="false">`;
  return `<span class="sin-foto" aria-hidden="true">${esc((d.nombre || '?').trim()[0].toUpperCase())}</span>`;
}

// La ficha del producto: lo que la tarjeta no enseña. Los datos buenos (alérgenos, si queda) están
// en la carta, no en el resumen de destacados, así que se cruzan por id.
function verFicha(id) {
  const d = destacados.find(x => x.id === id) || {};
  const p = buscar(id) || d;
  const hay = p.disponible === undefined ? true : !!p.disponible;
  $('#p-foto').innerHTML = fotoDe(d.foto_url || d.foto ? d : p);
  $('#p-foto').style.setProperty('--color', d.color || '#e67e22');
  $('#p-categoria').textContent = d.categoria || '';
  $('#p-nombre').textContent = p.nombre || d.nombre || '';
  $('#p-alergenos').innerHTML = chipsDe(p);
  $('#p-precio').textContent = euro(p.precio_cent ?? d.precio_cent);
  $('#p-agotado').hidden = hay;
  const boton = $('#p-pedir');
  boton.disabled = !hay;
  boton.textContent = hay ? 'Añadir' : 'Hoy no queda';
  boton.onclick = () => { anadir(id, boton); $('#d-producto').close(); };
  $('#d-producto').showModal();
}
$('#p-cerrar').onclick = () => $('#d-producto').close();

function colocarPila() {
  const tarjetas = [...$('#pila').children];
  tarjetas.forEach((t, i) => {
    const pos = (i - destacado + tarjetas.length) % tarjetas.length;
    t.style.setProperty('--pos', pos);
    t.classList.toggle('arriba', pos === 0);
    t.hidden = pos > 2;                    // solo se ven tres: la de delante y dos asomando
  });
  $('#d-cuenta').textContent = `${destacado + 1} / ${tarjetas.length}`;
}

function girar(paso) {
  destacado = (destacado + paso + destacados.length) % destacados.length;
  colocarPila();
}
$('#d-antes').onclick = () => girar(-1);
$('#d-despues').onclick = () => girar(1);
$('#b-tema').onclick = () => aplicarTema(document.body.dataset.tema === 'claro' ? 'oscuro' : 'claro');

function buscar(id) {
  for (const c of carta) for (const p of c.productos) if (p.id === id) return p;
}

function anadir(id, boton) {
  const p = buscar(id);
  const linea = cesta.find(l => l.producto_id === id);
  if (linea) linea.cantidad++;
  else cesta.push({ producto_id: id, nombre: p.nombre, precio_cent: p.precio_cent, cantidad: 1 });
  guardarCesta();
  pintarCesta();
  if (boton) {                                   // respuesta inmediata al dedo
    boton.classList.add('pulsado');
    setTimeout(() => boton.classList.remove('pulsado'), 250);
  }
}

// ── Cesta ──
function pintarCesta() {
  const n = cesta.reduce((s, l) => s + l.cantidad, 0);
  $('#cesta').hidden = n === 0;
  $('#n-cesta').textContent = n;
  $('#t-cesta').textContent = euro(totalCesta());
  $('#t-dialogo').textContent = euro(totalCesta());
  $('#lista-cesta').innerHTML = cesta.map((l, i) => `
    <div class="linea-cesta">
      <button data-menos="${i}" aria-label="Quitar uno">−</button>
      <span class="cant">${l.cantidad}</span>
      <button data-mas="${i}" aria-label="Añadir uno">+</button>
      <span class="nombre">${esc(l.nombre)}</span>
      <span class="importe">${euro(l.cantidad * l.precio_cent)}</span>
    </div>`).join('') || '<p class="tenue">Todavía no has elegido nada</p>';
  $('#lista-cesta').querySelectorAll('[data-mas]').forEach(b => b.onclick = () => {
    cesta[+b.dataset.mas].cantidad++; guardarCesta(); pintarCesta();
  });
  $('#lista-cesta').querySelectorAll('[data-menos]').forEach(b => b.onclick = () => {
    const l = cesta[+b.dataset.menos];
    if (--l.cantidad <= 0) cesta.splice(+b.dataset.menos, 1);
    guardarCesta(); pintarCesta();
  });
}

$('#b-ver').onclick = () => $('#d-cesta').showModal();
$('#c-cancelar').onclick = () => $('#d-cesta').close();
$('#b-enviar').onclick = () => $('#d-cesta').showModal();

$('#c-ok').onclick = async () => {
  if (!cesta.length) return aviso('Tu comanda está vacía', 'error');
  const lineas = cesta.map(l => ({ producto_id: l.producto_id, cantidad: l.cantidad }));
  const nota = $('#c-nota').value.trim() || null;
  // Con la mesa leída del QR, la comanda va derecha a cocina salvo que salte el filtro. Sin
  // mesa vinculada se sigue como antes: el cliente dice dónde está y lo confirma un camarero.
  const enLaMesa = typeof tokenVisita === 'function' && tokenVisita();
  try {
    if (enLaMesa) {
      const r = await api('/publico/visita/pedido', { method: 'POST', body: { lineas, nota } });
      cesta = []; guardarCesta(); pintarCesta();
      $('#d-cesta').close();
      if (r.estado === 'en cocina') {
        aviso('Pedido en cocina', 'ok');
      } else {
        aviso('Un camarero tiene que confirmarlo: ' + r.motivo, 'info');
      }
      verComandaDeLaMesa();
      return;
    }
    const r = await api('/publico/solicitudes', { method: 'POST', body: {
      mesa_id: $('#c-mesa').value ? +$('#c-mesa').value : null,
      cliente: $('#c-nombre').value.trim() || null, nota, lineas,
    }});
    cesta = []; guardarCesta(); pintarCesta();
    $('#d-cesta').close();
    aviso('Comanda enviada · la confirma un camarero', 'ok');
    seguirComanda(r.id);
    $('#mi-comanda').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (e) { aviso(e.message, 'error'); }
};

/** Lo que lleva pedido la mesa, con el estado de cada plato en palabras de cliente. */
async function verComandaDeLaMesa() {
  if (!(typeof tokenVisita === 'function' && tokenVisita())) return;
  const caja = $('#comanda-mesa');
  if (!caja) return;
  let d;
  try { d = await api('/publico/visita/comanda'); } catch { caja.hidden = true; return; }
  const hay = d.lineas.length || d.esperando.length || d.rechazadas.length;
  caja.hidden = !hay;
  if (!hay) return;
  const fila = l => `<div class="linea-cesta"><span class="cant">${l.cantidad}</span>
      <span class="nombre">${esc(l.nombre)}</span>
      <span class="importe">${esc(l.estado || '')}</span></div>`;
  cuentaDeLaMesa = d;
  caja.innerHTML = `
    <div class="cab"><b>Tu mesa ${esc(d.mesa)}</b>
      <span class="tenue">${euro(d.total_cent)}${d.pagado_cent ? ' · pagado ' + euro(d.pagado_cent) : ''}</span></div>
    ${d.lineas.map(fila).join('')}
    ${d.esperando.map(s => `<p class="esperando">⏳ ${s.lineas.map(l => `${l.cantidad}× ${esc(l.nombre)}`).join(', ')}
        <small>${esc(s.motivo_retencion || 'esperando confirmación')}</small></p>`).join('')}
    ${d.rechazadas.map(r => `<p class="rechazada">✕ No ha podido ser${r.motivo_rechazo ? ': ' + esc(r.motivo_rechazo) : ''}</p>`).join('')}
    ${botonDePagar(d)}`;
}

/** El pie de la cuenta: qué se puede pagar desde aquí, si es que queda algo.
 *
 * El botón de la factura sale en cuanto hay algo cobrado en la mesa. No se consulta al servidor
 * para decidir si pintarlo: eso duplicaría el sondeo de la cuenta cada quince segundos para una
 * pregunta que solo importa cuando alguien la pulsa. Quien la pulsa se encuentra dentro con la
 * respuesta de verdad —su factura, la de la mesa, o a quién pedirla—, que es donde tiene sentido.
 */
function botonDePagar(d) {
  const factura = d.pagado_cent
    ? '<button data-pagar="factura" class="sutil">Factura</button>' : '';
  if (d.saldo_cent <= 0) {
    return d.total_cent
      ? `<div class="fila acciones-cuenta"><span class="pagada">✓ Cuenta pagada</span>${factura}</div>`
      : '';
  }
  // Ya pagó lo suyo pero la mesa sigue debiendo: no se le empuja a pagar otra vez, se le dice en
  // qué va la mesa. Sin esto, el botón «Pagar» seguiría ahí después de haber pagado y parecería
  // que el pago no ha entrado.
  if (d.mio && d.mio.pagado) {
    return `<p class="tenue">Lo tuyo está pagado. La mesa debe todavía ${euro(d.saldo_cent)}.</p>
      <div class="fila"><button data-pagar="todo" class="sutil">Pagar lo que queda</button>${factura}</div>`;
  }
  return `<div class="fila acciones-cuenta">
      <span class="tenue">Queda por pagar ${euro(d.saldo_cent)}</span>
      ${factura}<button data-pagar="abrir" class="primario">Pagar</button>
    </div>`;
}

// Los botones de la cuenta se rehacen en cada repaso —cada 15 s—, así que el oyente va UNA vez
// sobre la caja, que no se rehace, y las pulsaciones se atienden por delegación. Enganchar aquí
// dentro de `verComandaDeLaMesa()` acumularía un juego de oyentes por repaso, que es exactamente
// el fallo que tuvo el carrusel de «lo que más sale» y acabó pasando quince tarjetas de golpe.
$('#comanda-mesa')?.addEventListener('click', e => {
  const b = e.target.closest('[data-pagar]');
  if (!b) return;
  if (b.dataset.pagar === 'todo') pagar(true);
  else if (b.dataset.pagar === 'factura') abrirFactura();
  else abrirPago();
});

/** Elegir qué se paga: lo propio o la mesa entera. */
function abrirPago() {
  const d = cuentaDeLaMesa;
  if (!d || d.saldo_cent <= 0) return;
  const mio = d.mio && !d.mio.pagado ? d.mio : null;
  $('#pg-mesa').textContent = d.mesa || '';
  $('#pg-saldo').textContent = euro(d.saldo_cent);
  // «Lo mío» solo se ofrece si hay platos a su nombre: sin eso no hay cifra que poner en el
  // botón, y un botón de pagar sin importe es una firma en blanco.
  const caja = $('#pg-opciones');
  caja.innerHTML = mio
    ? `<label class="opcion-pago"><input type="radio" name="pg" value="mio" checked>
         <span><b>Lo mío · ${euro(mio.a_pagar_cent)}</b>
         <small class="tenue">${euro(mio.suyo_cent)} de lo que pediste${mio.compartido_cent
            ? ` + ${euro(mio.compartido_cent)} de lo que comparte la mesa` : ''}</small></span></label>
       <label class="opcion-pago"><input type="radio" name="pg" value="todo">
         <span><b>Toda la mesa · ${euro(d.saldo_cent)}</b>
         <small class="tenue">Invitas tú</small></span></label>`
    : `<p class="tenue">Lo que has tomado no está apuntado a tu nombre, así que no puedo decirte
         cuánto es «lo tuyo». Puedes pagar la cuenta entera, o pedirle al camarero que la reparta.</p>
       <label class="opcion-pago"><input type="radio" name="pg" value="todo" checked>
         <span><b>Toda la mesa · ${euro(d.saldo_cent)}</b></span></label>`;
  // Con «factúrame siempre» puesto en el perfil, la factura sale con el propio pago: preguntarlo
  // otra vez aquí sería hacerle repetir algo que ya dijo.
  const sola = Boolean(cuenta && cuenta.factura_auto && cuenta.nif);
  $('#pg-factura').checked = false;
  $('#pg-factura-campo').hidden = sola;
  $('#pg-factura-auto').hidden = !sola;
  $('#pg-hecho').hidden = true;
  $('#pg-elegir').hidden = false;
  $('#d-pagar').showModal();
}

// La clave del pago se inventa UNA vez, al abrir el diálogo de confirmación, y se reutiliza en
// cada reintento: es lo que convierte «no me ha llegado la respuesta» en algo inofensivo. Si se
// inventara por intento, dos toques con mal wifi serían dos cobros. El middleware del servidor
// (`Idempotency-Key`) devuelve la respuesta del primero y no cobra de nuevo.
let claveDelPago = null;

async function pagar(todo) {
  const boton = $('#pg-pagar');
  if (boton) boton.disabled = true;
  claveDelPago = claveDelPago || uuidPago();
  const queria = $('#pg-factura').checked && !$('#pg-factura-campo').hidden;
  try {
    const r = await api('/publico/visita/pagar',
      { method: 'POST', body: { todo: !!todo, con_compartido: true }, clave: claveDelPago });
    claveDelPago = null;                   // pago cerrado: el siguiente lleva clave nueva
    $('#pg-elegir').hidden = true;
    $('#pg-hecho').hidden = false;
    $('#pg-importe').textContent = euro(r.importe_cent);
    $('#pg-resto').textContent = r.cuenta_saldada
      ? 'La cuenta de la mesa queda saldada.'
      : `La mesa debe todavía ${euro(r.saldo_cent)}.`;
    if (!$('#d-pagar').open) $('#d-pagar').showModal();
    aviso('Pagado ' + euro(r.importe_cent), 'ok');
    verComandaDeLaMesa();
    // El pago ya está hecho y apuntado. Lo de la factura viene DESPUÉS y por separado a propósito:
    // si fallara, lo que hay que ver es «tu pago está hecho, la factura no ha salido», nunca un
    // error que parezca que no se ha cobrado.
    if (r.factura) pintarFactura(r.factura, true);
    else if (queria) abrirFactura(true);
  } catch (e) {
    // Un fallo de red NO invalida la clave: puede que el cobro haya entrado y se haya perdido
    // la respuesta, y reintentar con la misma clave es justo lo que averigua cuál de las dos fue.
    if (!e.red) claveDelPago = null;
    aviso(e.message, 'error');
  } finally {
    if (boton) boton.disabled = false;
  }
}

// `crypto.randomUUID` solo existe en contexto seguro. Producción va por HTTPS y lo tiene, pero el
// sitio de pruebas de la LAN (:8093) va por HTTP pelado: allí sería `undefined` y el pago se
// quedaría sin clave —sin red de seguridad— justo donde se prueba. De ahí el respaldo.
const uuidPago = () => (crypto.randomUUID ? crypto.randomUUID()
  : 'p-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10));

$('#pg-pagar').onclick = () => {
  const cual = document.querySelector('input[name="pg"]:checked');
  pagar(cual && cual.value === 'todo');
};
$('#pg-cerrar').onclick = () => { $('#d-pagar').close(); claveDelPago = null; };
$('#pg-listo').onclick = () => $('#d-pagar').close();

// ── La factura ──────────────────────────────────────────────────────────────────────────
// De qué es la factura NO lo decide esta pantalla. Lo dice el servidor en `alcance_sugerido`:
// «mio» si la persona ha pagado su parte, «mesa» si la cuenta está saldada del todo y nadie ha
// sacado ya una por cabeza. Repetir esa lógica aquí sería tener dos reglas de una serie fiscal, y
// la que se queda vieja es siempre la del navegador.
//
// Y una cosa que esta pantalla no hace: quemar un número de factura sin saber qué imprimir. Con
// los datos fiscales en el perfil se pide sola; sin ellos se pregunta primero, porque una
// simplificada emitida ya no se puede convertir en completa —hay que rectificarla— y quien marcó
// «quiero factura» casi siempre la quiere con su NIF.
const diaYhora = s => (s ? new Date(s).toLocaleString('es-ES',
  { dateStyle: 'short', timeStyle: 'short' }) : '');

function datosFiscalesDelPerfil() {
  return {
    nif: (cuenta && cuenta.nif) || '',
    nombre: (cuenta && (cuenta.razon_social || cuenta.nombre)) || '',
    direccion: (cuenta && cuenta.direccion) || '',
  };
}

/** El documento, tal y como lo devuelve el servidor. */
function pintarFactura(f, abrir = false) {
  const d = $('#d-factura');
  $('#fa-datos').hidden = true;
  $('#fa-pedir').hidden = true;
  const fila = (cant, texto, importe, clase = '') => `<div class="fa-linea ${clase}">
      <span class="cant">${cant}</span><span>${texto}</span>
      <span class="importe">${euro(importe)}</span></div>`;
  $('#fa-cuerpo').innerHTML = `<div class="factura">
    <p class="estado-grande aceptada">${esc(f.numero_completo)}</p>
    <p class="fa-pie">${esc(f.local.nombre)} · NIF ${esc(f.local.nif)}<br>
      ${esc(f.local.direccion || '')}</p>
    ${f.cliente_nif ? `<p class="fa-quien"><b>${esc(f.cliente_nombre || '')}</b><br>
        NIF ${esc(f.cliente_nif)}${f.cliente_direccion ? '<br>' + esc(f.cliente_direccion) : ''}</p>`
      : '<p class="fa-quien tenue">Factura simplificada, sin datos de cliente.</p>'}
    ${(f.lineas || []).map(l => fila(l.cantidad, esc(l.producto), l.importe_cent)).join('')}
    ${fila('', 'Base', f.base_cent)}
    ${fila('', `IVA ${f.iva_pct}%`, f.iva_cent)}
    ${fila('', '<b>Total</b>', f.total_cent, 'fa-total')}
    <p class="fa-pie">${f.alcance === 'mesa' ? 'De la cuenta entera' : 'De lo que pagaste tú'}${
      f.mesa ? ' · mesa ' + esc(f.mesa) : ''}<br>
      Expedida el ${esc(diaYhora(f.emitida_en))}${f.fuera_de_fecha
        ? `<br>Operación del ${esc(diaYhora(f.operacion_en))}` : ''}</p>
  </div>`;
  if (abrir && !d.open) d.showModal();
}

/** Qué hay de la factura de esta mesa: la que ya existe, la que se puede pedir, o a quién pedirla. */
async function abrirFactura(pedirYa = false) {
  const d = $('#d-factura');
  $('#fa-cuerpo').innerHTML = '<p class="tenue">Un momento…</p>';
  $('#fa-datos').hidden = true;
  $('#fa-pedir').hidden = true;
  if (!d.open) d.showModal();
  let e;
  try { e = await api('/publico/visita/factura'); }
  catch (err) { $('#fa-cuerpo').innerHTML = `<p class="rechazada">${esc(err.message)}</p>`; return; }

  const ya = e.mia || e.de_la_mesa;
  if (ya) return pintarFactura(ya);
  if (!e.puedo_pedirla) {
    // Aquí es donde NO se dice «ya no se puede». Se dice a quién pedirla, porque el local está
    // obligado a expedirla cuando el cliente la pide, aunque la caja del día ya esté cerrada.
    const plazo = e.plazo || {};
    $('#fa-cuerpo').innerHTML = `
      <p>${esc(plazo.motivo || 'Desde la app no se puede emitir ahora')}.</p>
      ${plazo.como_pedirla ? `<p class="estado-grande">${esc(plazo.como_pedirla)}</p>
        <p class="tenue">Están obligados a hacértela si la pides: el plazo de facturación no
          termina cuando cierra la caja.</p>` : ''}
      ${e.por_cabeza ? `<p class="tenue">En esta mesa ya hay ${e.por_cabeza} factura(s) de quien
        pagó su parte, así que no puede hacerse además una de la cuenta entera.</p>` : ''}`;
    return;
  }

  const perfil = datosFiscalesDelPerfil();
  $('#fa-nif').value = perfil.nif;
  $('#fa-nombre').value = perfil.nombre;
  $('#fa-direccion').value = perfil.direccion;
  if (pedirYa && perfil.nif && perfil.nombre) return pedirLaFactura(e.alcance_sugerido);
  $('#fa-cuerpo').innerHTML = `<p>Se hará la factura de <b>${e.alcance_sugerido === 'mesa'
    ? 'la cuenta entera' : 'lo que has pagado tú'}</b>.</p>`;
  $('#fa-datos').hidden = false;
  $('#fa-pedir').hidden = false;
  $('#fa-pedir').dataset.alcance = e.alcance_sugerido || 'mio';
}

async function pedirLaFactura(alcance) {
  const boton = $('#fa-pedir');
  boton.disabled = true;
  try {
    const f = await api('/publico/visita/factura', { method: 'POST', body: {
      alcance: alcance || 'mio',
      nif: $('#fa-nif').value.trim() || null,
      nombre: $('#fa-nombre').value.trim() || null,
      direccion: $('#fa-direccion').value.trim() || null,
    }});
    pintarFactura(f, true);
    aviso('Factura ' + f.numero_completo, 'ok');
  } catch (err) {
    // El mensaje del servidor ya trae el teléfono y el correo cuando toca pedirla al local, así
    // que se muestra tal cual en vez de traducirlo a un «no se ha podido» que no dice nada.
    $('#fa-cuerpo').innerHTML = `<p class="rechazada">${esc(err.message)}</p>`;
    $('#fa-datos').hidden = true;
    boton.hidden = true;
  } finally { boton.disabled = false; }
}

/** Las facturas de la cuenta de cliente. Las suyas: se filtran por cuenta, no por NIF. */
async function verMisFacturas() {
  const d = $('#d-factura');
  $('#fa-datos').hidden = true;
  $('#fa-pedir').hidden = true;
  $('#fa-cuerpo').innerHTML = '<p class="tenue">Un momento…</p>';
  if (!d.open) d.showModal();
  let lista;
  try { lista = await api('/publico/clientes/facturas'); }
  catch (e) { $('#fa-cuerpo').innerHTML = `<p class="rechazada">${esc(e.message)}</p>`; return; }
  misFacturas = lista;
  $('#fa-cuerpo').innerHTML = lista.length
    ? `<div class="lista-facturas">${lista.map((f, i) => `<button data-factura="${i}">
         <span>${esc(f.numero_completo)} · ${esc(diaYhora(f.emitida_en))}</span>
         <span class="importe">${euro(f.total_cent)}</span></button>`).join('')}</div>`
    : `<p class="tenue">Todavía no tienes ninguna. Las que pidas desde la app se guardan aquí,
         y también las que salgan solas si dejas puesta la factura automática.</p>`;
}

// El listado ya trae cada factura entera, así que abrir una no vuelve a preguntar al servidor.
let misFacturas = [];
$('#fa-cuerpo').addEventListener('click', e => {
  const b = e.target.closest('[data-factura]');
  if (b) pintarFactura(misFacturas[+b.dataset.factura]);
});
$('#fa-pedir').onclick = () => pedirLaFactura($('#fa-pedir').dataset.alcance);
$('#fa-cerrar').onclick = () => $('#d-factura').close();

// ── Seguimiento de la propia comanda ──
const TEXTO = {
  pendiente: 'Esperando a que un camarero la confirme',
  aceptada: 'Confirmada y en marcha',
  rechazada: 'No se ha podido aceptar. Avisa a un camarero',
};
const COCINA = { enviada: 'en cola', preparando: 'cocinándose', lista: 'lista', servida: 'servida' };

async function verEstado(id) {
  try {
    const s = await api('/publico/solicitudes/' + id);
    $('#e-titulo').textContent = `Comanda #${s.id}${s.mesa ? ' · mesa ' + s.mesa : ''}`;
    const cocina = s.cocina
      ? Object.entries(s.cocina).map(([e, n]) => `${n} ${COCINA[e] || e}`).join(' · ')
      : '';
    $('#e-cuerpo').innerHTML = `
      <p class="estado-grande ${esc(s.estado)}">${esc(TEXTO[s.estado] || s.estado)}</p>
      ${cocina ? `<p class="tenue">En cocina: ${esc(cocina)}</p>` : ''}
      ${s.lineas.map(l => `<div class="linea-cesta"><span class="cant">${l.cantidad}</span>
          <span class="nombre">${esc(l.nombre)}</span>
          <span class="importe">${euro(l.cantidad * l.precio_cent)}</span></div>`).join('')}
      <div class="fila total-cesta"><span>Total</span><b>${euro(s.total_cent)}</b></div>`;
    if (!$('#d-estado').open) $('#d-estado').showModal();
  } catch (e) { aviso(e.message, 'error'); }
}
$('#e-cerrar').onclick = () => $('#d-estado').close();

// ── La tira de seguimiento: el estado de la comanda propia, siempre a la vista ──
// Cinco pasos: enviada → confirmada (un camarero la ha aceptado) → en cocina → lista → servida.
// Se refresca sola: el canal público del servidor avisa de «algo ha cambiado» (sin datos, por
// privacidad) y, por si un aviso se pierde, cada 15 s se vuelve a preguntar.
const PASOS = ['enviada', 'confirmada', 'cocina', 'lista', 'servida'];
let comandaSeguida = null, temporizadorSeguimiento = null, wsPublico = null;

function pasoDe(s) {
  if (s.estado === 'rechazada') return { paso: 'enviada', rechazada: true, texto: TEXTO.rechazada };
  if (s.estado === 'pendiente') return { paso: 'enviada', texto: TEXTO.pendiente };
  const c = s.cocina || {};
  const n = k => c[k] || 0;
  const enCocina = n('enviada') + n('preparando') + n('lista') + n('servida');
  if (!enCocina) return { paso: 'confirmada', texto: 'Confirmada · el camarero la está pasando a cocina' };
  if (n('enviada') + n('preparando') + n('lista') === 0) return { paso: 'servida', texto: 'Todo servido · ¡que aproveche!' };
  if (n('enviada') + n('preparando') === 0) return { paso: 'lista', texto: 'Lista en el pase · te la llevan ahora' };
  const partes = [];
  if (n('preparando')) partes.push(`${n('preparando')} cocinándose`);
  if (n('enviada')) partes.push(`${n('enviada')} en cola`);
  if (n('lista')) partes.push(`${n('lista')} ya lista`);
  if (n('servida')) partes.push(`${n('servida')} servida`);
  return { paso: 'cocina', texto: 'En cocina · ' + partes.join(' · ') };
}

function pintarSeguimiento(s) {
  const tira = $('#mi-comanda');
  const { paso, texto, rechazada } = pasoDe(s);
  tira.hidden = false;
  tira.classList.toggle('rechazada', !!rechazada);
  tira.classList.toggle('servida', paso === 'servida');
  $('#mc-titulo').textContent = `Comanda #${s.id}${s.mesa ? ' · mesa ' + s.mesa : ''} · ${euro(s.total_cent)}`;
  $('#mc-texto').textContent = texto;
  const hasta = PASOS.indexOf(paso);
  tira.querySelectorAll('[data-paso]').forEach(li => {
    const i = PASOS.indexOf(li.dataset.paso);
    li.classList.toggle('hecho', i < hasta);
    li.classList.toggle('actual', i === hasta);
  });
}

async function refrescarSeguimiento() {
  // La cuenta de la mesa se vuelve a mirar SIEMPRE, antes del `return` de abajo. Estaba dentro
  // del seguimiento de la comanda propia, y por eso un móvil que no había pedido nada desde aquí
  // —al que le apuntó el camarero, o el que solo picó del centro— no se enteraba nunca de nada:
  // ni de que le habían servido, ni de que otro de la mesa acababa de pagar. Y con el pago desde
  // la app eso ya no es un detalle estético: dos personas podrían ir a pagar lo mismo porque una
  // no ve que la otra ya lo hizo.
  verComandaDeLaMesa();
  if (!comandaSeguida) return;
  try {
    const s = await api('/publico/solicitudes/' + comandaSeguida);
    pintarSeguimiento(s);
    if ($('#d-estado').open) verEstado(comandaSeguida);
  } catch (e) {
    if (e.estado === 404) dejarDeSeguir();          // la comanda ya no existe: fuera la tira
  }
}

function escucharCanalPublico() {
  if (wsPublico) return;
  const abrir = () => {
    wsPublico = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/publico');
    wsPublico.onmessage = () => refrescarSeguimiento();     // el aviso no trae datos: se vuelve a mirar
    wsPublico.onclose = () => setTimeout(abrir, 3000);
  };
  abrir();
}

/** Enciende el repaso periódico si no estaba ya. Uno solo, aunque se pida varias veces. */
function arrancarRepaso() {
  escucharCanalPublico();
  if (!temporizadorSeguimiento) temporizadorSeguimiento = setInterval(refrescarSeguimiento, 15000);
}

function seguirComanda(id) {
  comandaSeguida = id;
  try { localStorage.setItem(LLAVE_COMANDA, String(id)); } catch {}
  refrescarSeguimiento();
  arrancarRepaso();
}

function dejarDeSeguir() {
  comandaSeguida = null;
  try { localStorage.removeItem(LLAVE_COMANDA); } catch {}
  $('#mi-comanda').hidden = true;
  // El reloj NO se para si seguimos sentados en una mesa: dejar de seguir la comanda propia es
  // dejar de mirar la tira de pasos, no desentenderse de la cuenta que hay que pagar.
  if (!(typeof tokenVisita === 'function' && tokenVisita())) {
    clearInterval(temporizadorSeguimiento);
    temporizadorSeguimiento = null;
  }
}

$('#mc-detalle').onclick = () => comandaSeguida && verEstado(comandaSeguida);
$('#mc-pasos').onclick = () => comandaSeguida && verEstado(comandaSeguida);
$('#mc-olvidar').onclick = dejarDeSeguir;

// Si ya hay una comanda enviada desde este teléfono, se sigue desde el primer momento
const mia = localStorage.getItem(LLAVE_COMANDA);
if (mia) seguirComanda(+mia);

// Estar sentado en una mesa ya es motivo para escuchar, aunque este teléfono no haya pedido nada:
// su cuenta la puede mover el camarero desde el TPV o cualquier otro móvil de la mesa. Antes el
// canal público y el repaso periódico solo se encendían al enviar una comanda, así que quien no
// pedía se quedaba mirando una pantalla congelada. El repaso es el de siempre (15 s), por si se
// pierde un aviso del socket.
if (typeof tokenVisita === 'function' && tokenVisita()) arrancarRepaso();

cargar();
setInterval(cargar, 60000);        // por si cambia la carta o se agota algo
