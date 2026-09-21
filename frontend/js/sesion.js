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
  try { await api('/logout', { method: 'POST' }); } catch {}
  borrarSesion();
  location.reload();
}

/** Garantiza una sesión válida con uno de los roles pedidos. Devuelve el empleado. */
async function exigirSesion(roles = []) {
  while (true) {
    if (tokenActual()) {
      try {
        const yo = await api('/yo');
        if (!roles.length || roles.includes(yo.rol)) { pintarBarraSesion(yo); return yo; }
        await pedirPin(`Esta pantalla es para ${roles.join(' o ')}. ${yo.nombre} es ${yo.rol}.`);
        continue;
      } catch (e) {
        borrarSesion();
      }
    }
    await pedirPin();
  }
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

/** Pone «Nombre (rol)» y el botón de salir en la barra superior de cualquier pantalla. */
function pintarBarraSesion(yo) {
  const barra = document.querySelector('header.barra');
  if (!barra || barra.querySelector('.sesion')) return;
  const hueco = barra.querySelector('.hueco') || barra;
  const span = document.createElement('span');
  span.className = 'sesion tenue';
  span.textContent = `${yo.nombre} (${yo.rol})`;
  const boton = document.createElement('button');
  boton.textContent = 'Salir';
  boton.onclick = salir;
  hueco.after(span, boton);
}
