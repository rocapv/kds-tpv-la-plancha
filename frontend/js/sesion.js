// Sesión compartida por todas las pantallas: el PIN se teclea una vez y a partir de ahí
// cada petición lleva el token. El token vive en localStorage, así que aguanta recargas
// y se comparte entre pestañas de la misma pantalla.
const LLAVE_SESION = 'kds_sesion';
let sesion = null;
try { sesion = JSON.parse(localStorage.getItem(LLAVE_SESION) || 'null'); } catch { sesion = null; }

const tokenActual = () => sesion?.token || null;

function guardarSesion(s) {
  sesion = s;
  try { localStorage.setItem(LLAVE_SESION, JSON.stringify(s)); } catch {}
}
function borrarSesion() {
  sesion = null;
  try { localStorage.removeItem(LLAVE_SESION); } catch {}
}

async function salir() {
  // Salir cierra la sesión de verdad: el PIN hay que volver a teclearlo. Como casi siempre lo
  // que se quiere es volver al menú, se pregunta antes (y al lado hay un «◀ Menú» que no cierra).
  if (!confirm('¿Cerrar la sesión? Habrá que volver a teclear el PIN. Si solo quieres volver al menú, usa «◀ Menú».')) return;
  try { await api('/logout', { method: 'POST' }); } catch {}
  borrarSesion();
  location.href = '/';
}

const PANTALLA = (location.pathname.split('/').pop() || 'index.html');

/** El puesto del plano manda: quien está en la placa térmica trabaja de cocina aunque
 *  su ficha diga camarero. El rol real solo se usa para la gestión. */
const rolEfectivo = yo => yo.rol_operativo || yo.rol;
const puedeEstarAqui = yo => !yo.guis?.length || yo.guis.includes(PANTALLA);

/** Garantiza una sesión válida con uno de los roles pedidos. Devuelve el empleado. */
async function exigirSesion(roles = []) {
  while (true) {
    if (tokenActual()) {
      try {
        const yo = await api('/yo');
        const vale = !roles.length
          || roles.includes(rolEfectivo(yo))
          || (yo.rol === 'encargado' && roles.includes('encargado'));
        if (vale && puedeEstarAqui(yo)) { pintarBarraSesion(yo); vigilarPuesto(yo); return yo; }
        if (vale && !puedeEstarAqui(yo)) return mandarASuPuesto(yo);
        await pedirPin(`Esta pantalla es para ${roles.join(' o ')}. ${yo.nombre} trabaja de ${rolEfectivo(yo) || 'nada'}${yo.puesto_nombre ? ' en ' + yo.puesto_nombre : ''}.`);
        continue;
      } catch (e) {
        borrarSesion();
      }
    }
    await pedirPin();
  }
}

/** Manda a cada uno a la pantalla de su puesto. Devuelve una promesa que no se resuelve:
 *  la página se está yendo y nadie debe seguir pintando encima. */
function mandarASuPuesto(yo) {
  const destino = yo.gui || 'index.html';
  if (destino.split('?')[0] === PANTALLA) return new Promise(() => {});   // evita el bucle
  aviso(`${yo.nombre}: tu puesto es ${yo.puesto_nombre || 'el menú'}`, 'info');
  setTimeout(() => location.href = '/' + destino, 1200);
  return new Promise(() => {});
}

/** Si el encargado mueve mi ficha en el plano, esta pantalla se entera y se recoloca sola. */
function vigilarPuesto(yo) {
  window.addEventListener('evento-ws', async e => {
    if (e.detail?.tipo !== 'plantilla' || e.detail.empleado_id !== yo.id) return;
    const ahora = await api('/yo').catch(() => null);
    if (!ahora) return;
    if (!puedeEstarAqui(ahora)) mandarASuPuesto(ahora);
    else aviso(`Ahora estás en ${ahora.puesto_nombre || 'ningún puesto'}`, 'info');
  });
}

