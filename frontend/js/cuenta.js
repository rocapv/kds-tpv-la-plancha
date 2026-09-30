// La cuenta del cliente dentro de la app: entrar, quedarse dentro y salir.
//
// El token se guarda en el móvil y **no caduca**: se entra una vez y se sigue dentro hasta pulsar
// «Salir». `comun.js` lo coge solo, porque busca una función `tokenActual()` — la misma que usa el
// personal en `sesion.js`. Aquí hay una sola app y una sola puerta: nunca se cargan los dos.
const LLAVE_CLIENTE = 'kds_cliente';

let cuenta = null;
try { cuenta = JSON.parse(localStorage.getItem(LLAVE_CLIENTE) || 'null'); } catch { cuenta = null; }

function tokenActual() { return cuenta?.token || null; }

function guardarCuenta(c) {
  cuenta = c;
  try { localStorage.setItem(LLAVE_CLIENTE, JSON.stringify(c)); } catch {}
  pintarCuenta();
}
function olvidarCuenta() {
  cuenta = null;
  try { localStorage.removeItem(LLAVE_CLIENTE); } catch {}
  pintarCuenta();
}

function pintarCuenta() {
  const b = document.querySelector('#b-cuenta');
  if (!b) return;
  b.textContent = cuenta ? (cuenta.nombre || cuenta.email.split('@')[0]) : 'Entrar';
  b.classList.toggle('dentro', Boolean(cuenta));
}

// ── Entrar y darse de alta ──
async function entrar(alta) {
  const email = $('#cu-email').value.trim();
  const contrasena = $('#cu-clave').value;
  const ruta = alta ? '/publico/clientes/registro' : '/publico/clientes/entrar';
  const cuerpo = { email, contrasena };
  if (alta) cuerpo.nombre = $('#cu-nombre').value.trim() || null;
  try {
    guardarCuenta(await api(ruta, { method: 'POST', body: cuerpo }));
    $('#d-micuenta').close();
    aviso(alta ? 'Cuenta creada' : 'Ya estás dentro', 'ok');
  } catch (e) { aviso(e.message, 'error'); }
}

async function salir() {
  try { await api('/publico/clientes/salir', { method: 'POST' }); } catch {}
  olvidarCuenta();
  $('#d-micuenta').close();
  aviso('Sesión cerrada', 'ok');
}

// ── Perfil ──
async function verPerfil() {
  try {
    const yo = await api('/publico/clientes/yo');
    guardarCuenta({ ...cuenta, ...yo });
    $('#cu-p-nombre').value = yo.nombre || '';
    $('#cu-p-telefono').value = yo.telefono || '';
    $('#cu-p-nif').value = yo.nif || '';
    $('#cu-p-razon').value = yo.razon_social || '';
    $('#cu-p-direccion').value = yo.direccion || '';
    $('#cu-p-auto').checked = Boolean(yo.factura_auto);
    $('#cu-correo').textContent = yo.email;
  } catch (e) {
    if (e.estado === 401) olvidarCuenta();      // el token ya no vale: a empezar de nuevo
  }
}

async function guardarPerfil() {
  try {
    await api('/publico/clientes/yo', { method: 'PATCH', body: {
      nombre: $('#cu-p-nombre').value.trim() || null,
      telefono: $('#cu-p-telefono').value.trim() || null,
      nif: $('#cu-p-nif').value.trim() || null,
      razon_social: $('#cu-p-razon').value.trim() || null,
      direccion: $('#cu-p-direccion').value.trim() || null,
      factura_auto: $('#cu-p-auto').checked,
    }});
    await verPerfil();
    aviso('Guardado', 'ok');
  } catch (e) { aviso(e.message, 'error'); }
}

// ── Enganches ──
function abrirCuenta() {
  const dentro = Boolean(cuenta);
  $('#cu-fuera').hidden = dentro;
  $('#cu-dentro').hidden = !dentro;
  if (dentro) verPerfil();
  $('#d-micuenta').showModal();
}

document.addEventListener('DOMContentLoaded', () => {
  $('#b-cuenta').onclick = abrirCuenta;
  $('#cu-entrar').onclick = () => entrar(false);
  $('#cu-alta').onclick = () => entrar(true);
  $('#cu-guardar').onclick = guardarPerfil;
  $('#cu-salir').onclick = salir;
  // El listado de facturas vive en `cliente.js`, que es quien tiene el diálogo del documento.
  $('#cu-facturas').onclick = () => {
    $('#d-micuenta').close();
    if (typeof verMisFacturas === 'function') verMisFacturas();
  };
  $('#cu-cerrar').onclick = () => $('#d-micuenta').close();
  $('#cu-modo').onclick = () => {
    const alta = $('#cu-nombre-campo').hidden;
    $('#cu-nombre-campo').hidden = !alta;
    $('#cu-entrar').hidden = alta;
    $('#cu-alta').hidden = !alta;
    $('#cu-modo').textContent = alta ? 'Ya tengo cuenta' : 'Crear una cuenta';
  };
  pintarCuenta();
  if (cuenta) verPerfil();     // de paso comprueba que el token sigue valiendo
});
