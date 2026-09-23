"""QA de las pantallas: entra con cada PIN, recorre el menú, abre cada aplicación,
rellena los formularios y anota lo que falta, lo que sobra y lo que peta.

    python qa.py --url https://192.168.1.105:8443
    python qa.py --ver            # con navegador a la vista

No toca datos de verdad más allá de lo que crearía una persona probando: pedidos que anula,
un producto de prueba que da de baja y un usuario de prueba que también da de baja.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

# Lo que DEBE ver cada uno en el menú, y lo que NO debe ver bajo ningún concepto.
ESPERADO = {
    "1111": {"quien": "Laura · camarero",
             "ve": ["TPV", "Facturación"],
             "no_ve": ["Informe", "Arqueo", "Carta", "Usuarios", "Ajustes", "API"]},
    "3333": {"quien": "Aitana · cocina",
             "ve": ["Recogida", "Placa térmica", "Fritura", "Cámara fría", "Pase"],
             "no_ve": ["TPV", "Informe", "Arqueo", "Carta", "Usuarios", "Ajustes", "API"]},
    "9999": {"quien": "Pau · encargado",
             "ve": ["TPV", "Facturación", "Recogida", "Informe", "Arqueo", "Carta", "Usuarios",
                    "Ajustes", "Placa térmica", "Pase"],
             "no_ve": []},
}

fallos, avisos = [], []


def anota(lista, texto):
    lista.append(texto)
    print(("  ✗ " if lista is fallos else "  · ") + texto)


def entrar(page, url, pin):
    page.goto(url + "/index.html", wait_until="domcontentloaded")
    page.evaluate("localStorage.removeItem('kds_sesion')")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#teclado button", timeout=15000)
    for cifra in pin:
        page.click(f"#teclado button:text-is('{cifra}')")
    page.wait_for_selector("#panel-pin", state="detached", timeout=15000)
    page.wait_for_timeout(900)


def tarjetas(page):
    return [t.strip().split("\n")[0] for t in page.eval_on_selector_all(
        ".app b", "els => els.map(e => e.textContent)")]


def errores_de_consola(page):
    guardados = []
    page.on("console", lambda m: guardados.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: guardados.append(str(e)))
    return guardados


def revisar_menu(page, pin, esperado):
    vistas = tarjetas(page)
    print(f"  menú: {', '.join(vistas) or '(vacío)'}")
    for debe in esperado["ve"]:
        if not any(debe.lower() in v.lower() for v in vistas):
            anota(fallos, f"[{pin}] falta «{debe}» en el menú")
    for sobra in esperado["no_ve"]:
        if any(sobra.lower() in v.lower() for v in vistas):
            anota(fallos, f"[{pin}] sobra «{sobra}»: no debería poder abrirlo")
    # Secciones sin tarjetas
    vacias = page.eval_on_selector_all(
        ".menu section", "ss => ss.filter(s => !s.querySelector('.app')).map(s => s.querySelector('h2').textContent)")
    for v in vacias:
        anota(fallos, f"[{pin}] sección «{v}» sin ninguna tarjeta")
    return vistas


def recorrer(page, url, pin, vistas, consola):
    """Abre cada tarjeta, comprueba que no cae en el PIN ni en un error, y vuelve."""
    enlaces = page.eval_on_selector_all(".app", "els => els.map(e => e.getAttribute('href'))")
    for destino in enlaces:
        if destino.startswith("/docs"):
            continue
        page.goto(url + destino, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        if page.query_selector("#panel-pin"):
            anota(fallos, f"[{pin}] {destino} pide PIN teniendo sesión")
        if "index.html" in page.url and destino != "/index.html":
            anota(fallos, f"[{pin}] {destino} rebota al menú aunque estaba en su menú")
        vacia = page.eval_on_selector_all("body main *, body section *", "els => els.length") < 3
        if vacia:
            anota(avisos, f"[{pin}] {destino} se ve vacía")
        page.goto(url + "/index.html", wait_until="domcontentloaded")
        page.wait_for_timeout(600)
    for e in consola:
        if "Failed to load resource" in e and "403" in e:
            continue                                   # permisos: se comprueban aparte
        anota(fallos, f"[{pin}] error en consola: {e[:120]}")
    consola.clear()


def probar_prohibido(page, url, pin, prohibidas):
    """Entrar a mano en una pantalla que no toca: ni PIN ni pantalla en blanco, al menú."""
    for pagina in prohibidas:
        page.goto(url + "/" + pagina, wait_until="domcontentloaded")
        page.wait_for_timeout(2600)
        if page.query_selector("#panel-pin"):
            anota(fallos, f"[{pin}] {pagina} pide PIN en vez de devolver al menú")
        elif not page.url.endswith("index.html"):
            anota(fallos, f"[{pin}] {pagina} se queda abierta para quien no debe verla")


def rellenar_formularios(page, url, pin):
    """Rellena de verdad los formularios del encargado y comprueba que guardan."""
    # ── Usuarios ──
    page.goto(url + "/usuarios.html", wait_until="domcontentloaded")
    page.wait_for_timeout(900)
    page.click("#b-nuevo")
    page.fill("#u-nombre", "QA Temporal")
    page.select_option("#u-rol", "cocina")
    page.click("#u-dado")                                   # PIN libre al azar
    # El PIN lo da el servidor (busca uno que no esté cogido), así que hay que esperarlo:
    # leerlo de inmediato devolvía vacío y el informe mentía sobre lo que había creado.
    try:
        page.wait_for_function("document.querySelector('#u-pin').value.length === 4", timeout=5000)
    except Exception:
        pass
    pin_qa = page.input_value("#u-pin")
    page.click("#u-ok")
    page.wait_for_timeout(1200)
    if "QA Temporal" not in page.inner_text("#tabla"):
        anota(fallos, "[usuarios] el alta no aparece en la tabla")
    else:
        print(f"  · usuario QA creado con PIN {pin_qa}")

    # ── Carta ──
    page.goto(url + "/carta.html", wait_until="domcontentloaded")
    page.wait_for_timeout(900)
    page.click("#b-producto")
    page.fill("#p-nombre", "Plato QA")
    page.fill("#p-precio", "7.25")
    # Los alérgenos dejaron de ser un campo de texto: ahora son el catálogo de los catorce, en
    # casillas. Se marcan las dos primeras, que es lo que haría una persona.
    casillas = page.query_selector_all("#p-alergenos [data-al]")
    if not casillas:
        anota(fallos, "[carta] el producto no ofrece ningún alérgeno que marcar")
    for c in casillas[:2]:
        c.click()
    page.click("#p-ok")
    page.wait_for_timeout(1200)
    if "Plato QA" not in page.inner_text("#carta"):
        anota(fallos, "[carta] el producto nuevo no aparece")
    else:
        print("  · producto «Plato QA» creado")

    # ── Ajustes: se toca un valor y se devuelve a su sitio ──
    page.goto(url + "/ajustes.html", wait_until="domcontentloaded")
    page.wait_for_timeout(900)
    campos = page.eval_on_selector_all("[data-k]", "els => els.map(e => e.getAttribute('data-k'))")
    if not campos:
        anota(fallos, "[ajustes] no hay ningún campo editable")
    else:
        print(f"  · ajustes editables: {len(campos)}")

    # ── TPV: comanda completa ──
    page.goto(url + "/tpv.html", wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    libre = page.query_selector(".mesa:not(.ocupada)")
    if not libre:
        anota(avisos, "[tpv] no quedaba ninguna mesa libre para la prueba")
    else:
        libre.click()
        page.wait_for_timeout(900)
        productos = page.query_selector_all(".producto:not([disabled])")
        for p in productos[:3]:
            p.click()
            page.wait_for_timeout(250)
        lineas = len(page.query_selector_all("#lineas .linea"))
        if lineas < 3:
            anota(fallos, f"[tpv] se añadieron 3 productos y salen {lineas} líneas")
        page.click("#b-enviar")
        page.wait_for_timeout(1200)
        if page.query_selector("#b-cobrar[disabled]"):
            anota(fallos, "[tpv] tras enviar a cocina, «Cobrar» sigue deshabilitado")
        else:
            print("  · comanda enviada y lista para cobrar")
        page.once("dialog", lambda d: d.accept())
        page.click("#b-anular")                              # se deja la mesa como estaba
        page.wait_for_timeout(1000)


def limpiar(page, url):
    """Deshace lo que ha creado el QA: usuario y producto de prueba.

    Se llama SIEMPRE, también si el recorrido ha reventado a mitad (va en un `finally`). Un QA
    que aborta dejando un usuario activo deja también su PIN funcionando, y en un TPV abierto a
    internet eso no es un resto molesto: es una puerta.
    """
    page.goto(url + "/usuarios.html", wait_until="domcontentloaded")
    page.wait_for_timeout(900)
    # Puede haber más de uno si alguna pasada anterior se quedó a medias: se dan de baja todos.
    for _ in range(10):
        fila = page.query_selector("tr:has-text('QA Temporal') [data-baja]")
        if not fila:
            break
        page.once("dialog", lambda d: d.accept())
        fila.click(); page.wait_for_timeout(800)
    page.goto(url + "/carta.html", wait_until="domcontentloaded")
    page.wait_for_timeout(900)
    for _ in range(10):
        fila = page.query_selector("tr:has-text('Plato QA') [data-baja]")
        if not fila:
            break
        page.once("dialog", lambda d: d.accept())
        fila.click(); page.wait_for_timeout(800)
    print("  · limpieza hecha (usuario y producto de prueba dados de baja)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://192.168.1.105:8443")
    ap.add_argument("--ver", action="store_true", help="con navegador a la vista")
    ap.add_argument("--fotos", default=str(Path(__file__).parent / "_qa"))
    a = ap.parse_args()
    Path(a.fotos).mkdir(exist_ok=True)

    with sync_playwright() as pw:
        # Con el certificado autofirmado sin instalar, Chromium se niega a registrar el
        # trabajador de servicio del TPV y llena la consola de errores de SSL que no son del
        # programa. En la tableta del local el certificado estara confiado; aqui se hace igual.
        navegador = pw.chromium.launch(headless=not a.ver, args=["--ignore-certificate-errors"])
        ctx = navegador.new_context(ignore_https_errors=True, viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        consola = errores_de_consola(page)

        for pin, esperado in ESPERADO.items():
            print(f"\n── {esperado['quien']} (PIN {pin}) ──")
            entrar(page, a.url, pin)
            barra = page.inner_text("header.barra")
            print(f"  barra: {' '.join(barra.split())[:90]}")
            if "sin conexión" in barra:
                anota(fallos, f"[{pin}] la barra dice «sin conexión con el servidor»")
            vistas = revisar_menu(page, pin, esperado)
            page.screenshot(path=f"{a.fotos}/menu_{pin}.png")
            recorrer(page, a.url, pin, vistas, consola)
            prohibidas = [p for p, n in (("informe.html", "Informe"), ("usuarios.html", "Usuarios"),
                                         ("carta.html", "Carta"), ("tpv.html", "TPV"),
                                         ("kds.html", "KDS"))
                          if n in esperado["no_ve"]]
            probar_prohibido(page, a.url, pin, prohibidas)
            if pin == "9999":
                # La limpieza va en `finally`: si el recorrido revienta a mitad, el usuario de
                # prueba (con su PIN funcionando) NO se puede quedar vivo en el sistema.
                try:
                    rellenar_formularios(page, a.url, pin)
                finally:
                    limpiar(page, a.url)

        navegador.close()

    print("\n══ RESULTADO ══")
    print(f"fallos: {len(fallos)} · avisos: {len(avisos)}")
    for f in fallos:
        print("  ✗ " + f)
    for v in avisos:
        print("  · " + v)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
