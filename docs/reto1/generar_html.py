#!/usr/bin/env python3
"""Presentación del Reto 1 (HTML + CSS + JS en ficheros separados), servida por la LAN, y ZIP de entrega.

Sigue los ocho puntos del informe (contextualización, empresa de referencia, entorno económico, modelo de
negocio y finanzas, servicios, publicidad, conclusiones y bibliografía), y deja al final, como opción, un cuestionario de seis preguntas para el público (no se llega a él con «siguiente»: se abre con su botón). 12-15 minutos: el guion hablado vive en
guion.json. Los laboratorios son páginas aparte en laboratorios/ y van en el ZIP, no en la presentación.

Se presenta con servidor.py, y cada equipo de la LAN elige su vista:
- presentación (la pizarra, la principal), con PIN;
- público (los móviles de la clase), que sigue a la presentación y vota en el cuestionario;
- PC (el guion del orador, con la diapositiva en pequeño, letra ajustable, modo lectura, desplazamiento
  automático y edición), con PIN;
- móvil (el mando: notas rápidas y controles), con PIN.
La diapositiva, el cronómetro, las animaciones, el cuestionario y los laboratorios son globales; los
laboratorios se ejecutan en la pizarra y los demás ven su espejo. Abierta sin servidor (file://),
presentacion.html funciona sola, sin sincronizar. La lógica está en web/presentacion.js y web/presentacion.css.

Teclas: ← → / espacio / clic para avanzar, N guion del orador, T cronómetro de ensayo, M movimiento,
F pantalla completa. Respeta `prefers-reduced-motion` salvo que se fuerce (M o ?movimiento=1).
Uso: python3 generar_html.py  ->  entrega/ (index.html, presentacion.html, servidor.py, css/, js/, fig/,
laboratorios/, LEEME.txt) y reto1_entrega.zip
"""
import html, json, shutil, zipfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
img = lambda f: "fig/" + f          # las figuras van como ficheros en entrega/fig/
e = html.escape
LOGO = "fig/logo_servipass.png"
GUION = {d["n"]: d for d in json.loads((AQUI / "guion.json").read_text(encoding="utf-8"))["diapositivas"]}


def tarjetas(items, cols, clase="card"):
    return f'<div class="grid c{cols}">' + "".join(f'<div class="{clase}">{x}</div>' for x in items) + "</div>"


def lista(items):
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def punto(n, titulo):
    """Cabecera de diapositiva con el número del punto del informe."""
    return f'<h2><span class="pt">{n}</span>{titulo}</h2>'


def lab(titulo, fichero, hd=False):
    """Diapositiva que carga un laboratorio de laboratorios/ a pantalla completa; no se anuncia antes.
    hd: el laboratorio ve una ventana de 1920 px de ancho (en un proyector de 1920×1080 se ve sin escalar)."""
    return ("labframe", f'''<div class="labbar"><span>{titulo}</span><span><button onclick="ir(i-1)">← anterior</button>
<a href="laboratorios/{fichero}" target="_blank" rel="noopener">abrir en una pestaña nueva ↗</a><button onclick="ir(i+1)">siguiente →</button></span></div>
<iframe data-src="laboratorios/{fichero}" title="{titulo}"{' class="hd"' if hd else ''}></iframe>''')


S = []   # (clase, html)

# 1 · Portada
S.append(("dark portada", f"""
<div class="badge">R1</div>
<img class="logo" src="{LOGO}" alt="Logo de ServiPass">
<h1 class="big">ServiPass,<br>por dentro y por fuera</h1>
<p class="sub">Contextualización de la empresa y análisis de su entorno económico</p>
<p class="pie">Reto 1 · Proyecto Intermodular I · 1.º CFGS ASIR · IES Conselleria<br>Riches Manuel y Roca · octubre de 2026</p>"""))

# 2 · Los ocho puntos
S.append(("", f"""
<h2>Los ocho puntos del informe</h2>
<div class="ocho">{''.join(f'<div class="fila"><span class="dot">{k}</span><p>{t}</p></div>' for k, t in enumerate([
  "Contextualización de la empresa", "Empresa de referencia", "Análisis del entorno económico <small>macro y micro</small>",
  "Modelo de negocio y finanzas <small>financiación · salarios · gastos · local</small>", "Servicios prestados",
  "Publicidad (marketing)", "Conclusiones", "Bibliografía"], 1))}</div>"""))

