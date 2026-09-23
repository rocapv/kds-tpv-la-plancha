"""QA funcional del cliente: pide desde el móvil y ve avanzar su comanda hasta que se la sirven.

    python qa_cliente.py --url http://192.168.1.100:8093

Tres personas a la vez, cada una en su navegador:
  · el CLIENTE, en su móvil, abre la carta por el QR de una mesa libre, añade dos platos, envía
    la comanda y se queda mirando la tira de seguimiento;
  · la CAMARERA (PIN 1111), en el TPV, ve llegar la solicitud, la acepta y la manda a cocina;
  · la COCINERA (PIN 3333), en el pase, la empieza, la marca lista y la da por servida.
En cada paso se comprueba que la tira del cliente ha avanzado SOLA (canal público + sondeo),
sin recargar la página. Al final se anula el pedido: no queda nada en la base de datos real.
"""
import argparse
import sys

from playwright.sync_api import sync_playwright

fallos = []


def mal(t):
    fallos.append(t); print("  ✗ " + t)


def bien(t):
    print("  · " + t)


def entrar(page, url, pin, destino):
    page.goto(url + destino, wait_until="domcontentloaded")
    page.evaluate("try { localStorage.removeItem('kds_sesion') } catch {}")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#teclado button", timeout=20000)
    for c in pin:
        page.click(f"#teclado button:text-is('{c}')")
    page.wait_for_selector("#panel-pin", state="detached", timeout=20000)


def paso_actual(cliente):
    return cliente.evaluate("document.querySelector('#mi-comanda [data-paso].actual')?.dataset.paso || null")


