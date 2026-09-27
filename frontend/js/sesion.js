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
        // Sesión buena pero pantalla que no le toca: NO se pide PIN. Pedirlo invitaría a
        // buscar el de otra persona; se le devuelve al menú, que ya solo enseña lo suyo.
        return alMenu(yo, `Esta pantalla es para ${roles.join(' o ')}; ${yo.nombre} trabaja de ${rolEfectivo(yo) || 'nada'}${yo.puesto_nombre ? ' en ' + yo.puesto_nombre : ''}.`);
      } catch (e) {
        // Sin servidor no se puede comprobar la sesión... pero tampoco se puede teclear el PIN,
        // que lo valida el servidor. Borrarla dejaría al camarero fuera justo cuando más falta
        // le hace la pantalla, así que se conserva y se reintenta. Solo un rechazo de verdad
        // (401: token caducado o cerrado por el encargado) cierra la sesión.
        if (e.red || e.estado === 503) {
          aviso('Sin conexión con el servidor: sigues con la sesión abierta en esta pantalla', 'error');
          await new Promise(r => setTimeout(r, 4000));
          continue;
        }
        borrarSesion();
      }
    }
    await pedirPin();
  }
}

/** Devuelve a alguien al menú principal cuando ha entrado donde no le toca.
 *  La promesa no se resuelve a propósito: la página se está yendo y nadie debe seguir pintando. */
function alMenu(yo, motivo) {
  aviso(motivo, 'error');
  if (PANTALLA === 'index.html') return Promise.resolve(yo);   // ya estamos en el menú
  setTimeout(() => location.href = '/index.html', 1600);
  return new Promise(() => {});
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
    await mirarAvisos();
    const ahora = await api('/yo').catch(() => null);
    if (!ahora) return;
    // Se avisa ANTES de mandarle a otra pantalla: si se le mueve la pantalla debajo de los pies
    // sin decirle nada, lo que ve es que el TPV «se ha vuelto loco».
    if (!puedeEstarAqui(ahora)) setTimeout(() => mandarASuPuesto(ahora), 2500);
  });
  mirarAvisos();
}

// ── Avisos que esperan: «te han cambiado de puesto» ───────────────────────────────────
// No es un mensajito de tres segundos: es una tira que se queda hasta que la persona dice
// «enterado». A quien mueven casi nunca está mirando la pantalla en ese instante.
async function mirarAvisos() {
  let lista = [];
  try { lista = await api('/mis-avisos'); } catch { return; }
  if (!lista.length) return;
  let caja = document.querySelector('#avisos-personales');
  if (!caja) {
    caja = document.createElement('div');
    caja.id = 'avisos-personales';
    document.body.appendChild(caja);
  }
  caja.innerHTML = lista.map(a => `
    <div class="aviso-personal" data-aviso="${a.id}">
      <span class="ico">📣</span>
      <div>
        <b>${esc(a.texto)}</b>
        ${a.detalle ? `<small>${esc(a.detalle)}</small>` : ''}
      </div>
      <button class="primario" data-visto="${a.id}">Enterado</button>
    </div>`).join('');
  caja.querySelectorAll('[data-visto]').forEach(b => b.onclick = async () => {
    await api(`/mis-avisos/${b.dataset.visto}/visto`, { method: 'POST' }).catch(() => {});
    b.closest('.aviso-personal').remove();
    if (!caja.querySelector('.aviso-personal')) caja.remove();
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
        <details class="por-clave">
          <summary>Entrar con numero de empleado</summary>
          <div class="fila">
            <input id="acc-num" inputmode="numeric" placeholder="N.o de empleado" style="width:9em">
            <input id="acc-clave" type="password" placeholder="Contrasena" style="flex:1">
            <button id="acc-ok" class="primario">Entrar</button>
          </div>
        </details>
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
    // La otra puerta: numero de empleado y contrasena, para quien entra a la gestion desde
    // un teclado de verdad y no desde la pantalla tactil de barra.
    caja.querySelector('#acc-ok').onclick = async () => {
      const num = +caja.querySelector('#acc-num').value;
      const clave = caja.querySelector('#acc-clave').value;
      if (!num || clave.length < 6) return aviso('Numero de empleado y contrasena', 'error');
      try {
        guardarSesion(await api('/login', { method: 'POST', body: { empleado_id: num, contrasena: clave } }));
        document.removeEventListener('keydown', porTeclado);
        caja.remove();
        resolve(sesion);
      } catch (e) { aviso(e.message, 'error'); }
    };
    caja.querySelector('#acc-clave').onkeydown = e => {
      if (e.key === 'Enter') caja.querySelector('#acc-ok').click();
      e.stopPropagation();                      // que el teclado del PIN no se coma las teclas
    };
    caja.querySelector('#acc-num').onkeydown = e => e.stopPropagation();

    document.addEventListener('keydown', porTeclado);
    pintar();
  });
}

