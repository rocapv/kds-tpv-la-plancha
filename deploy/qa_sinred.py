"""QA del modo sin red: se le corta el wifi al TPV en mitad del servicio.

    python qa_sinred.py --url https://192.168.1.105:8443
    python qa_sinred.py --ver          # con el navegador a la vista

Recorrido, tal cual lo viviría una camarera:
  1. entra con su PIN y abre el TPV (con red);
  2. se cae la red: abre mesa, pide dos cosas y las manda a cocina;
  3. comprueba que NO puede cobrar mientras está caída;
  4. recarga la tableta sin red (esto prueba `sw.js`: sin él no habría ni pantalla);
  5. vuelve la red: lo apuntado se reenvía solo;
  6. se verifica contra la API que hay UN pedido con dos líneas en cocina, y no dos.
Al terminar anula el pedido de prueba: no deja nada en la base de datos real.
"""
import argparse
import sys

from playwright.sync_api import sync_playwright

fallos = []


def mal(texto):
    fallos.append(texto)
    print("  ✗ " + texto)


def bien(texto):
    print("  · " + texto)


def entrar(page, url, pin="1111"):
    page.goto(url + "/tpv.html", wait_until="domcontentloaded")
    page.evaluate("localStorage.removeItem('kds_sesion')")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#teclado button", timeout=15000)
    for cifra in pin:
        page.click(f"#teclado button:text-is('{cifra}')")
    page.wait_for_selector("#panel-pin", state="detached", timeout=15000)
    page.wait_for_selector("#v-mesas .mesa", timeout=15000)