# 3 · Punto 1: la empresa
S.append(("", f"""
{punto(1, "ServiPass: la tecnología de la hostelería pequeña")}
{tarjetas([f'<b class="num">{n}</b><span>{t}</span>' for n, t in [("3", "socios que trabajan en la empresa"), ("7.450 €", "proyecto tipo, sin IVA"), ("10", "años de licencia con soporte"), ("18", "instalaciones el primer año")]], 4, "card stat")}
<div class="split mitad"><img src="{img('organigrama.png')}" alt="Organigrama de ServiPass">
<div class="card tint"><h3>Burjassot, 2026</h3>{lista(["Red, wifi, caja, Verifactu, copias y un <b>TPV + KDS propio</b>", "Microempresa que vende a microempresas: el <b>93 %</b> de los locales es independiente", "Tres socios, cuatro áreas: cada una con responsable y <b>suplente</b>", "Empresa ficticia; datos del sector reales"])}</div></div>"""))

# 4 · Punto 1: flujo de trabajo y cliente piloto
S.append(("", f"""
{punto(1, "Del primer contacto a diez años de soporte")}
<div class="ciclo">{''.join(f'<div class="card"><span class="dot">{k}</span><b>{t}</b><span>{d}</span></div>' for k, (t, d) in enumerate([
  ("Captación", "visita en horas valle"), ("Auditoría", "un día en el local"), ("Presupuesto", "cerrado, con un 50 % de anticipo"),
  ("Preparación", "1,5 días en la maqueta"), ("Instalación", "2-3 días, en el cierre del local"), ("Puesta en marcha", "formación y primer servicio"),
  ("Soporte", "diez años de licencia")], 1))}</div>
<h3 class="sec">Lo que encontró la auditoría del cliente piloto, Burglar King</h3>
{tarjetas([f'<div class="fila"><span class="dot rojo">{k}</span><b>{t}</b></div><p>{d}</p>' for k, (t, d) in enumerate([
  ("La comanda no entra en ningún sistema", "hasta que se teclea para cobrar"),
  ("TPV de 2005 con Windows XP", "sin soporte, sin copias y sin Verifactu"),
  ("Una sola red para todo", "caja, cámaras expuestas y móviles de los clientes")], 1)], 3)}"""))

# Lab 1 (tras la red del cliente piloto)
S.append(lab("Simulación: la red actual frente a la red segmentada", "red.html"))

# 5 · Punto 2: empresas de referencia
S.append(("", f"""
{punto(2, "Empresas de referencia: Revo (y Last.app como contrapunto)")}
<div class="grid c2">
 <div class="card tint"><h3>Revo · Manresa, 2013</h3>
  <div class="minis"><div><b class="num m">37</b><span>personas (2023)</span></div><div><b class="num m">1.900</b><span>clientes</span></div><div><b class="num m">6.500</b><span>cuentas activas</span></div><div><b class="num m">50 %</b><span>de las cuotas, por distribuidores</span></div></div>
  <p>TPV en la nube para tabletas. En 2023 la compró Cegid (4.400 empleados, 791 M€): los grupos grandes compran a los fabricantes pequeños con clientes fieles.</p></div>
 <div class="card oscura"><h3>Last.app · Barcelona, 2019</h3>
  <div class="minis"><div><b class="num m">2,2 M€</b><span>ronda de 2022</span></div><div><b class="num m">5 M€</b><span>ronda de 2023</span></div><div><b class="num m">500 €</b><span>de alta</span></div><div><b class="num m">35 €</b><span>al mes por la pantalla de cocina</span></div></div>
  <p>Suscripción en la nube y crecimiento con capital riesgo. No publica su facturación ni su plantilla.</p></div>
</div>
<div class="banda">Lo que toma ServiPass: especialización · cercanía (fabricante y distribuidor a la vez) · crecer según el soporte · competir en precio, no en funciones</div>"""))