/** Panel de PIN a pantalla completa. Se resuelve cuando el PIN es correcto. */
function pedirPin(mensaje = '') {
  return new Promise(resolve => {
    document.querySelector('#panel-pin')?.remove();
    let pin = '';
    const caja = document.createElement('div');
    caja.id = 'panel-pin';
    caja.className = 'visor';
    caja.innerHTML = `
      <div class="pin">
        <h2>Introduce tu PIN</h2>
        ${mensaje ? `<p class="aviso-rol">${esc(mensaje)}</p>` : ''}
        <div class="pantalla" id="pin-pantalla">····</div>
        <div class="teclado" id="teclado"></div>
      </div>`;
    document.body.appendChild(caja);

    const pantalla = caja.querySelector('#pin-pantalla');
    const pintar = () => pantalla.textContent = '•'.repeat(pin.length) + '·'.repeat(4 - pin.length);
    const teclado = caja.querySelector('#teclado');
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 'C', 0, '⌫'].forEach(k => {
      const b = document.createElement('button');
      b.textContent = k;
      b.onclick = () => pulsar(String(k));
      teclado.appendChild(b);
    });

    async function validar() {
      if (pin.length !== 4) return;
      try {
        guardarSesion(await api('/login', { method: 'POST', body: { pin } }));
        document.removeEventListener('keydown', porTeclado);
        caja.remove();
        resolve(sesion);
      } catch (e) {
        aviso(e.message, 'error');
        pantalla.classList.add('mal');
        setTimeout(() => { pantalla.classList.remove('mal'); pin = ''; pintar(); }, 600);
      }
    }
    async function pulsar(k) {
      if (k === 'C') { pin = ''; return pintar(); }
      if (k === '⌫') { pin = pin.slice(0, -1); return pintar(); }
      if (pin.length >= 4) return;
      pin += k;
      pintar();
      if (pin.length === 4) { await new Promise(r => setTimeout(r, 120)); validar(); }
    }
    function porTeclado(e) {
      if (/^[0-9]$/.test(e.key)) pulsar(e.key);
      else if (e.key === 'Backspace') pulsar('⌫');
      else if (e.key === 'Enter') validar();
      else if (e.key === 'Escape') pulsar('C');
    }
    document.addEventListener('keydown', porTeclado);
    pintar();
  });
}

/** Pone «Nombre (rol)», los mandos de la simulación y el botón de salir en la barra superior. */
function pintarBarraSesion(yo) {
  const barra = document.querySelector('header.barra');
  if (!barra || barra.querySelector('.sesion')) return;
  const hueco = barra.querySelector('.hueco') || barra;
  const span = document.createElement('span');
  span.className = 'sesion tenue';
  span.textContent = yo.puesto_nombre ? `${yo.nombre} · ${yo.puesto_nombre}` : `${yo.nombre} (${yo.rol})`;
  span.title = `Rol ${yo.rol}${yo.rol_operativo && yo.rol_operativo !== yo.rol ? ` · en este puesto trabaja de ${yo.rol_operativo}` : ''}`;
  const boton = document.createElement('button');
  boton.textContent = 'Salir';
  boton.onclick = salir;
  hueco.after(span, mandosSimulacion(yo), boton);
  ponerVolverAlMenu(barra);
}

/** Toda pantalla tiene que poder volver al menú sin cerrar la sesión. Las que ya traen su
 *  «◀ Menú» escrito en el HTML se quedan como están. */
function ponerVolverAlMenu(barra) {
  if (PANTALLA === 'index.html' || barra.querySelector('[data-menu]')) return;
  if ([...barra.querySelectorAll('a')].some(a => a.getAttribute('href') === '/')) return;
  const enlace = document.createElement('a');
  enlace.href = '/';
  enlace.dataset.menu = '1';
  enlace.innerHTML = '<button title="Volver al menú principal sin cerrar la sesión">◀ Menú</button>';
  barra.prepend(enlace);
}

// ── Simulación de actividad ──
// Genera servicio falso (comandas, cocina y cobros) para enseñar el sistema en marcha.
// Solo la ve el encargado: es quien puede responder de los datos que entran.
function mandosSimulacion(yo) {
  const caja = document.createElement('span');
  caja.className = 'simulacion';
  if (yo.rol !== 'encargado') return caja;
  caja.innerHTML = `
    <button data-sim="play"  title="Simular actividad">▶</button>
    <button data-sim="pause" title="Pausar la simulación">⏸</button>
    <button data-sim="reset" title="Parar y borrar lo que ha creado la simulación">⟲</button>
    <span class="sim-estado tenue"></span>`;

  const pintar = s => {
    caja.dataset.estado = s.estado;
    caja.querySelectorAll('[data-sim]').forEach(b => {
      b.classList.toggle('activo', (b.dataset.sim === 'play' && s.estado === 'corriendo')
                                || (b.dataset.sim === 'pause' && s.estado === 'pausado'));
    });
    caja.querySelector('.sim-estado').textContent =
      s.estado === 'parado' ? '' : `${s.estado} · ${s.pedidos} pedidos, ${s.cobrados} cobrados`;
  };

  caja.querySelectorAll('[data-sim]').forEach(b => b.onclick = async () => {
    const accion = b.dataset.sim;
    if (accion === 'reset' && !confirm('Reset: para la simulación y borra los pedidos que ha creado. ¿Seguir?')) return;
    try {
      const r = await api('/simulacion/' + accion, { method: 'POST' });
      pintar(r);
      aviso(accion === 'reset' ? `Simulación reiniciada · ${r.borrados} pedidos borrados`
            : accion === 'play' ? 'Simulación en marcha' : 'Simulación en pausa',
            accion === 'play' ? 'ok' : 'info');
    } catch (e) { aviso(e.message, 'error'); }
  });

  api('/simulacion').then(pintar).catch(() => {});
  window.addEventListener('evento-ws', e => { if (e.detail?.tipo === 'simulacion') pintar(e.detail); });
  return caja;
}