def api(page, ruta):
    """Pregunta a la API con el token de la sesión del navegador."""
    return page.evaluate("""async ruta => {
        const s = JSON.parse(localStorage.getItem('kds_sesion') || '{}');
        const r = await fetch('/api' + ruta, { headers: { Authorization: 'Bearer ' + s.token } });
        return { estado: r.status, datos: await r.json() };
    }""", ruta)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://192.168.1.105:8443")
    ap.add_argument("--ver", action="store_true")
    args = ap.parse_args()

    with sync_playwright() as p:
        # `--ignore-certificate-errors` no es cosmética: con el certificado autofirmado sin
        # instalar, Chromium se NIEGA a registrar el trabajador de servicio («An SSL certificate
        # error occurred»). En la tableta del local pasa lo mismo hasta que se confía el
        # certificado; aquí se hace de cuenta que ya está confiado.
        nav = p.chromium.launch(headless=not args.ver, args=["--ignore-certificate-errors"])
        ctx = nav.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        consola = []
        page.on("console", lambda m: consola.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: consola.append(str(e)))

        print("1 · entrar con red")
        entrar(page, args.url)
        # el trabajador de servicio necesita una vuelta para hacerse cargo de la pantalla
        page.wait_for_timeout(1500)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_selector("#v-mesas .mesa", timeout=15000)
        activo = page.evaluate("!!navigator.serviceWorker.controller")
        (bien if activo else mal)("copia de la pantalla instalada (service worker)")

        libres = page.eval_on_selector_all(
            "#v-mesas .mesa:not(.ocupada)", "els => els.map(e => e.textContent.trim().split('\\n')[0])")
        if not libres:
            mal("no hay ninguna mesa libre para la prueba")
            return 1
        mesa = libres[0]
        bien(f"mesa elegida: {mesa}")

        print("2 · se cae la red")
        ctx.set_offline(True)
        page.wait_for_timeout(9000)                       # el sondeo tarda hasta 8 s en notarlo
        barra = (page.text_content("#sinred") or "").strip()
        if "Sin conexión" in barra:
            bien("avisa en pantalla: " + barra)
        else:
            mal(f"no avisa de la caída (barra: {barra!r})")

        print("3 · tomar nota sin red")
        page.click(f"#v-mesas .mesa:has-text('{mesa}')")
        page.wait_for_selector("#productos .producto", timeout=10000)
        for i in (0, 1):
            page.eval_on_selector_all(".producto:not([disabled])", f"els => els[{i}].click()")
            page.wait_for_timeout(400)
        lineas = page.eval_on_selector_all("#lineas .linea", "e => e.length")
        (bien if lineas == 2 else mal)(f"dos líneas apuntadas sin servidor (hay {lineas})")

        cobrar_bloqueado = page.is_disabled("#b-cobrar")
        (bien if cobrar_bloqueado else mal)("el botón de cobrar está bloqueado sin red")

        page.click("#b-enviar")
        page.wait_for_timeout(600)
        estados = page.eval_on_selector_all("#lineas .estado", "els => els.map(e => e.textContent)")
        (bien if estados and set(estados) == {"enviada"} else mal)(f"comanda mandada a cocina: {estados}")
        pendientes = page.evaluate("sinRed.pendientes()")
        (bien if pendientes >= 4 else mal)(f"{pendientes} acciones guardadas para cuando vuelva la red")

        print("4 · recargar la tableta sin red")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        if page.query_selector("#panel-pin"):
            mal("pide el PIN sin red (la camarera se queda fuera)")
        hay_mesas = page.eval_on_selector_all("#v-mesas .mesa", "e => e.length")
        (bien if hay_mesas else mal)(f"la pantalla se abre sin servidor ({hay_mesas} mesas pintadas)")
        sigue = page.evaluate("sinRed.pendientes()")
        (bien if sigue >= 4 else mal)(f"lo apuntado sobrevive a la recarga ({sigue} acciones)")

        print("5 · vuelve la red")
        ctx.set_offline(False)
        page.wait_for_function("sinRed.pendientes() === 0", timeout=30000)
        page.wait_for_timeout(1500)
        bien("cola vaciada")

        print("6 · comprobación contra la API")
        abiertos = api(page, "/pedidos")["datos"]
        mios = [p for p in abiertos if p["mesa"] == mesa]
        if len(mios) != 1:
            mal(f"la mesa {mesa} tiene {len(mios)} pedidos abiertos (debería tener 1)")
            return 1
        pid = mios[0]["id"]
        pedido = api(page, f"/pedidos/{pid}")["datos"]
        (bien if len(pedido["lineas"]) == 2 else mal)(
            f"el pedido #{pid} tiene {len(pedido['lineas'])} líneas (deberían ser 2)")
        enviadas = {l["estado"] for l in pedido["lineas"]}
        (bien if enviadas == {"enviada"} else mal)(f"las líneas llegaron a cocina: {enviadas}")
        en_kds = [c for c in api(page, "/kds")["datos"]["comandas"] if c["pedido_id"] == pid]
        (bien if en_kds else mal)("la comanda se ve en la pantalla de cocina")

        print("7 · limpieza")
        page.evaluate("""async pid => {
            const s = JSON.parse(localStorage.getItem('kds_sesion') || '{}');
            await fetch('/api/pedidos/' + pid + '/anular',
                        { method: 'POST', headers: { Authorization: 'Bearer ' + s.token } });
        }""", pid)
        bien(f"pedido #{pid} anulado")

        # La consola se ensucia a propósito en esta prueba: cortar la red hace que fallen el
        # WebSocket y las peticiones en vuelo. Eso NO es un fallo; lo sería un error de código.
        ESPERADOS = ("ERR_INTERNET_DISCONNECTED", "WebSocket connection", "Failed to load resource",
                     "Failed to fetch")
        de_verdad = [c for c in consola if not any(e in c for e in ESPERADOS)]
        for c in de_verdad[:10]:
            mal("consola: " + c)
        if not de_verdad:
            bien(f"consola limpia ({len(consola)} avisos, todos del corte de red)")
        ctx.close()
        nav.close()

    print()
    print(f"{'FALLOS: ' + str(len(fallos)) if fallos else 'SIN FALLOS'}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
