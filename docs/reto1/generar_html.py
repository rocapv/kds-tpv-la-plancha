#!/usr/bin/env python3
"""Presentación del Reto 1 (HTML + CSS + JS en ficheros separados) y ZIP de entrega con los laboratorios.

Sigue los ocho puntos del informe (contextualización, empresa de referencia, entorno económico, modelo de
negocio y finanzas, servicios, publicidad, conclusiones y bibliografía), termina con un cuestionario de tres preguntas (sin anunciarlo antes). 12-15 minutos: el guion hablado vive en
guion.json. Los laboratorios son páginas aparte en laboratorios/ y van en el ZIP, no en la presentación.

Teclas: ← → / espacio / clic para avanzar, N guion del orador, T cronómetro de ensayo, M movimiento,
F pantalla completa. Respeta `prefers-reduced-motion` salvo que se fuerce (M o ?movimiento=1).
Uso: python3 generar_html.py  ->  entrega/ (presentacion.html, css/, js/, fig/, laboratorios/, LEEME.txt) y reto1_entrega.zip
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


def lab(titulo, fichero):
    """Diapositiva que carga un laboratorio de laboratorios/ a pantalla completa; no se anuncia antes."""
    return ("labframe", f'''<div class="labbar"><span>{titulo}</span><span><button onclick="ver(i-1)">← anterior</button>
<a href="laboratorios/{fichero}" target="_blank" rel="noopener">abrir en una pestaña nueva ↗</a><button onclick="ver(i+1)">siguiente →</button></span></div>
<iframe data-src="laboratorios/{fichero}" title="{titulo}"></iframe>''')


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
{tarjetas([f'<b class="num">{n}</b><span>{t}</span>' for n, t in [("2", "socios que trabajan en la empresa"), ("7.450 €", "proyecto tipo, sin IVA"), ("10", "años de licencia con soporte"), ("18", "instalaciones el primer año")]], 4, "card stat")}
<div class="split mitad"><img src="{img('organigrama.png')}" alt="Organigrama de ServiPass">
<div class="card tint"><h3>Burjassot, 2026</h3>{lista(["Red, wifi, caja, Verifactu, copias y un <b>TPV + KDS propio</b>", "Microempresa que vende a microempresas: el <b>93 %</b> de los locales es independiente", "Dos socios, cuatro áreas: cada uno es <b>suplente</b> del otro", "Empresa ficticia; datos del sector reales"])}</div></div>"""))

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
  ("TPV de 2015 con Windows 10", "sin soporte, sin copias y sin Verifactu"),
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
  ("P", "Político", "Verifactu el <b>1/1/2027</b> para sociedades: la principal fuente de demanda; Kit Digital cerrado"),
  ("E", "Económico", "<b>13.698</b> bares y restaurantes en la provincia; rentabilidad <b>−0,9 %</b>; IPC del <b>4,9 %</b>"),
  ("S", "Social", "El <b>81,6 %</b> de las empresas tiene dos asalariados o menos: el cliente no tiene informático"),
  ("T", "Tecnológico", "Windows 10 sin soporte; la digitalización se quedó en el cobro, no en la cocina"),
  ("A", "Ambiental", "Retirada de los equipos viejos como RAEE; bisfenol A en el papel térmico; ticket electrónico"),
  ("L", "Legal", "Verifactu también para quien hace el software (hasta <b>150.000 €</b>); encargado del tratamiento (RGPD)")]], 3, "card pestel")}"""))

# Lab 2 (tras el factor legal del PESTEL)
S.append(lab("Simulación: Verifactu, la cadena de facturas", "verifactu.html"))

# 7 · Punto 3.2: micro
S.append(("", f"""
{punto("3.2", "Factores microeconómicos")}
<div class="grid c3">
 <div class="card"><h3>Clientes</h3>{lista(["Hamburguesería y comida rápida: prioridad <b>1</b>", "Bar de barrio: volumen de mercado", "Restaurante de mantel: tercera", "Cadenas: ya tienen su sistema, fuera de mercado"])}</div>
 <div class="card"><h3>Proveedores</h3>{lista(["Mayorista de informática: dependencia <b>alta</b>", "Repositorio y copias, operadoras y gestoría: media", "Aseguradora: baja", "Sin almacén: los equipos se compran con el anticipo"])}</div>
 <div class="card tint"><h3>Competencia</h3>{lista(["Cobran <b>por terminal o por pantalla</b>; la de cocina, casi siempre aparte", "Last.app con pantalla de cocina: <b>85 €/mes</b>, 10.700 € en diez años", "ServiPass: <b>1.800 €</b> por diez años", "Competencia monopolística: cercanía y confianza"])}</div>
