// Carta en el móvil del cliente. Sin PIN y sin sesión: solo la carta, la cesta y el estado
// de la propia comanda. Nada de lo que se pulse aquí llega a cocina por sí solo: entra en una
// bandeja y un camarero la acepta, igual que si el cliente levantara la mano.
const mesaDelQR = new URLSearchParams(location.search).get('mesa');   // …/cliente.html?mesa=3
const LLAVE_CESTA = 'kds_cesta';
const LLAVE_COMANDA = 'kds_mi_comanda';

let carta = [], catActiva = null, cesta = [], local = {};
try { cesta = JSON.parse(localStorage.getItem(LLAVE_CESTA) || '[]'); } catch { cesta = []; }

const guardarCesta = () => { try { localStorage.setItem(LLAVE_CESTA, JSON.stringify(cesta)); } catch {} };
const totalCesta = () => cesta.reduce((s, l) => s + l.cantidad * l.precio_cent, 0);

// ── Carta ──
async function cargar() {
  [local, carta] = await Promise.all([api('/publico/local'), api('/publico/carta')]);
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
            ${p.alergenos ? `<small class="alerg">⚠ ${esc(p.alergenos)}</small>` : ''}
            ${p.disponible ? '' : '<small class="tenue">hoy no queda</small>'}
          </div>
          <div class="precio">${euro(p.precio_cent)}</div>
          ${p.disponible ? `<button class="sumar" data-p="${p.id}" aria-label="Añadir ${esc(p.nombre)}">+</button>` : ''}
        </article>`).join('')}
    </section>`).join('');
  $('#carta').querySelectorAll('[data-p]').forEach(b => b.onclick = () => anadir(+b.dataset.p, b));
}

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
    try { localStorage.setItem(LLAVE_COMANDA, String(r.id)); } catch {}
    $('#d-cesta').close();
    aviso('Comanda enviada · la confirma un camarero', 'ok');
    verEstado(r.id);
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

// Si ya hay una comanda enviada desde este teléfono, se ofrece seguirla
const mia = localStorage.getItem(LLAVE_COMANDA);
if (mia) {
  const b = document.createElement('button');
  b.className = 'seguir';
  b.textContent = 'Ver mi comanda';
  b.onclick = () => verEstado(+mia);
  document.querySelector('.barra-cliente .hueco').after(b);
  setInterval(() => { if ($('#d-estado').open) verEstado(+mia); }, 10000);
}

cargar();
setInterval(cargar, 60000);        // por si cambia la carta o se agota algo