# 6 · Punto 3.1: PESTEL
S.append(("", f"""
{punto("3.1", "Factores macroeconómicos (PESTEL)")}
{tarjetas([f'<b class="letra">{l}</b><h3>{t}</h3><p>{d}</p>' for l, t, d in [
  ("P", "Político", "Verifactu el <b>1/1/2027</b> para sociedades: la principal fuente de demanda"),
  ("E", "Económico", "<b>13.698</b> bares y restaurantes en la provincia; rentabilidad <b>−0,9 %</b>; IPC del <b>4,9 %</b>"),
  ("S", "Social", "El <b>81,6 %</b> de las empresas tiene dos asalariados o menos: el cliente no tiene informático"),
  ("T", "Tecnológico", "Windows 10 sin soporte; la digitalización se quedó en el cobro, no en la cocina"),
  ("A", "Ambiental", "Retirada de los equipos viejos como RAEE; bisfenol A en el papel térmico; ticket electrónico"),
  ("L", "Legal", "Verifactu también para quien hace el software; encargado del tratamiento (RGPD)")]], 3, "card pestel")}"""))

# Lab 2 (tras el factor legal del PESTEL)
S.append(lab("Simulación: Verifactu, la cadena de facturas", "verifactu.html", hd=True))

# 7 · Punto 3.2: micro
S.append(("", f"""
{punto("3.2", "Factores microeconómicos")}
<div class="grid c3">
 <div class="card"><h3>Clientes</h3>{lista(["Hamburguesería y comida rápida", "Bar de barrio: volumen de mercado", "Restaurante de mantel: importa el pase", "Cadenas: ya tienen su sistema, fuera de mercado"])}</div>
 <div class="card"><h3>Proveedores</h3>{lista(["Mayorista de informática: dependencia <b>alta</b>", "Repositorio y copias, operadoras y gestoría: media", "Aseguradora: baja", "Sin almacén: los equipos se compran con el anticipo"])}</div>
 <div class="card tint"><h3>Competencia</h3>{lista(["Cobran <b>por terminal o por pantalla</b>; la de cocina, casi siempre aparte", "Last.app con pantalla de cocina: <b>85 €/mes</b>, 10.700 € en diez años", "ServiPass: <b>1.800 €</b> por diez años", "Competencia monopolística: cercanía y confianza"])}</div>
</div>"""))

# 8 · Punto 4: modelo de negocio (barras HTML animadas)
PROYECTO = [("Equipos (20 % de margen)", 3850, "#E67E22"), ("Instalación y formación", 1800, "#D35400"),
            ("Licencia: derecho de uso", 900, "#27AE60"), ("Licencia: soporte en diez años", 900, "#7F8C8D")]
S.append(("", f"""
{punto(4, "Modelo de negocio: un proyecto tipo de 7.450 €")}
<div class="barras g">{''.join(f'<span class="id">{round(v / 74.5)} %</span><div class="barra"><i style="width:{v / 74.5 * 1.5:.1f}%;background:{c}"></i><b>{v:,} €</b></div><span>{t}</span>'.replace(',', '.') for t, v, c in PROYECTO)}</div>
<div class="tras-barras">{tarjetas([f'<b class="num">{n}</b><span>{t}</span>' for n, t in [("3.340 €", "de margen por instalación"), ("27", "instalaciones al año: punto muerto"), ("33.870 €", "antes de impuestos el tercer año (−24.158 € el primero)")]], 3, "card stat")}</div>
<p class="nota">Escenario: 18, 24 y 30 instalaciones en los años 1 a 3; 9, 8 y 6 de ellas, de locales mecenas que ya tienen la licencia (margen de 2.440 €). El soporte se cobra al instalar, pero cuenta como ingreso en diez años: 90 € por cliente y año (Resolución del ICAC de 10/02/2021).</p>"""))