</div>"""))

# 8 · Punto 4: modelo de negocio (barras HTML animadas)
PROYECTO = [("Equipos (20 % de margen)", 3850, "#E67E22"), ("Instalación y formación", 1800, "#D35400"),
            ("Licencia: derecho de uso", 900, "#27AE60"), ("Licencia: soporte en diez años", 900, "#7F8C8D")]
S.append(("", f"""
{punto(4, "Modelo de negocio: un proyecto tipo de 7.450 €")}
<div class="barras g">{''.join(f'<span class="id">{round(v / 74.5)} %</span><div class="barra"><i style="width:{v / 74.5 * 1.5:.1f}%;background:{c}"></i><b>{v:,} €</b></div><span>{t}</span>'.replace(',', '.') for t, v, c in PROYECTO)}</div>
<div class="tras-barras">{tarjetas([f'<b class="num">{n}</b><span>{t}</span>' for n, t in [("3.340 €", "de margen por instalación"), ("18,5", "instalaciones al año: punto muerto"), ("53.229 €", "antes de impuestos el tercer año (−1.589 € el primero)")]], 3, "card stat")}</div>
<p class="nota">Escenario: 18, 24 y 30 instalaciones en los años 1 a 3. El soporte se cobra al instalar, pero cuenta como ingreso en diez años: 90 € por cliente y año (Resolución del ICAC de 10/02/2021).</p>"""))


# 9 · Punto 4.1 y 4.2
S.append(("", f"""
{punto("4.1 · 4.2", "Financiación y salarios")}
<div class="grid c2">
 <div class="card"><h3>Financiación · 25.000 €</h3>{lista(["Equipos de trabajo, fianza y, sobre todo, un <b>colchón de tres meses</b> de gastos fijos", "<b>10.000 €</b> de los socios y un microcrédito de MicroBank de <b>15.000 €</b> a tres años, sin garantías", "ICO y ENISA como alternativas · Kit Digital cerrado · Digitaliza-CV pide unos 20.000 € de proyecto", "El anticipo del 50 % paga los equipos de cada cliente"])}</div>
 <div class="card tint"><h3>Salarios: convenio estatal TIC</h3>
  <div class="barras s"><span class="id">C3</span><div class="barra"><i style="width:100%"></i><b>24.105 €</b></div><span>cada socio</span>
  <span class="id">D1</span><div class="barra"><i style="width:85%;background:#D35400"></i><b>20.436 €</b></div><span>primer técnico</span>
  <span class="id">SMI</span><div class="barra"><i style="width:71%;background:#aaa"></i><b>17.094 €</b></div><span>mínimo legal</span></div>
  <p>XIX Convenio de consultoría y tecnologías de la información, área 3 (BOE-A-2026-9024). Coste de los dos socios: <b>55.411 €/año</b>. Se contrata al pasar de 30 instalaciones al año.</p></div>
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
  "Viable pero ajustada: punto muerto en <b>18,5 instalaciones</b>; −1.589 € el primer año, 25.238 € y 53.229 € los dos siguientes.",
  "El entorno pone fecha: <b>Verifactu el 1/1/2027</b>, Windows 10 sin soporte y una cocina que sigue en papel.",
  "<b>1.800 €</b> de licencia frente a 10.700 € de suscripción: competir en precio, no en funciones, y crecer según el soporte."], 1))}</div>"""))

# 13 · Bibliografía
S.append(("dark", f"""
{punto(8, "Bibliografía")}
<div class="grid c3 bib">
 <div class="card oscura"><h3>Sector y empresas</h3>{lista(["INE (2025) · Profesional Horeca (2025) · Hosteltur (2026)", "Cegid (2023) · capital-riesgo.es (2022, 2023) · Taylor (2023)", "El Periòdic (2025) · Riches Manuel y Roca (2026)"])}</div>
 <div class="card oscura"><h3>Finanzas y trabajo</h3>{lista(["XIX Convenio TIC (BOE-A-2026-9024) · RD 126/2026 (SMI)", "Cámara de España (2022) · ICO (s.f.) · Intelectium (s.f.)", "Billin (2026) · idealista/news (2026) · Digitaliza CV (2026)"])}</div>
 <div class="card oscura"><h3>Mercado y normativa</h3>{lista(["idealista, Fotocasa, Habitaclia y Nuroa (2026)", "Garrigues (2025) · Microsoft (2025) · L'Express Franchise (2026)", "Ley 11/2021 · RD 1007/2023 · RGPD · Resolución del ICAC (2021)"])}</div>