def esperar_paso(cliente, paso, segundos=20):
    """La tira tiene que llegar sola a ese paso, sin recargar."""
    try:
        cliente.wait_for_function(
            f"document.querySelector('#mi-comanda [data-paso].actual')?.dataset.paso === '{paso}'", timeout=segundos * 1000)
        bien(f"la tira del cliente pasa a «{paso}» sola · {cliente.text_content('#mc-texto').strip()}")
        return True
    except Exception:
        mal(f"la tira no llegó a «{paso}» en {segundos} s (está en «{paso_actual(cliente)}»)")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://192.168.1.100:8093")
    ap.add_argument("--ver", action="store_true")
    a = ap.parse_args()
    pid = None
    with sync_playwright() as pw:
        nav = pw.chromium.launch(headless=not a.ver)
        movil = nav.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        sala = nav.new_context(viewport={"width": 1280, "height": 800})
        cocina = nav.new_context(viewport={"width": 1280, "height": 800})
        cliente, camarera, cocinera = movil.new_page(), sala.new_page(), cocina.new_page()
        errores = []
        for pg in (cliente, camarera, cocinera):
            pg.on("pageerror", lambda e: errores.append(str(e)))

        print("1 · la camarera abre el TPV y busca una mesa libre")
        entrar(camarera, a.url, "1111", "/tpv.html")
        camarera.wait_for_selector("#v-mesas .mesa", timeout=20000)
        libres = camarera.eval_on_selector_all("#v-mesas .mesa:not(.ocupada)", "els => els.map(e => e.dataset.mesa)")
        # Sin mesa libre (pasa cuando la simulación ha llenado la sala) se pide PARA LLEVAR,
        # que recorre exactamente el mismo camino: solicitud → aceptar → cocina → servido.
        mesa = libres[-1] if libres else None
        bien(f"mesa libre: id {mesa}" if mesa else "sin mesas libres: la comanda va para llevar")

        print("2 · el cliente abre la carta desde el QR y pide dos cosas")
        cliente.goto(f"{a.url}/cliente.html" + (f"?mesa={mesa}" if mesa else ""), wait_until="domcontentloaded")
        cliente.evaluate("try { localStorage.removeItem('kds_mi_comanda'); localStorage.removeItem('kds_cesta') } catch {}")
        cliente.reload(wait_until="domcontentloaded")
        cliente.wait_for_selector(".plato .sumar", timeout=20000)
        if not cliente.is_hidden("#mi-comanda"):
            mal("la tira de seguimiento se ve sin haber pedido nada")
        cliente.eval_on_selector_all(".plato:not(.agotado) .sumar", "els => { els[0].click(); els[1].click(); }")
        cliente.wait_for_timeout(500)
        n = cliente.text_content("#n-cesta").strip()
        (bien if n == "2" else mal)(f"cesta con {n} productos")
        cliente.click("#b-enviar")
        cliente.wait_for_selector("#d-cesta[open]", timeout=5000)
        if not mesa:
            cliente.fill("#c-nombre", "QA cliente")
        cliente.click("#c-ok")
        cliente.wait_for_selector("#mi-comanda:not([hidden])", timeout=10000)
        (bien if paso_actual(cliente) == "enviada" else mal)(f"tira visible en «{paso_actual(cliente)}» · {cliente.text_content('#mc-texto').strip()}")
        sid = cliente.evaluate("localStorage.getItem('kds_mi_comanda')")
        bien(f"solicitud #{sid} enviada desde el móvil")

        print("3 · la camarera ve la solicitud, la acepta y la manda a cocina")
        camarera.wait_for_selector("#b-solicitudes:not([hidden])", timeout=15000)
        camarera.click("#b-solicitudes")
        camarera.wait_for_selector(f"[data-aceptar='{sid}']", timeout=10000)
        camarera.click(f"[data-aceptar='{sid}']")
        camarera.wait_for_selector("#b-enviar:not([disabled])", timeout=10000)
        pid = camarera.evaluate("pedido && pedido.id")
        bien(f"aceptada · pedido #{pid} en el ticket")
        esperar_paso(cliente, "confirmada")
        camarera.click("#b-enviar")
        camarera.wait_for_timeout(800)
        esperar_paso(cliente, "cocina")

        print("4 · la cocinera la empieza, la marca lista y la sirve")
        entrar(cocinera, a.url, "3333", "/kds.html?pantalla=pase")
        cocinera.wait_for_selector(".comanda", timeout=20000)
        tarjeta = cocinera.locator(".comanda", has=cocinera.locator(f".meta:has-text('#{pid} ')"))
        if tarjeta.count() == 0:
            tarjeta = cocinera.locator(".comanda", has=cocinera.locator(f".meta:has-text('#{pid}')"))
        (bien if tarjeta.count() == 1 else mal)(f"comanda #{pid} en el pase ({tarjeta.count()} tarjetas)")
        for esperado, paso in (("Empezar", None), ("Listo", "lista"), ("Servido", "servida")):
            texto = tarjeta.locator(".bump").text_content().strip()
            (bien if esperado in texto else mal)(f"botón de la comanda: «{texto}»")
            tarjeta.locator(".bump").click()
            # el botón cambia cuando llega el aviso del WebSocket y se repinta: se espera a eso,
            # no a un tiempo fijo (o la comanda desaparece del pase, que es el último paso)
            try:
                tarjeta.locator(".bump").wait_for(state="attached", timeout=200)
                cocinera.wait_for_function(
                    "([t, pid]) => { const c = [...document.querySelectorAll('.comanda')].find(a => a.querySelector('.meta')?.textContent.includes('#' + pid)); return !c || c.querySelector('.bump').textContent.trim() !== t; }",
                    arg=[texto, pid], timeout=8000)
            except Exception:
                pass
            if paso:
                esperar_paso(cliente, paso)

        print("5 · detalle y limpieza")
        cliente.click("#mc-detalle")
        cliente.wait_for_selector("#d-estado[open]", timeout=5000)
        detalle = cliente.text_content("#e-cuerpo")
        (bien if "servid" in detalle.lower() else mal)("el detalle refleja el estado final")
        cliente.click("#e-cerrar")
        cliente.click("#mc-olvidar")
        (bien if cliente.is_hidden("#mi-comanda") else mal)("«dejar de seguir» quita la tira")

        r = camarera.evaluate("""async pid => (await fetch('/api/pedidos/' + pid + '/anular', { method: 'POST',
            headers: { Authorization: 'Bearer ' + JSON.parse(localStorage.kds_sesion).token } })).status""", pid)
        (bien if r in (200, 409) else mal)(f"pedido #{pid} anulado ({r})")
        for e in errores[:5]:
            mal("excepción en página: " + e[:140])
        nav.close()
    print()
    print("FALLOS: %d" % len(fallos) if fallos else "SIN FALLOS")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