# 9 · Punto 4.1 y 4.2
S.append(("", f"""
{punto("4.1 · 4.2", "Financiación y salarios")}
<div class="grid c2">
 <div class="card"><h3>Micromecenazgo · 50.000 €</h3>{lista(["Campaña de recompensa en Verkami: <b>todo o nada</b> en 40 días, 6,5 % de comisión", "Desde <b>1 €</b>, diez años de servicio · <b>10 €</b>, de por vida · <b>100 €</b>, y las expansiones de la siguiente versión · <b>500 €</b>, y soporte gratis para siempre", "Quedan <b>38.072 €</b> tras el IVA y la comisión: sin deuda ni intereses, y los mecenas son los primeros clientes", "Riesgos: licencias casi regaladas y soporte sin fin · plan B: socios y microcrédito"])}</div>
 <div class="card tint"><h3>Salarios: convenio estatal TIC</h3>
  <div class="barras s"><span class="id">C3</span><div class="barra"><i style="width:100%"></i><b>24.105 €</b></div><span>cada socio</span>
  <span class="id">D1</span><div class="barra"><i style="width:85%;background:#D35400"></i><b>20.436 €</b></div><span>primer técnico</span>
  <span class="id">SMI</span><div class="barra"><i style="width:71%;background:#aaa"></i><b>17.094 €</b></div><span>mínimo legal</span></div>
  <p>XIX Convenio de consultoría y tecnologías de la información, área 3 (BOE-A-2026-9024). Coste de los tres socios: <b>83.116 €/año</b>. Se contrata al pasar de 45 instalaciones al año.</p></div>
</div>"""))


# 10 · Punto 4.3 y 4.4
S.append(("", f"""
{punto("4.3 · 4.4", "Gastos materiales y el local")}
<div class="grid c3">
 <div class="card"><h3>Equipos · proyecto tipo</h3>
  <table class="mini esc"><tr><td>Servidor de bajo consumo</td><td>450 €</td></tr><tr><td>Terminal de caja</td><td>700 €</td></tr><tr><td>Dos tabletas de sala</td><td>500 €</td></tr><tr><td>Dos pantallas de cocina</td><td>600 €</td></tr><tr><td>Red: conmutador, wifi y router</td><td>560 €</td></tr><tr><td>SAI, armario y cableado</td><td>400 €</td></tr><tr class="tot"><td>Coste</td><td>3.210 €</td></tr><tr class="tot"><td>Venta sin IVA</td><td>3.850 €</td></tr></table>
  <p><b class="num">20 %</b> de margen sobre el coste</p></div>
 <div class="card"><h3>Gastos generales · 1.430 €/mes</h3>{lista(["Alquiler <b>490 €</b> · publicidad 300 €", "Desplazamientos 250 €: visitas, instalaciones y guardias", "Suministros y telefonía 150 € · gestoría 120 €", "Seguros 60 € · software y servicios 60 €", "Licencias de terceros: <b>0 €</b>, programas libres"])}</div>
 <div class="card tint"><h3>El local · 65 m² en Burjassot</h3>{lista(["<b>490 €/mes</b>: 7,54 €/m², el más barato de la muestra (Nuroa)", "Fotocasa: 35 locales en oferta, de 4,46 a 13,75 €/m²", "Oficina, taller con la maqueta y un almacén pequeño", "LAU: IPC anual y fianza de dos meses (art. 36)", "Las obras en los locales de los clientes necesitan permiso del propietario"])}</div>
</div>"""))


# 11 · Puntos 5 y 6
S.append(("", f"""
{punto("5 · 6", "Servicios prestados y publicidad")}
<div class="grid c2">
 <div class="card"><h3>Servicios · precio sin IVA</h3>
  <table class="mini"><tr><td>Proyecto TPV + KDS</td><td>desde 7.450 €</td></tr><tr><td>Licencia sola, diez años</td><td>1.800 €</td></tr><tr><td>Auditoría tecnológica (se descuenta)</td><td>150 €</td></tr><tr><td>Red segmentada y wifi profesional</td><td>desde 600 €</td></tr><tr><td>Videovigilancia conforme a la ley</td><td>desde 300 €</td></tr><tr><td>Ampliaciones</td><td>37,50 €/h</td></tr></table>
  <p>Soporte: número único, guardia en comidas y cenas, respuesta en <b>menos de 15 minutos</b> y equipo de repuesto en 24 horas.</p></div>
 <div class="card tint"><h3>Publicidad · 300 €/mes</h3>
  <p class="lema">«Se paga una vez. Funciona diez años.»</p>
  {lista(["<b>Burglar King como caso de éxito</b>: visitas en hora punta", "Visita comercial en horas valle, nunca durante el servicio", "Jornadas sobre Verifactu con las gestorías de la zona", "Web con la calculadora del coste a diez años · una pantalla gratis por recomendación"])}</div>
</div>
<p class="nota">Calendario: los meses antes de los plazos de Verifactu y el inicio del curso universitario.</p>"""))