</div>
<p class="pie">47 referencias en formato APA (7.ª ed.) en el punto 8 del informe.</p>"""))

# 14 · Cuestionario
S.append(("lab quiz", """
<h2><span class="pt">¿?</span>Tres preguntas para terminar</h2>
<div id="quiz"></div>"""))


CSS = """
:root{--osc:#23272b;--nar:#e67e22;--nar2:#fdebd9;--txt:#2b2b2b;--gris:#6b6b6b;--claro:#f4f4f4;--rojo:#c0392b;--verde:#27ae60}
*{box-sizing:border-box;margin:0}
html,body{height:100%;background:#111;font-family:Arial,Helvetica,sans-serif;color:var(--txt)}
#deck{position:fixed;inset:0;display:grid;place-items:center}
.slide{position:absolute;width:1280px;height:720px;background:#fff;padding:44px 58px;display:none;transform-origin:center;overflow:hidden}
.slide.on,.slide.sale{display:block}
.slide.dark{background:var(--osc);color:#fff}
h1.big{font-size:54px;line-height:1.1;margin-top:40px;max-width:760px}
h2{font-size:32px;margin-bottom:26px;display:flex;align-items:center;gap:16px}
.pt{flex:none;background:var(--nar);color:#fff;border-radius:10px;padding:4px 14px;font-size:22px;min-width:52px;text-align:center}
.pt.lab{background:var(--osc);letter-spacing:.06em}.dark .pt{background:var(--nar)}
h3{font-size:20px;margin-bottom:12px}
.sub{font-size:24px;color:var(--nar);margin-top:16px;max-width:760px}
.pie{position:absolute;left:58px;bottom:44px;font-size:15px;color:#ccc;line-height:1.7;max-width:1100px}
.badge{width:76px;height:76px;border-radius:50%;background:var(--nar);display:grid;place-items:center;font-weight:bold;font-size:22px;margin-top:40px}
.grid{display:grid;gap:20px}.c2{grid-template-columns:1fr 1fr}.c3{grid-template-columns:repeat(3,1fr)}.c4{grid-template-columns:repeat(4,1fr)}
.card{background:var(--claro);border-radius:12px;padding:20px 22px;font-size:17px;line-height:1.4}
.card p{color:var(--gris);margin-top:14px;font-size:17px;line-height:1.4}
.card.tint{background:var(--nar2)}.card.oscura{background:#2f353b;color:#fff}.card.oscura p,.card.oscura li{color:#eee}
.card.pestel{min-height:170px;padding-top:16px}.letra{display:inline-block;width:40px;height:40px;border-radius:10px;background:var(--nar);color:#fff;font-size:24px;text-align:center;line-height:40px;margin-bottom:10px}
.stat{display:flex;flex-direction:column;gap:8px;min-height:120px;justify-content:center}.stat span{font-size:15px;color:var(--gris)}
.num{font-size:48px;color:var(--nar);line-height:1}.num.neg{color:var(--rojo)}.num.m{font-size:28px}.num.xl{font-size:64px;display:block;margin:10px 0}
.minis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:6px 0 4px}.minis div{display:flex;flex-direction:column;gap:6px}.minis span{font-size:13px;color:var(--gris)}.oscura .minis span{color:#ccc}
.lead{font-size:19px;line-height:1.45;margin-top:22px}
.nota{font-size:13px;color:var(--gris);position:absolute;left:58px;bottom:28px;right:120px}
.split{display:grid;grid-template-columns:1.9fr 1fr;gap:28px;align-items:start}.split img{width:100%}
.split.mitad{grid-template-columns:1.15fr 1fr;margin-top:18px}.split.ancho2{grid-template-columns:1.1fr 1fr}
img.ancho{width:100%;display:block;margin-bottom:18px}
.banda{background:var(--osc);color:#fff;font-size:19px;padding:16px 24px;border-radius:12px;margin-top:20px}.banda b{color:var(--nar)}
.fila{display:flex;gap:16px;align-items:center}.fila b{font-size:18px}.fila p{font-size:19px;color:inherit;margin:0;line-height:1.35}.fila small{display:block;font-size:14px;color:var(--gris)}
.dot{flex:none;width:44px;height:44px;border-radius:50%;background:var(--nar);color:#fff;display:grid;place-items:center;font-weight:bold;font-size:18px}
.dot.rojo{background:var(--rojo)}.dot.g{width:52px;height:52px;font-size:22px}
.ocho{display:grid;grid-template-columns:1fr 1fr;gap:18px 40px}.ocho .fila p{font-size:21px}
.pasos{display:flex;flex-direction:column;gap:30px;margin-top:10px}.pasos p{font-size:21px}.dark .pasos b{color:var(--nar)}
.barras{display:grid;grid-template-columns:70px 1fr 300px;gap:14px 16px;align-items:center;font-size:18px}
.barras .id{color:var(--gris);font-weight:bold;text-align:right}.barra{display:flex;align-items:center;gap:10px}
.barra i{display:block;height:28px;background:var(--nar);border-radius:4px}.barra b{font-size:16px;white-space:nowrap}
.barras.g{font-size:22px;gap:24px 18px;grid-template-columns:80px 1fr 360px;margin-top:10px}.barras.g .barra i{height:40px}.barras.g .barra b{font-size:19px}
.barras.s{grid-template-columns:92px 1fr 120px;font-size:15px;gap:10px 12px}.barras.s .barra i{height:22px}.barras.s .barra b{font-size:14px}
ul{padding-left:20px}li{margin:9px 0;font-size:17px;line-height:1.35}
.num-pag{position:absolute;right:40px;bottom:20px;font-size:14px;color:#999}
.slide.labframe{padding:0}.labbar{height:44px;background:var(--osc);color:#fff;display:flex;justify-content:space-between;align-items:center;padding:0 18px;font-size:15px}
.labbar span{display:flex;gap:10px;align-items:center}.labbar a{color:var(--nar);font-size:14px}.labbar button{font:inherit;font-size:14px;padding:5px 12px;border-radius:8px;border:1px solid #666;background:#2f353b;color:#fff;cursor:pointer}.labbar button:hover{background:var(--nar);border-color:var(--nar)}
.slide.labframe iframe{display:block;width:1280px;height:676px;border:0;background:#fff}.slide.labframe .num-pag{color:#aaa;bottom:auto;top:14px;right:auto;left:50%;translate:-50% 0}
.bib li{font-size:15px}
.tras-barras{margin-top:36px}
.ciclo{display:grid;grid-template-columns:repeat(7,1fr);gap:12px;margin-bottom:24px}.ciclo .card{padding:14px 12px;display:flex;flex-direction:column;gap:8px}
.ciclo .card b{font-size:17px}.ciclo .card span:last-child{color:var(--gris);font-size:14px;line-height:1.3}.ciclo .dot{width:34px;height:34px;font-size:15px}
h3.sec{font-size:19px;color:var(--gris);margin:0 0 14px}.lema{font-size:22px!important;font-weight:bold;color:var(--txt)!important;margin:2px 0 6px!important}
/* Laboratorios */
.mandos{display:flex;flex-direction:column;gap:14px}
.mandos label{display:flex;flex-direction:column;gap:6px;font-size:16px;color:var(--txt)}.mandos output{float:right;font-weight:bold;color:var(--nar);font-size:18px}
.mandos label:not(.check){position:relative}.mandos label:not(.check) output{position:absolute;right:0;top:-2px}
input[type=range]{width:100%;accent-color:var(--nar);height:28px}
label.check{flex-direction:row;align-items:center;gap:10px}label.check input{width:20px;height:20px;accent-color:var(--nar)}
.presets{display:flex;flex-wrap:wrap;gap:8px}.presets button,.quiz button{font:inherit;font-size:14px;padding:8px 12px;border-radius:8px;border:1px solid #ccc;background:#fff;cursor:pointer;transition:background .2s,transform .15s}
.presets button:hover{background:var(--nar2);transform:translateY(-2px)}.presets button.on{background:var(--nar);color:#fff;border-color:var(--nar)}
.peq{font-size:14px;color:var(--gris);margin-top:4px}
.panel{background:var(--claro);border-radius:14px;padding:22px 26px;min-height:520px}
.res{display:flex;flex-direction:column}.res span{font-size:15px;color:var(--gris)}.res em{font-style:normal;font-size:18px;color:var(--txt)}
.res .num.xl.rojo{color:var(--rojo)}.res .num.xl.verde{color:var(--verde)}
.apilada{display:flex;height:34px;border-radius:8px;overflow:hidden;margin:18px 0 12px;background:#ddd}.apilada i{display:block;height:100%;transition:flex-basis .5s cubic-bezier(.2,.7,.2,1);flex:0 0 0}
table.mini{width:100%;border-collapse:collapse;font-size:14px}table.mini td{padding:5px 6px;border-bottom:1px solid #ddd}table.mini td:last-child{text-align:right;white-space:nowrap}
table.mini tr.tot td{font-weight:bold;border-top:2px solid #999;border-bottom:0}table.esc{margin-top:4px}
.semaforo{display:flex;gap:14px;margin:22px 0}.semaforo i{width:46px;height:46px;border-radius:50%;background:#ddd;transition:background .3s,box-shadow .3s}
.semaforo.v i:nth-child(1){background:var(--verde);box-shadow:0 0 18px var(--verde)}.semaforo.a i:nth-child(2){background:#f1c40f;box-shadow:0 0 18px #f1c40f}.semaforo.r i:nth-child(3){background:var(--rojo);box-shadow:0 0 18px var(--rojo)}
/* Cuestionario */
#quiz{max-width:980px}.q{font-size:24px;margin:10px 0 22px;line-height:1.35}.qn{font-size:14px;color:var(--gris);text-transform:uppercase;letter-spacing:.06em}
.ops{display:grid;grid-template-columns:1fr 1fr;gap:14px}.ops button{text-align:left;font-size:18px;padding:16px 18px;border-radius:12px;background:#fff;border:2px solid #ddd}
.ops button:hover{border-color:var(--nar);transform:translateY(-2px)}.ops button.ok{background:#e9f7ef;border-color:var(--verde)}.ops button.ko{background:#fdecea;border-color:var(--rojo)}.ops button:disabled{cursor:default}
.ops button.ok{animation:pop .4s cubic-bezier(.3,1.6,.5,1)}.ops button.ko{animation:tiembla .4s}
@keyframes tiembla{0%,100%{translate:0}25%{translate:-8px 0}75%{translate:8px 0}}
.fb{margin-top:18px;font-size:17px;line-height:1.45;min-height:70px;color:var(--txt)}.fb b{color:var(--nar)}
.qbar{display:flex;align-items:center;justify-content:space-between;margin-top:14px}.qbar .pts{font-size:15px;color:var(--gris)}.qbar button{font-size:16px;padding:10px 20px;background:var(--nar);color:#fff;border:0}
.final{text-align:center;padding-top:40px}.final .num{font-size:120px;display:block;margin:10px 0 20px}.final p{font-size:22px;margin-bottom:28px}
.conf{position:absolute;inset:0;pointer-events:none;overflow:hidden}.conf i{position:absolute;top:-20px;width:10px;height:16px;animation:cae2 2.6s linear both}
@keyframes cae2{to{translate:0 760px;rotate:720deg;opacity:.2}}
#notas{position:fixed;left:0;right:0;bottom:0;background:#fffbe8;color:#222;font-size:19px;line-height:1.55;padding:14px 28px 18px;display:none;max-height:48vh;overflow:auto;border-top:3px solid var(--nar);white-space:pre-wrap}
#notas .cab{display:block;font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:#8a5a14;margin-bottom:8px;white-space:normal}
#notas.on{display:block}
#ayuda{position:fixed;right:12px;top:10px;color:#888;font-size:12px}body.lab #ayuda{display:none}
#reloj{position:fixed;left:12px;top:10px;color:#bbb;font-size:13px;font-variant-numeric:tabular-nums;display:none;z-index:11}#reloj.on{display:block}
@media print{@page{size:1280px 720px;margin:0}html,body{background:#fff}#deck{position:static;display:block}
 .slide{display:block!important;position:relative;transform:none!important;page-break-after:always}#notas,#ayuda{display:none!important}}
/* ---- Movimiento ---- */
.slide.on{z-index:2;animation:entra .55s cubic-bezier(.2,.7,.2,1) both}
.slide.sale{z-index:1;pointer-events:none;animation:sale .5s ease both}
body[data-dir=atras] .slide.on{animation-name:entraAtras}
body[data-dir=atras] .slide.sale{animation-name:saleAtras}
@keyframes entra{from{opacity:0;translate:90px 0;scale:.985}to{opacity:1;translate:0 0;scale:1}}
@keyframes entraAtras{from{opacity:0;translate:-90px 0;scale:.985}to{opacity:1;translate:0 0;scale:1}}
@keyframes sale{to{opacity:0;translate:-90px 0}}
@keyframes saleAtras{to{opacity:0;translate:90px 0}}
.slide.on .rev{animation:sube .85s cubic-bezier(.2,.8,.2,1) both;animation-delay:calc(var(--i,0)*95ms + 250ms)}
@keyframes sube{from{opacity:0;translate:calc(var(--dx,0px)*var(--k,1)) var(--dy,36px);scale:var(--sc,1)}to{opacity:1;translate:0 0;scale:1}}
body[data-dir=atras] .slide.on .rev{--k:-1}
.slide.sale .rev{animation:salir .42s ease both;animation-delay:calc(var(--i,0)*22ms)}
@keyframes salir{to{opacity:0;translate:calc(var(--dx,0px)*var(--k,1)*-.7) -16px}}
body[data-dir=atras] .slide.sale .rev{--k:-1}
.slide.portada{background:linear-gradient(115deg,#23272b 0%,#2f353b 45%,#23272b 100%);background-size:220% 220%}
.slide.on.portada{animation:entra .55s cubic-bezier(.2,.7,.2,1) both,flujo 16s ease-in-out infinite}
body[data-dir=atras] .slide.on.portada{animation-name:entraAtras,flujo}
@keyframes flujo{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.logo{position:absolute;right:90px;top:110px;width:340px;border-radius:30px;box-shadow:0 20px 60px rgba(0,0,0,.45)}
.slide.on .logo.rev{animation:cae .9s cubic-bezier(.3,1.4,.5,1) .35s both,flota 5s ease-in-out 1.5s infinite}
@keyframes cae{from{opacity:0;translate:0 -140px;rotate:-6deg}to{opacity:1;translate:0 0;rotate:0deg}}
@keyframes flota{0%,100%{transform:translateY(0)}50%{transform:translateY(-12px)}}
.slide.on .badge.rev{animation:pop .6s cubic-bezier(.3,1.6,.5,1) .2s both,anillo 2.6s ease-out 1s infinite}
@keyframes pop{from{opacity:0;scale:0}to{opacity:1;scale:1}}
@keyframes anillo{0%{box-shadow:0 0 0 0 rgba(230,126,34,.55)}70%,100%{box-shadow:0 0 0 22px rgba(230,126,34,0)}}
.slide.on .barra i{transform-origin:left;animation:crece .9s cubic-bezier(.2,.7,.2,1) both;animation-delay:calc(var(--i,0)*120ms + 500ms)}
.slide.on .barra b{animation:sube .5s ease both;animation-delay:calc(var(--i,0)*120ms + 1200ms)}
@keyframes crece{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.slide.on .pt{animation:pop .5s cubic-bezier(.3,1.6,.5,1) .15s both}
.slide.on .letra{animation:pop .5s cubic-bezier(.3,1.6,.5,1) both;animation-delay:calc(var(--i,0)*95ms + 500ms)}
.card{transition:transform .25s ease,box-shadow .25s ease}
.card:hover{transform:translateY(-5px);box-shadow:0 12px 26px rgba(0,0,0,.16)}
.dot{transition:scale .2s ease}.fila:hover .dot{scale:1.12}
#prog{position:fixed;top:0;left:0;right:0;height:4px;background:rgba(255,255,255,.08);z-index:10}
#prog i{display:block;height:100%;background:var(--nar);transform-origin:left;transition:transform .5s cubic-bezier(.2,.7,.2,1)}
html[data-mov="off"] *,html[data-mov="off"] *:before,html[data-mov="off"] *:after{animation:none!important;transition:none!important}
#toast{position:fixed;top:16px;left:50%;translate:-50% 0;background:#23272b;color:#fff;font-size:15px;padding:10px 18px;border-radius:10px;border:1px solid #e67e22;z-index:20;opacity:0;pointer-events:none;transition:opacity .3s;max-width:90vw;text-align:center}
#toast.on{opacity:1}
@media print{#prog{display:none}.slide,.slide *,.slide *:before{animation:none!important;transition:none!important;translate:none!important;scale:none!important}}
"""

JS = r"""
const sl=[...document.querySelectorAll('.slide')],notas=document.getElementById('notas'),prog=document.querySelector('#prog i');
const SO_QUIETO=matchMedia('(prefers-reduced-motion: reduce)').matches;
let eleccion=null;try{eleccion=localStorage.getItem('reto1_mov')}catch(e){}
const pedido=new URLSearchParams(location.search).get('movimiento');
if(pedido==='1'||pedido==='0'){eleccion=pedido==='1'?'on':'off';try{localStorage.setItem('reto1_mov',eleccion)}catch(e){}}
let quieto=eleccion?eleccion==='off':SO_QUIETO;
document.documentElement.dataset.mov=quieto?'off':'on';
let i=-1,tok=0,salida=null;
const SEL='h1,h2,.badge,.logo,.sub,.pie,.lead,.nota,.banda,.card,.fila,.num.xl,.split>img,img.ancho,.barras>*,#quiz,.labbar,iframe';
sl.forEach(s=>{const c=[...s.querySelectorAll(SEL)];
 c.filter(a=>!c.some(o=>o!==a&&o.contains(a))).forEach((el,k)=>{el.classList.add('rev');
  const st=el.style,p=el.parentElement,hijo=[...p.children].indexOf(el);let dx=0,dy=36,sc=1;
  if(/^H[12]$/.test(el.tagName)){dx=-80;dy=0}
  else if(el.matches('.sub,.lead')){dx=-50;dy=12}
  else if(el.tagName==='IMG'){sc=.9;dy=34}
  else if(p.classList.contains('grid')){const n=+(/c(\d)/.exec(p.className)||[0,3])[1];dx=(hijo%n-(n-1)/2)*80;dy=50}
  else if(el.closest('.pasos,.ocho')){dx=-60;dy=0}
  else if(p.classList.contains('barras')){dx=hijo%3===2?0:-50;dy=0}
  st.setProperty('--i',p.classList.contains('barras')?Math.floor(hijo/3):Math.min(k,12));
  st.setProperty('--dx',dx+'px');st.setProperty('--dy',dy+'px');st.setProperty('--sc',sc)})});
const CIFRA=/^([−-]?)(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?(\s*(?:%|€|M€))?$/;
const fmtN=(x,dec)=>{const[a,b]=Math.abs(x).toFixed(dec).split('.');return (x<0?'−':'')+a.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(b?','+b:'')};
function contar(el,t){
 if(el.closest('.panel'))return;
 const f=el.dataset.final||(el.dataset.final=el.textContent.trim()),m=f.match(CIFRA);el.textContent=f;
 if(!m||quieto)return;
 const dec=(m[3]||'').length,val=parseFloat(m[2].replace(/\./g,'')+(dec?'.'+m[3]:'')),suf=m[4]||'';
 const r=el.closest('.rev'),ini=performance.now()+250+85*(r?parseInt(r.style.getPropertyValue('--i'))||0:0)+150;
 el.textContent=fmtN(0,dec)+suf;
 const paso=now=>{if(t!==tok){el.textContent=f;return}
  const p=Math.min(1,Math.max(0,(now-ini)/1300));{const v=fmtN(val*(1-Math.pow(1-p,3)),dec);el.textContent=p<1?(/[1-9]/.test(v)?m[1]:'')+v+suf:f}
  if(p<1)requestAnimationFrame(paso)};
 requestAnimationFrame(paso)}
const restaura=v=>v.querySelectorAll('.num[data-final]').forEach(e=>e.textContent=e.dataset.final);
const mmss=s=>{s=Math.round(Math.abs(s));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')};
const TOTAL=sl.reduce((a,x)=>a+parseFloat(x.dataset.min),0);
function pinta(){const s=sl[i],cab=document.createElement('span');cab.className='cab';
 cab.textContent=`Diapositiva ${i+1} de ${sl.length} · ${s.dataset.min} min · acumulado ${mmss(s.dataset.acum*60)} de ${mmss(TOTAL*60)}`;
 notas.replaceChildren(cab,document.createTextNode(s.dataset.notas));notas.scrollTop=0}
const reloj=document.getElementById('reloj');let t0=0,acum=0,corre=false;
function tic(){const t=acum+(corre?(performance.now()-t0)/1000:0),fin=parseFloat(sl[i].dataset.acum)*60,ini=fin-parseFloat(sl[i].dataset.min)*60,
 d=t<ini?t-ini:t>fin?t-fin:0;
 reloj.textContent=`${mmss(t)} / ${mmss(TOTAL*60)} · diapositiva ${i+1}: ${mmss(ini)}–${mmss(fin)} · ${d===0?'en hora':mmss(d)+(d>0?' de retraso':' de adelanto')}`}
setInterval(tic,500);
function fit(){const k=Math.min(innerWidth/1280,innerHeight/720);sl.forEach(s=>s.style.transform=`scale(${k})`)}
function ver(n){n=Math.max(0,Math.min(sl.length-1,n));if(n===i)return;
 document.body.dataset.dir=n<i?'atras':'adelante';
 if(i>=0){const v=sl[i];restaura(v);v.classList.remove('on');
  if(!quieto){v.classList.add('sale');clearTimeout(salida);salida=setTimeout(()=>sl.forEach(s=>s.classList.remove('sale')),650)}}
 i=n;sl[i].classList.remove('sale');sl[i].classList.add('on');
 prog.style.transform=`scaleX(${(i+1)/sl.length})`;
 pinta();try{history.replaceState(null,'','#'+(i+1))}catch(e){}
 const t=++tok;sl[i].querySelectorAll('.num').forEach(el=>contar(el,t));
 document.body.classList.toggle('lab',sl[i].classList.contains('labframe'));
 sl[i].querySelectorAll('iframe[data-src]').forEach(f=>{f.src=f.dataset.src;f.removeAttribute('data-src')});
 if(sl[i].classList.contains('quiz'))quizInicio()}
const toast=document.getElementById('toast');let tt=null;
function aviso(t,ms){toast.textContent=t;toast.classList.add('on');clearTimeout(tt);tt=setTimeout(()=>toast.classList.remove('on'),ms||2200)}
function alterna(){quieto=!quieto;document.documentElement.dataset.mov=quieto?'off':'on';
 try{localStorage.setItem('reto1_mov',quieto?'off':'on')}catch(e){}
 aviso(quieto?'Movimiento desactivado':'Movimiento activado');
 const s=sl[i];s.classList.remove('on','sale');void s.offsetWidth;s.classList.add('on');
 const t=++tok;s.querySelectorAll('.num').forEach(el=>contar(el,t))}
addEventListener('beforeprint',()=>{tok++;sl.forEach(restaura)});
// Dentro de un laboratorio o del cuestionario, el teclado y el ratón son suyos: las flechas mueven los deslizadores, no las diapositivas.
const interactivo=el=>el&&el.closest&&el.closest('#quiz,.labbar,iframe,input,button');
addEventListener('keydown',ev=>{if(interactivo(ev.target)&&['ArrowRight','ArrowLeft',' '].includes(ev.key))return;
 if(['ArrowRight','PageDown',' '].includes(ev.key)){ev.preventDefault();ver(i+1)}
 else if(['ArrowLeft','PageUp'].includes(ev.key))ver(i-1);else if(ev.key==='Home')ver(0);else if(ev.key==='End')ver(sl.length-1);
 else if(ev.key==='n'||ev.key==='N')notas.classList.toggle('on');
 else if(ev.key==='m'||ev.key==='M')alterna();
 else if(ev.key==='T'){acum=0;t0=performance.now();tic()}
 else if(ev.key==='t'){if(corre){acum+=(performance.now()-t0)/1000;corre=false}else{t0=performance.now();corre=true;reloj.classList.add('on')}tic()}
 else if(ev.key==='f'||ev.key==='F'){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()}});
document.getElementById('deck').addEventListener('click',ev=>{if(interactivo(ev.target))return;ver(ev.clientX>innerWidth/3?i+1:i-1)});
let x0=null;addEventListener('touchstart',e=>{x0=interactivo(e.target)?null:e.touches[0].clientX});addEventListener('touchend',e=>{if(x0===null)return;const d=e.changedTouches[0].clientX-x0;if(Math.abs(d)>40)ver(d<0?i+1:i-1);x0=null});

/* ---------- Cuestionario ---------- */
const PREG=[
 {q:'¿Cuántas instalaciones al año necesita ServiPass para no perder dinero?',o:['12','18,5','24','30'],ok:1,
  x:'<b>Unas 18,5</b>: cada instalación deja 3.340 € de margen y los costes fijos que deben cubrir son unos 61.700 €. Con 18 instalaciones, el primer año cierra con −1.589 €.'},
 {q:'Si ServiPass vendiera un programa de facturación que no cumple Verifactu, ¿a qué sanción se expondría?',o:['A ninguna: la multa es para el restaurante','50.000 € por ejercicio','150.000 € por ejercicio y por tipo de programa','Al cierre del local'],ok:2,
  x:'<b>150.000 € por ejercicio y por cada tipo de programa</b> (art. 201 bis de la Ley General Tributaria); el restaurante que lo usa, 50.000 €. Por eso el TPV de ServiPass cumple Verifactu antes de vender la primera licencia.'},
 {q:'¿Cuánto pagaría en diez años un local por el plan básico de Last.app con su pantalla de cocina?',o:['1.800 €','4.250 €','10.700 €','25.000 €'],ok:2,
  x:'<b>10.700 €</b>: 85 € al mes durante diez años más 500 € de alta, solo por el software. La licencia de ServiPass del mismo periodo cuesta 1.800 €.'}];
let qi=0,qp=0;const Q=document.getElementById('quiz');
function quizInicio(){qi=0;qp=0;quizPinta()}
function quizPinta(){if(qi>=PREG.length){quizFin();return}
 const p=PREG[qi];Q.innerHTML=`<div class="qn">Pregunta ${qi+1} de ${PREG.length} · aciertos: ${qp}</div><div class="q">${p.q}</div>
  <div class="ops">${p.o.map((o,k)=>`<button data-k="${k}">${String.fromCharCode(65+k)}. ${o}</button>`).join('')}</div><div class="fb"></div><div class="qbar"><span class="pts"></span></div>`;
 Q.querySelectorAll('.ops button').forEach(b=>b.addEventListener('click',()=>{const k=+b.dataset.k,ok=k===p.ok;if(ok)qp++;
  Q.querySelectorAll('.ops button').forEach(x=>{x.disabled=true;if(+x.dataset.k===p.ok)x.classList.add('ok')});if(!ok)b.classList.add('ko');
  Q.querySelector('.fb').innerHTML=(ok?'✔ Correcto. ':'✘ No. ')+p.x;
  const sig=document.createElement('button');sig.textContent=qi<PREG.length-1?'Siguiente pregunta →':'Ver resultado';sig.addEventListener('click',()=>{qi++;quizPinta()});
  Q.querySelector('.qbar').append(sig)}))}
function quizFin(){const msg=qp===3?'¡Pleno! Habéis escuchado de verdad.':qp===2?'Muy bien: solo una se ha escapado.':qp===1?'Una de tres: el informe tiene las respuestas.':'Ninguna… toca releer el informe.';
 Q.innerHTML=`<div class="final"><div class="qn">Resultado</div><b class="num">${qp} / 3</b><p>${msg}</p><button class="otra">Repetir el cuestionario</button></div>`;
 Q.querySelector('.otra').addEventListener('click',quizInicio);
 if(!quieto&&qp>=2){const c=document.createElement('div');c.className='conf';for(let k=0;k<80;k++){const i=document.createElement('i');i.style.left=Math.random()*100+'%';i.style.background=['#e67e22','#27ae60','#f1c40f','#3498db'][k%4];i.style.animationDelay=Math.random()*1.2+'s';i.style.animationDuration=(2+Math.random()*1.5)+'s';c.append(i)}
  sl[i].append(c);setTimeout(()=>c.remove(),4500)}}

addEventListener('resize',fit);fit();ver((parseInt(location.hash.slice(1))||1)-1);
if(SO_QUIETO&&!eleccion)aviso('Tu sistema tiene las animaciones desactivadas. Pulsa M para activar el movimiento.',9000);
"""

cuerpo = "".join(
    f'<section class="slide {c}" data-notas="{e(GUION[k]["texto"])}" data-min="{GUION[k]["min"]}" '
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
<body><div id="prog"><i></i></div><div id="deck">{cuerpo}</div><div id="notas"></div>
<div id="toast"></div><div id="reloj"></div><div id="ayuda">← → avanzar · N guion · T cronómetro · M movimiento · F pantalla completa</div><script src="js/presentacion.js"></script></body></html>"""
(ENTREGA / "presentacion.html").write_text(doc, encoding="utf-8")
MIN = sum(d["min"] for d in GUION.values())
(ENTREGA / "LEEME.txt").write_text(f"""Reto 1 · Proyecto Intermodular I · ServiPass
Riches Manuel y Roca · 1.º CFGS ASIR · IES Conselleria · octubre de 2026

Descomprimir la carpeta entera y abrir los ficheros con cualquier navegador (no hace falta conexión ni servidor).

presentacion.html      Presentación ({len(S)} diapositivas, {MIN:g} min).
                       Teclas: flechas o espacio para avanzar, N guion del orador, T cronómetro de ensayo,
                       M animaciones sí/no, F pantalla completa. Tres diapositivas cargan los laboratorios (se pueden abrir
                       también en una pestaña aparte); la última es un cuestionario de 3 preguntas.
css/presentacion.css   Estilos y animaciones de la presentación.
js/presentacion.js     Navegación, contadores, cronómetro y cuestionario.
fig/                   Figuras del informe (organigrama de ServiPass; flujo de la comanda y red actual del
                       cliente piloto, Burglar King; costes) y logo de ServiPass.
laboratorios/          Tres simulaciones sobre Burglar King, el cliente piloto (abrir laboratorios/index.html);
                       cada una se lanza con «Simular» y tiene modo manual:
  red.html             Lab 1 · La red actual frente a la segmentada: misma batería de pings en los dos escenarios.
  verifactu.html       Lab 2 · Cadena de facturas con SHA-256: alteración detectada y corrección con rectificativa.
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