/** Pone «Nombre (rol)», los mandos de la simulación y el botón de salir en la barra superior. */
// ── Tema claro / oscuro, en TODAS las pantallas ────────────────────────────────────────
// Mecanismo tomado del «Faction Toggle» de jkantner (CodePen), rehecho con código propio: dos
// bandos con su etiqueta y un pomo que cruza. Los bandos aquí son el día y la noche de la
// estación; los emblemas de la Alianza y el Imperio son marcas de Lucasfilm y no pintan nada
// en un TPV. El tema se guarda por pantalla: la tableta de la barra y la de cocina pueden
// tener luces distintas, que no están en la misma sala.
const LLAVE_TEMA_APP = 'kds_tema_app';

function aplicarTemaApp(tema) {
  document.documentElement.dataset.tema = tema;
  try { localStorage.setItem(LLAVE_TEMA_APP, tema); } catch {}
  document.querySelectorAll('.faccion').forEach(b => b.setAttribute('aria-pressed', tema === 'claro'));
}

(function temaInicialApp() {
  let t = null;
  try { t = localStorage.getItem(LLAVE_TEMA_APP); } catch {}
  if (t !== 'claro' && t !== 'oscuro') t = 'oscuro';
  // Sin preferencia guardada, OSCURO. No se sigue al sistema a propósito: estas pantallas
  // viven en una cocina y en una barra con poca luz, y el portátil de quien la abra por
  // primera vez no sabe nada de eso. Quien quiera claro lo pulsa una vez y se recuerda.
  document.documentElement.dataset.tema = t;
})();

function interruptorTema() {
  const b = document.createElement('button');
  b.className = 'faccion';
  b.type = 'button';
  b.title = 'Cambiar entre pantalla oscura y clara';
  b.setAttribute('aria-pressed', document.documentElement.dataset.tema === 'claro');
  b.innerHTML = `
    <span class="lado noche">Noche</span>
    <span class="carril"><span class="pomo">
      <svg class="luna" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/></svg>
      <svg class="sol" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="12" r="5"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3M4 4l2 2M18 18l2 2M20 4l-2 2M6 18l-2 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
    </span></span>
    <span class="lado dia">Día</span>`;
  b.onclick = () => aplicarTemaApp(document.documentElement.dataset.tema === 'claro' ? 'oscuro' : 'claro');
  return b;
}

// ── Botón de tutorial: se carga solo cuando alguien lo pide ────────────────────────────
function botonTutorial() {
  const b = document.createElement('button');
  b.className = 'sutil';
  b.type = 'button';
  b.textContent = '?';
  b.title = 'Explicarme esta pantalla';
  b.style.minWidth = '40px';
  b.onclick = async () => {
    if (!window.tutorial) {
      await new Promise((ok, mal) => {
        const s = document.createElement('script');
        s.src = '/js/tutorial.js?v=' + Date.now();
        s.onload = ok; s.onerror = mal;
        document.head.appendChild(s);
      }).catch(() => aviso('No se ha podido cargar el tutorial', 'error'));
    }
    window.tutorial?.empezar(PANTALLA);
  };
  return b;
}

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
  hueco.after(span, mandosSimulacion(yo), botonTutorial(), interruptorTema(), boton);
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
  // Icono de tres barras desiguales, del pen «Star Wars Menu Icon» de Naito, rehecho en CSS.
  enlace.innerHTML = '<button title="Volver al menú principal sin cerrar la sesión">'
                   + '<span class="sables"><i></i><i></i><i></i></span> Menú</button>';
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
    const bots = s.bots || [];
    // Cada bot lleva su cronómetro: cambia de marcha cada pocos minutos y no coincide con los
    // demás. Se resume en la barra porque durante la demo es justo lo que hay que poder señalar:
    // «mira, ahora aprietan estos tres y descansan estos dos».
    const MARCHA = { fuerte: '▲ fuerte', flojo: '▼ flojo', apuro: '‼ apuro', espera: '⏸ espera' };
    const cuantos = s.marchas || {};
    const resumenMarchas = Object.entries(cuantos)
      .map(([m, n]) => `${n} ${(MARCHA[m] || m).split(' ')[1] || m}`).join(' · ');
    caja.querySelector('.sim-estado').textContent = s.estado === 'parado' ? ''
      : `${s.estado} · ${bots.length} bots${resumenMarchas ? ' (' + resumenMarchas + ')' : ''} · ${s.pedidos} pedidos, ${s.cobrados} cobrados`;
    // El detalle de quién está haciendo qué, sin ocupar sitio en la barra.
    caja.querySelector('.sim-estado').title = bots.map(b => {
      const m = MARCHA[b.marcha] || b.marcha || '';
      return b.tipo === 'sala'
        ? `${b.area}: ${b.empleado} · ${m} · ${b.pedidos} comandas`
        : `${b.area}: ${b.empleado} · ${m} · ${b.avances} pases${b.cola ? ` (${b.cola} en cola)` : ''}`;
    }).join(String.fromCharCode(10)) || 'Sin bots en marcha';
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