# Lab 3 (tras los servicios)
S.append(lab("Simulación: una hora punta con papel y con KDS", "hora_punta.html"))

# 12 · Punto 7: conclusiones
S.append(("dark", f"""
{punto(7, "Conclusiones")}
<div class="pasos">{''.join(f'<div class="fila"><span class="dot g">{k}</span><p>{t}</p></div>' for k, t in enumerate([
  "Una microempresa que vende a microempresas: un <b>TPV + KDS propio</b> con pago único y diez años de soporte.",
  "Viable a medio plazo: punto muerto en <b>26-27 instalaciones</b>; −24.158 € el primer año, −8.634 € el segundo y 33.870 € el tercero.",
  "Sin deuda: un <b>micromecenazgo</b> de 50.000 €, pagado con licencias para los mecenas y soporte para siempre que hay que vigilar.",
  "El entorno pone fecha: <b>Verifactu el 1/1/2027</b>, Windows 10 sin soporte y una cocina que sigue en papel.",
  "<b>1.800 €</b> de licencia frente a 10.700 € de suscripción: competir en precio, no en funciones, y crecer según el soporte."], 1))}</div>"""))

# 13 · Bibliografía
S.append(("dark", f"""
{punto(8, "Bibliografía")}
<div class="grid c3 bib">
 <div class="card oscura"><h3>Sector y empresas</h3>{lista(["INE (2025) · Profesional Horeca (2025) · Hosteltur (2026)", "Cegid (2023) · capital-riesgo.es (2022, 2023) · Taylor (2023)", "El Periòdic (2025) · Riches Manuel y Roca (2026)"])}</div>
 <div class="card oscura"><h3>Finanzas y trabajo</h3>{lista(["XIX Convenio TIC (BOE-A-2026-9024) · RD 126/2026 (SMI)", "Verkami (s.f., 2025) · Ley 5/2015 · Reglamento (UE) 2020/1503", "Cámara de España (2022) · ICO (s.f.) · Intelectium (s.f.)", "Billin (2026) · idealista/news (2026) · Digitaliza CV (2026)"])}</div>
 <div class="card oscura"><h3>Mercado y normativa</h3>{lista(["idealista, Fotocasa, Habitaclia y Nuroa (2026)", "Garrigues (2025) · Microsoft (2025) · L'Express Franchise (2026)", "Ley 11/2021 · RD 1007/2023 · RGPD · Resolución del ICAC (2021)"])}</div>
</div>
<button class="opc-q" onclick="ir(i+1,true)">¿? Preguntas para el público (opcional)</button>"""))

# 14 · Cuestionario
S.append(("lab quiz opcional", """
<h2><span class="pt">¿?</span>Seis preguntas para terminar</h2>
<div id="quiz"></div>"""))


# Estilos y lógica de la presentación: ficheros propios en web/ (se copian tal cual a la entrega).
CSS = (AQUI / "web" / "presentacion.css").read_text(encoding="utf-8")
JS = (AQUI / "web" / "presentacion.js").read_text(encoding="utf-8")

cuerpo = "".join(
    f'<section class="slide {c}" data-notas="{e(GUION[k]["texto"])}" data-rapidas="{e(json.dumps(GUION[k].get("rapidas", []), ensure_ascii=False))}" '
    f'data-titulo="{e(GUION[k]["titulo"])}" data-min="{GUION[k]["min"]}" '
    f'data-acum="{sum(GUION[j]["min"] for j in range(1, k + 1))}" aria-label="Diapositiva {k}">{h}'
    + (f'<span class="num-pag">{k}</span>' if k > 1 else "") + "</section>"
    for k, (c, h) in enumerate(S, 1))
assert len(S) == len(GUION), (len(S), len(GUION))
ENTREGA = AQUI / "entrega"
if ENTREGA.exists():
    shutil.rmtree(ENTREGA)
