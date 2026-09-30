// Carta en el móvil del cliente. Sin PIN y sin sesión: solo la carta, la cesta y el estado
// de la propia comanda. Nada de lo que se pulse aquí llega a cocina por sí solo: entra en una
// bandeja y un camarero la acepta, igual que si el cliente levantara la mano.
const mesaDelQR = new URLSearchParams(location.search).get('mesa');   // …/cliente.html?mesa=3
const LLAVE_CESTA = 'kds_cesta';
const LLAVE_COMANDA = 'kds_mi_comanda';

let carta = [], catActiva = null, cesta = [], local = {};
let alergenos = [], destacados = [], destacado = 0;
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
  caja.innerHTML = `
    <div class="cab"><b>Tu mesa ${esc(d.mesa)}</b>
      <span class="tenue">${euro(d.total_cent)}${d.pagado_cent ? ' · pagado ' + euro(d.pagado_cent) : ''}</span></div>
    ${d.lineas.map(fila).join('')}
    ${d.esperando.map(s => `<p class="esperando">⏳ ${s.lineas.map(l => `${l.cantidad}× ${esc(l.nombre)}`).join(', ')}
        <small>${esc(s.motivo_retencion || 'esperando confirmación')}</small></p>`).join('')}
    ${d.rechazadas.map(r => `<p class="rechazada">✕ No ha podido ser${r.motivo_rechazo ? ': ' + esc(r.motivo_rechazo) : ''}</p>`).join('')}`;
}

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
  if (!comandaSeguida) return;
  try {
    const s = await api('/publico/solicitudes/' + comandaSeguida);
    verComandaDeLaMesa();
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

function seguirComanda(id) {
  comandaSeguida = id;
  try { localStorage.setItem(LLAVE_COMANDA, String(id)); } catch {}
  refrescarSeguimiento();
  escucharCanalPublico();
  clearInterval(temporizadorSeguimiento);
  temporizadorSeguimiento = setInterval(refrescarSeguimiento, 15000);
}

function dejarDeSeguir() {
  comandaSeguida = null;
  try { localStorage.removeItem(LLAVE_COMANDA); } catch {}
  clearInterval(temporizadorSeguimiento);
  $('#mi-comanda').hidden = true;
}

$('#mc-detalle').onclick = () => comandaSeguida && verEstado(comandaSeguida);
$('#mc-pasos').onclick = () => comandaSeguida && verEstado(comandaSeguida);
$('#mc-olvidar').onclick = dejarDeSeguir;

// Si ya hay una comanda enviada desde este teléfono, se sigue desde el primer momento
const mia = localStorage.getItem(LLAVE_COMANDA);
if (mia) seguirComanda(+mia);

cargar();
setInterval(cargar, 60000);        // por si cambia la carta o se agota algo
