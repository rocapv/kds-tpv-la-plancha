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

// Destacados: una pila de tarjetas que se pasa con el dedo. La de arriba se puede pedir.
function pintarDestacados() {
  const caja = $('#destacados');
  if (!destacados.length) { caja.hidden = true; return; }
  caja.hidden = false;
  $('#pila').innerHTML = destacados.map((d, i) => `
    <article class="tarjeta" data-i="${i}" style="--color:${esc(d.color || '#e67e22')}">
      ${d.foto ? `<img src="${esc(d.foto)}" alt="" loading="lazy">` : '<div class="sin-foto"></div>'}
      <div class="texto">
        <small>${esc(d.categoria)}</small>
        <b>${esc(d.nombre)}</b>
        <span class="precio">${euro(d.precio_cent)}</span>
      </div>
      <button class="pedir" data-pedir="${d.id}">Añadir</button>
    </article>`).join('');
  colocarPila();
  $('#pila').querySelectorAll('[data-pedir]').forEach(b => b.onclick = e => {
    e.stopPropagation();
    anadir(+b.dataset.pedir, b);
  });
  // gesto: arrastrar la de arriba pasa a la siguiente
  let x0 = null;
  $('#pila').addEventListener('pointerdown', e => x0 = e.clientX);
  $('#pila').addEventListener('pointerup', e => {
    if (x0 === null) return;
    const dx = e.clientX - x0;
    x0 = null;
    if (Math.abs(dx) > 40) girar(dx < 0 ? 1 : -1);
  });
}

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
  const cuerpo = {
    mesa_id: $('#c-mesa').value ? +$('#c-mesa').value : null,
    cliente: $('#c-nombre').value.trim() || null,
    nota: $('#c-nota').value.trim() || null,
    lineas: cesta.map(l => ({ producto_id: l.producto_id, cantidad: l.cantidad })),
  };
  try {
    const r = await api('/publico/solicitudes', { method: 'POST', body: cuerpo });
    cesta = []; guardarCesta(); pintarCesta();
    $('#d-cesta').close();
    aviso('Comanda enviada · la confirma un camarero', 'ok');
    seguirComanda(r.id);
    $('#mi-comanda').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (e) { aviso(e.message, 'error'); }
};

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