for d in ("css", "js", "fig"):
    (ENTREGA / d).mkdir(parents=True)
for f in ("organigrama.png", "flujo_comanda.png", "red_actual.png", "costes.png"):
    shutil.copy(AQUI / "fig" / f, ENTREGA / "fig" / f)
shutil.copy(AQUI / "fig" / "logo_servipass.png", ENTREGA / "fig" / "logo_servipass.png")
shutil.copytree(AQUI / "laboratorios", ENTREGA / "laboratorios")
(ENTREGA / "css" / "presentacion.css").write_text(CSS, encoding="utf-8")
(ENTREGA / "js" / "presentacion.js").write_text(JS, encoding="utf-8")
doc = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reto 1 · ServiPass</title><link rel="stylesheet" href="css/presentacion.css"></head>
<body><div id="prog"><i></i></div><div id="deck">{cuerpo}</div><div id="notas"></div><div id="ui"></div>
<div id="toast"></div><div id="reloj"></div><script src="js/presentacion.js"></script></body></html>"""
(ENTREGA / "presentacion.html").write_text(doc, encoding="utf-8")
shutil.copy(AQUI / "servidor.py", ENTREGA / "servidor.py")
(ENTREGA / "index.html").write_text(f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reto 1 · ServiPass · elegir vista</title><style>
body{{margin:0;min-height:100vh;background:#23272b;color:#fff;font-family:Arial,Helvetica,sans-serif;display:grid;place-items:center}}
main{{width:min(900px,calc(100vw - 32px));padding:32px 0}}h1{{font-size:30px;margin:18px 0 6px}}p{{color:#ccc;font-size:17px;line-height:1.45}}
img{{width:110px;border-radius:18px}}.op{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px;margin-top:26px}}
a.c{{display:block;background:#2f353b;border:2px solid #444;border-radius:14px;padding:22px 24px;color:#fff;text-decoration:none;transition:border-color .2s,transform .2s}}
a.c:hover{{border-color:#e67e22;transform:translateY(-3px)}}a.c b{{display:block;font-size:22px;color:#e67e22;margin-bottom:8px}}a.c span{{color:#ccc;font-size:15px;line-height:1.4}}
small{{display:block;margin-top:26px;color:#999;font-size:14px}}small a{{color:#e67e22}}</style></head>
<body><main><img src="{LOGO}" alt="Logo de ServiPass"><h1>Reto 1 · ServiPass</h1>
<p>Elige qué ve este equipo. Todos van siempre a la vez: la diapositiva, el cronómetro, las animaciones, el cuestionario y los laboratorios son los mismos en todas las pantallas. Las vistas de control piden el PIN que muestra el servidor.</p>
<div class="op"><a class="c" href="presentacion.html"><b>Presentación</b><span>La pizarra electrónica, la principal: los laboratorios se manejan aquí. Pantalla completa con la tecla F. Con PIN.</span></a>
<a class="c" href="presentacion.html?vista=pc"><b>PC · guion</b><span>El guion con la diapositiva en pequeño, letra ajustable, modo lectura, desplazamiento automático y edición. Con PIN.</span></a>
<a class="c" href="presentacion.html?vista=mando"><b>Móvil · mando</b><span>Notas rápidas, anterior y siguiente, cronómetro, animaciones, laboratorios y cuestionario. Con PIN.</span></a>
<a class="c" href="presentacion.html?vista=publico"><b>Público</b><span>Sigue la presentación y vota en el cuestionario. Sin PIN; el atajo es /p.</span></a></div>
<small>Los tres laboratorios, por separado: <a href="laboratorios/index.html">laboratorios/index.html</a></small></main></body></html>""", encoding="utf-8")
MIN = sum(d["min"] for d in GUION.values())
(ENTREGA / "LEEME.txt").write_text(f"""Reto 1 · Proyecto Intermodular I · ServiPass
Riches Manuel y Roca · 1.º CFGS ASIR · IES Conselleria · octubre de 2026

CÓMO SE PRESENTA (servidor en la red local, sin internet)
1. Descomprimir la carpeta entera en el equipo que hará de servidor y, dentro de ella, ejecutar:
       python3 servidor.py            (en Windows: py servidor.py; opción --puerto 8000)
   Solo necesita Python 3, sin instalar nada más. La primera vez, Windows puede pedir permiso en el cortafuegos
   para la red privada: hay que permitirlo.
2. El servidor imprime su dirección (por ejemplo http://192.168.1.20:8000/) y el PIN de los controles. Abrir la
   dirección en cada equipo de la misma red y elegir la vista:
     Presentación   la pizarra electrónica, la principal (con PIN).
     PC             el guion del orador: diapositiva en pequeño, siguiente, cronómetro, letra A− / A+, modo
                    lectura, desplazamiento automático con el cronómetro y edición del guion (con PIN).
     Móvil          el mando: notas rápidas, anterior y siguiente, cronómetro, animaciones, botones de los
                    laboratorios y mandos del cuestionario (con PIN).
     Público        los móviles de la clase, en http://IP:8000/p: siguen a la presentación y votan (sin PIN).
3. Todo es global: la diapositiva, el cronómetro, las animaciones (M), el cuestionario y los laboratorios. Los
   laboratorios se manejan en la pizarra (o con sus botones desde el PC y el móvil) y los demás ven su espejo.
   En el cuestionario vota el público; la pizarra enseña el recuento y se cierra cada pregunta desde cualquier
   control. Un equipo que se conecta tarde entra donde vaya la presentación.
4. Los cambios del guion hechos desde el PC se guardan en guion_vivo.json y llegan a todos. El PIN, las sesiones
   y el estado se guardan en sesion_servidor.json: reiniciar el servidor no echa a nadie y sigue donde iba.
   Opciones del servidor:
   --pin 1234 para fijar el PIN, --nuevo-pin para cambiarlo y cerrar las sesiones, y --desde-cero para empezar
   en la diapositiva 1 con el cronómetro a cero y sin votos (después de un ensayo).
Sin servidor, presentacion.html también se abre con doble clic, pero cada equipo va por su cuenta.

index.html             Elección de la vista.
presentacion.html      Presentación ({len(S)} diapositivas, {MIN:g} min). ?vista=pc, ?vista=mando o ?vista=publico.
                       Teclas: flechas o espacio para avanzar, N guion (en la pizarra), t cronómetro (T lo reinicia),
                       M animaciones sí/no, F pantalla completa. Tres diapositivas cargan los laboratorios. Tras la
                       bibliografía, un botón abre, si se quiere, el cuestionario de 3 preguntas.
servidor.py            Servidor de la presentación: sirve la carpeta, guarda el estado global y lo reparte.
css/presentacion.css   Estilos y animaciones de la presentación.
js/presentacion.js     Vistas, PIN, navegación, sincronización, espejo de los laboratorios, votación y edición.
fig/                   Figuras del informe (organigrama de ServiPass; flujo de la comanda y red actual del
                       cliente piloto, Burglar King; costes) y logo de ServiPass.
laboratorios/          Tres simulaciones sobre Burglar King, el cliente piloto (abrir laboratorios/index.html);
                       cada una se lanza con «Simular» y tiene modo manual:
  red.html             Lab 1 · La red actual frente a la segmentada: misma batería de pings en los dos escenarios.
  verifactu.html       Lab 2 · Tres facturas completas encadenadas con SHA-256: cualquier cambio rompe la huella a la vista.
  hora_punta.html      Lab 3 · Hora punta simulada en paralelo: papel, voz y tableta contra KDS, mismo flujo de pedidos.
  css/lab.css, js/     Estilos y lógica de cada laboratorio (JavaScript sin dependencias).

El informe en PDF (reto1_contexto_tecnologico.pdf) se entrega aparte.
""", encoding="utf-8")
ZIP = AQUI / "reto1_entrega.zip"
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(ENTREGA.rglob("*")):
        if f.is_file():
            z.write(f, "reto1_entrega/" + f.relative_to(ENTREGA).as_posix())
    n = len(z.namelist())
print("HTML:", ENTREGA / "presentacion.html", f"{len(S)} diapositivas · {MIN:g} min")
print("ZIP:", ZIP, f"{ZIP.stat().st_size / 1024:.0f} KB ·", n, "ficheros")
