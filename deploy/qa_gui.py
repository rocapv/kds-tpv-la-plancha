"""QA de la interfaz: cada pantalla, con cada rol, en tableta y en móvil.

    python qa_gui.py --url http://192.168.1.100:8093 --tanda despues
    python qa_gui.py --url https://home.pr1.es --tanda antes

Por cada pantalla que ve cada rol se mira lo que una revisión de calidad miraría a mano, pero
sin cansarse: errores de consola, desbordamiento horizontal (la pantalla que "se sale" por un
lado), botones demasiado pequeños para el dedo, texto con contraste insuficiente (WCAG 2.1 AA:
4,5:1 el normal, 3:1 el grande) y textos que se cortan (elipsis o recorte). Deja una captura de
cada pantalla en deploy/_qa/gui/<tanda>/ y un informe JSON + Markdown al lado.

No toca datos: solo entra, mira y hace capturas.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
ROLES = {"1111": "camarero", "3333": "cocina", "9999": "encargado"}
PUBLICAS = ["/recogida.html", "/cliente.html?mesa=3"]
TAMANOS = {"tableta": (1280, 800), "movil": (390, 844)}

# Lo que se mide dentro de la página. Va en un solo bloque para no hacer cien viajes.
MEDIR = r"""
() => {
  const rel = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const lum = ([r, g, b]) => 0.2126 * rel(r) + 0.7152 * rel(g) + 0.0722 * rel(b);
  const parse = (s) => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(',').map(Number); return { rgb: p.slice(0, 3), a: p.length > 3 ? p[3] : 1 }; };
  const mezcla = (arriba, abajo) => arriba.rgb.map((c, i) => Math.round(c * arriba.a + abajo[i] * (1 - arriba.a)));
  // Fondo efectivo: se sube por los padres componiendo los fondos con transparencia.
  const fondoDe = (el) => {
    let capas = [];
    for (let e = el; e; e = e.parentElement) {
      const bg = parse(getComputedStyle(e).backgroundColor);
      if (bg && bg.a > 0) { capas.push(bg); if (bg.a >= 1) break; }
    }
    let f = [16, 13, 12];           // si nada es opaco, el color de fondo del body
    for (let i = capas.length - 1; i >= 0; i--) f = mezcla(capas[i], f);
    return f;
  };
  const contraste = (a, b) => { const l1 = lum(a), l2 = lum(b); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); };
  const visible = (el) => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && cs.opacity !== '0'; };

  const bajos = [];
  const vistos = new Set();
  for (const el of document.querySelectorAll('p,span,b,small,em,h1,h2,h3,h4,button,a,td,th,label,li,dt,dd,legend,summary')) {
    if (!visible(el)) continue;
    const texto = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ').trim();
    if (texto.length < 2) continue;
    const cs = getComputedStyle(el);
    const col = parse(cs.color); if (!col) continue;
    const fondo = fondoDe(el);
    const fg = col.a < 1 ? mezcla(col, fondo) : col.rgb;
    const ratio = contraste(fg, fondo);
    const px = parseFloat(cs.fontSize), negrita = parseInt(cs.fontWeight) >= 700;
    const grande = px >= 24 || (px >= 18.66 && negrita);
    const minimo = grande ? 3 : 4.5;
    if (ratio < minimo) {
      const clave = el.tagName + '.' + el.className + ':' + texto.slice(0, 30);
      if (vistos.has(clave)) continue; vistos.add(clave);
      bajos.push({ texto: texto.slice(0, 40), ratio: +ratio.toFixed(2), minimo, px, sel: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className ? '.' + String(el.className).split(' ')[0] : '') });
    }
  }

  const pequenos = [];
  for (const el of document.querySelectorAll('button,a[href],input[type=checkbox],[role=button]')) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 40 || r.height < 40) {
      pequenos.push({ sel: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className ? '.' + String(el.className).split(' ')[0] : ''), w: Math.round(r.width), h: Math.round(r.height), texto: (el.textContent || '').trim().slice(0, 25) });
    }
  }

  const cortados = [];
  for (const el of document.querySelectorAll('*')) {
    if (!visible(el)) continue;
    const cs = getComputedStyle(el);
    if (cs.overflow === 'hidden' && el.scrollWidth > el.clientWidth + 2 && el.textContent.trim().length > 3 && cs.textOverflow !== 'ellipsis') {
      cortados.push({ sel: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className ? '.' + String(el.className).split(' ')[0] : ''), texto: el.textContent.trim().slice(0, 30) });
      if (cortados.length > 8) break;
    }
  }

  return {
    desborde: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    ancho: document.documentElement.scrollWidth, ventana: document.documentElement.clientWidth,
    contraste_bajo: bajos.slice(0, 25), botones_pequenos: pequenos.slice(0, 25), cortados,
    titulo: document.title, fuentes: [...new Set([...document.querySelectorAll('body,h1,h2,button,input')].map(e => getComputedStyle(e).fontFamily.split(',')[0]))],
  };
}
"""


def entrar(page, url, pin):
    page.goto(url + "/index.html", wait_until="domcontentloaded")
    page.evaluate("try { localStorage.removeItem('kds_sesion') } catch {}")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#teclado button", timeout=20000)
    for cifra in pin:
        page.click(f"#teclado button:text-is('{cifra}')")
    page.wait_for_selector("#panel-pin", state="detached", timeout=20000)
    # Las tarjetas de cocina llegan por AJAX después del menú: hay que darles tiempo, o el
    # recorrido de la cocinera se queda sin sus pantallas de KDS.
    try:
        page.wait_for_selector('.app[href*="kds.html"]', timeout=6000)
    except Exception:
        pass
    page.wait_for_timeout(600)


def enlaces_del_menu(page):
    hrefs = page.eval_on_selector_all(".app", "els => els.map(e => e.getAttribute('href'))")
    return [h for h in hrefs if h and not h.startswith("/docs")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://192.168.1.100:8093")
    ap.add_argument("--tanda", default="despues")
    ap.add_argument("--solo", help="solo esta pantalla (p. ej. tpv.html)")
    a = ap.parse_args()
    salida = AQUI / "_qa" / "gui" / a.tanda
    salida.mkdir(parents=True, exist_ok=True)
    informe = {"url": a.url, "cuando": datetime.now().isoformat(timespec="seconds"), "pantallas": []}

    with sync_playwright() as pw:
        nav = pw.chromium.launch(headless=True)
        for tamano, (w, h) in TAMANOS.items():
            for pin, rol in list(ROLES.items()) + [(None, "publico")]:
                ctx = nav.new_context(viewport={"width": w, "height": h}, device_scale_factor=1,
                                      is_mobile=(tamano == "movil"), has_touch=(tamano == "movil"))
                page = ctx.new_page()
                consola = []
                page.on("console", lambda m: consola.append(m.text) if m.type == "error" else None)
                page.on("pageerror", lambda e: consola.append("EXCEPCION " + str(e)))
                if pin:
                    entrar(page, a.url, pin)
                    rutas = ["/index.html"] + enlaces_del_menu(page)
                else:
                    rutas = PUBLICAS
                for ruta in rutas:
                    if a.solo and a.solo not in ruta:
                        continue
                    consola.clear()
                    page.goto(a.url + ruta, wait_until="domcontentloaded")
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    page.wait_for_timeout(900)
                    nombre = ruta.strip("/").replace("/", "_").replace("?", "_").replace("=", "-").replace(".html", "") or "index"
                    fichero = salida / f"{tamano}_{rol}_{nombre}.png"
                    page.screenshot(path=str(fichero), full_page=False)
                    try:
                        m = page.evaluate(MEDIR)
                    except Exception as e:  # una página que se ha ido al menú, por ejemplo
                        m = {"error_medida": str(e)[:120]}
                    m.update({"tamano": tamano, "rol": rol, "ruta": ruta, "url_final": page.url.replace(a.url, ""),
                              "consola": [c for c in consola if "favicon" not in c and "WebSocket" not in c],
                              "captura": fichero.name})
                    informe["pantallas"].append(m)
                    avisos = []
                    if m.get("desborde"): avisos.append(f"DESBORDE {m['ancho']}>{m['ventana']}")
                    if m.get("contraste_bajo"): avisos.append(f"contraste×{len(m['contraste_bajo'])}")
                    if tamano == "movil" and m.get("botones_pequenos"): avisos.append(f"pequeños×{len(m['botones_pequenos'])}")
                    if m.get("cortados"): avisos.append(f"cortados×{len(m['cortados'])}")
                    if m["consola"]: avisos.append(f"consola×{len(m['consola'])}")
                    print(f"  {tamano:7} {rol:9} {ruta:34} {' · '.join(avisos) or 'ok'}")
                ctx.close()
        nav.close()

    (salida / "informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
    # Resumen en Markdown, para leerlo de un vistazo y para pegarlo en la memoria del proyecto.
    filas = ["| Tamaño | Rol | Pantalla | Desborde | Contraste bajo | Botones < 40 px | Cortados | Consola |", "|---|---|---|---|---|---|---|---|"]
    tot = {"desborde": 0, "contraste": 0, "pequenos": 0, "cortados": 0, "consola": 0}
    for m in informe["pantallas"]:
        d = "SÍ" if m.get("desborde") else ""
        c = len(m.get("contraste_bajo", [])); p = len(m.get("botones_pequenos", [])) if m["tamano"] == "movil" else 0
        k = len(m.get("cortados", [])); e = len(m["consola"])
        tot["desborde"] += bool(d); tot["contraste"] += c; tot["pequenos"] += p; tot["cortados"] += k; tot["consola"] += e
        filas.append(f"| {m['tamano']} | {m['rol']} | `{m['ruta']}` | {d} | {c or ''} | {p or ''} | {k or ''} | {e or ''} |")
    detalle = []
    for m in informe["pantallas"]:
        for b in m.get("contraste_bajo", []):
            detalle.append(f"- {m['tamano']}/{m['rol']} `{m['ruta']}` · contraste {b['ratio']}:1 (mín. {b['minimo']}) en `{b['sel']}` «{b['texto']}»")
        if m["tamano"] == "movil":
            for b in m.get("botones_pequenos", []):
                detalle.append(f"- {m['tamano']}/{m['rol']} `{m['ruta']}` · botón {b['w']}×{b['h']} px `{b['sel']}` «{b['texto']}»")
        for c in m["consola"]:
            detalle.append(f"- {m['tamano']}/{m['rol']} `{m['ruta']}` · consola: {c[:140]}")
    md = [f"# QA de la interfaz · tanda «{a.tanda}» · {informe['cuando']} · {a.url}", "",
          f"Pantallas medidas: {len(informe['pantallas'])} · desbordes: {tot['desborde']} · textos con contraste bajo: {tot['contraste']} · "
          f"botones pequeños en móvil: {tot['pequenos']} · cortados: {tot['cortados']} · errores de consola: {tot['consola']}", "",
          *filas, "", "## Detalle", *(detalle or ["- nada que señalar"])]
    (salida / "informe.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n{len(informe['pantallas'])} pantallas · desbordes {tot['desborde']} · contraste {tot['contraste']} · pequeños {tot['pequenos']} · cortados {tot['cortados']} · consola {tot['consola']}")
    print(f"informe: {salida / 'informe.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
