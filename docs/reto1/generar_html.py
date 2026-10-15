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
LOGO = "fig/logo.svg"
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
<img class="logo" src="{LOGO}" alt="Logo de Burglar King">
<h1 class="big">Burglar King,<br>por dentro y por fuera</h1>
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
{punto(1, "Burglar King: una hamburguesería de barrio")}
{tarjetas([f'<b class="num">{n}</b><span>{t}</span>' for n, t in [("13", "mesas · 44 plazas"), ("4", "personas en plantilla"), ("45.000 €", "ventas al mes sin IVA"), ("4", "canales: sala, barra, llevar y reparto")]], 4, "card stat")}
<div class="split mitad"><img src="{img('organigrama.png')}" alt="Organigrama de Burglar King">
<div class="card tint"><h3>Burjassot, junto al campus</h3>{lista(["Restauración independiente: el <b>93 %</b> de los locales", "Microempresa: nadie sabe de informática", "El encargado es dirección, compras, caja… <b>y el informático</b>", "Empresa ficticia; datos del sector reales"])}</div></div>"""))

# 4 · Punto 1: flujo e infraestructura
S.append(("", f"""
{punto(1, "El dato llega cuando el cliente ya se va")}
<img class="ancho" src="{img('flujo_comanda.png')}" alt="Flujo actual de una comanda">
{tarjetas([f'<div class="fila"><span class="dot rojo">{k}</span><b>{t}</b></div><p>{d}</p>' for k, (t, d) in enumerate([
  ("La comanda no entra en ningún sistema", "hasta que se teclea para cobrar"),
  ("TPV de 2015 con Windows 10", "sin soporte desde octubre de 2025, sin copias"),
  ("Una sola red para todo", "caja, cámaras y móviles de los clientes juntos")], 1)], 3)}"""))

# Lab 1 (tras la red actual)
S.append(lab("Simulación: la red actual frente a la red segmentada", "red.html"))

# 5 · Punto 2: empresa de referencia
S.append(("", f"""
{punto(2, "Empresa de referencia: Hundred Burgers (y Goiko como contrapunto)")}
<div class="grid c2">
 <div class="card tint"><h3>Hundred Burgers · València, 2020</h3>
  <div class="minis"><div><b class="num m">8</b><span>locales</span></div><div><b class="num m">25 M€</b><span>ingresos</span></div><div><b class="num m">20 €</b><span>ticket medio</span></div><div><b class="num m">35 %</b><span>en reparto</span></div></div>
  <p>Mejor hamburguesa del mundo en 2024. En octubre de 2025 el fondo Buenavista compró el 80 %; los fundadores siguen al frente.</p></div>
 <div class="card oscura"><h3>Goiko · Madrid, 2013</h3>
  <div class="minis"><div><b class="num m">117</b><span>restaurantes</span></div><div><b class="num m neg">−11,2 %</b><span>ventas 2025</span></div><div><b class="num m neg">−36,4 M€</b><span>pérdidas 2025</span></div><div><b class="num m">1.737</b><span>empleados</span></div></div>
  <p>«Disminución del tráfico» y «menores niveles de consumo»: el mercado de la hamburguesa ya no admite a todos.</p></div>
</div>
<div class="banda">Lo que toma Burglar King: carta corta · reparto como tercio del negocio · pedido digital desde el primer día · costes controlados</div>"""))

# 6 · Punto 3.1: PESTEL
S.append(("", f"""
{punto("3.1", "Factores macroeconómicos (PESTEL)")}
{tarjetas([f'<b class="letra">{l}</b><h3>{t}</h3><p>{d}</p>' for l, t, d in [
  ("P", "Político", "Verifactu el <b>1/1/2027</b> para sociedades; Kit Digital cerrado en 2025"),
  ("E", "Económico", "El sector vende más y gana menos: rentabilidad <b>−0,9 %</b>; SMI 2026 de <b>1.221 €</b>"),
  ("S", "Social", "65-70 % de pagos digitales; el <b>62 %</b> descarta un local por una mala reseña"),
  ("T", "Tecnológico", "Windows 10 sin soporte; la digitalización se quedó en el cobro, no en la cocina"),
  ("A", "Ambiental", "Bisfenol A en el papel térmico; impuesto a los envases de plástico; RAEE"),
  ("L", "Legal", "Ley antifraude, RGPD, alérgenos, registro de jornada, convenio provincial")]], 3, "card pestel")}"""))

# Lab 2 (tras el factor legal del PESTEL)
S.append(lab("Simulación: Verifactu, la cadena de facturas", "verifactu.html"))

# 7 · Punto 3.2: micro
S.append(("", f"""
{punto("3.2", "Factores microeconómicos")}
<div class="grid c3">
 <div class="card"><h3>Clientes</h3>{lista(["Estudiantes <b>45 %</b>", "Familias y barrio <b>27 %</b>", "Reparto <b>18 %</b> · para llevar <b>10 %</b>", "Todos en franjas cortas: nada puede fallar en hora punta"])}</div>
 <div class="card"><h3>Proveedores</h3>{lista(["Cash and carry, carnicería y obrador", "Operadora, banco y fabricante del TPV: dependencia <b>alta</b>", "Plataformas de reparto: <b>15-30 %</b> de cada pedido"])}</div>
 <div class="card"><h3>Competencia</h3>{lista(["Cadenas con cocina en pantalla: la experiencia con la que compara el cliente", "TPV comerciales que cobran <b>por terminal y por pantalla</b>", "La oportunidad: añadir pantallas sin pagar licencias"])}</div>
</div>"""))

# 8 · Punto 4: modelo de negocio (barras HTML animadas)
PARTIDAS = [("Materia prima", 14400, "#E67E22"), ("Personal", 14800, "#D35400"), ("Alquiler", 1000, "#7F8C8D"), ("Suministros", 3600, "#95A5A6"),
            ("Comisiones de reparto", 2100, "#BDC3C7"), ("Publicidad, financiación e impuestos", 1750, "#AEB6BF"), ("Resultado antes de impuestos", 7350, "#27AE60")]
S.append(("", f"""
{punto(4, "Modelo de negocio: cada 100 € de ventas")}
<div class="barras g">{''.join(f'<span class="id">{round(v / 450)} %</span><div class="barra"><i style="width:{v / 450 * 5.2}%;background:{c}"></i><b>{v:,} €</b></div><span>{t}</span>'.replace(',', '.') for t, v, c in PARTIDAS)}</div>
<p class="nota">Ventas estimadas: 45.000 €/mes sin IVA (1.500 comensales en sala × 19,50 € · 300 en barra · 300 pedidos para llevar · 550 de reparto × 15 €). Bandas del sector: producto 28-35 %, personal 30-35 %, alquiler ≤ 10 % (Tourinews, 2025).</p>"""))


# 10 · Punto 4.1 y 4.2
S.append(("", f"""
{punto("4.1 · 4.2", "Financiación y salarios")}
<div class="grid c2">
 <div class="card"><h3>Financiación</h3>{lista(["Constituida en 2022 con <b>60.000 €</b>: 35.000 de capital y un préstamo de 25.000 (quedan 7.000)", "Proyecto tecnológico: <b>5.000-8.000 €</b>, con tesorería y, si hace falta, microcrédito de MicroBank (hasta 25.000 €, sin garantías)", "Kit Digital: cerrado en 2025 · Digitaliza-CV (IVACE): solo si hay convocatoria", "Renting descartado: el proyecto no quiere cuotas"])}</div>
 <div class="card tint"><h3>Salarios: el convenio es el mínimo</h3>
  <div class="barras s"><span class="id">Nivel III</span><div class="barra"><i style="width:61%;background:#aaa"></i><b>1.215 €</b></div><span>convenio</span>
  <span class="id">Camarero</span><div class="barra"><i style="width:100%"></i><b>2.000 €</b></div><span>Burglar King</span>
  <span class="id">Cocinero</span><div class="barra"><i style="width:106%"></i><b>2.122 €</b></div><span>Burglar King</span>
  <span class="id">Encargado</span><div class="barra"><i style="width:197%;background:#D35400"></i><b>3.950 €</b></div><span>autónomo</span></div>
  <p>Convenio de hostelería de Valencia en ultraactividad desde enero de 2026. Coste de personal: <b>14.800 €/mes</b>, el 33 % de las ventas.</p></div>
</div>"""))


# 12 · Punto 4.3 y 4.4
S.append(("", f"""
{punto("4.3 · 4.4", "Gastos materiales y el local")}
<div class="grid c3">
 <div class="card"><h3>Escandallo · hamburguesa clásica</h3>
  <table class="mini esc"><tr><td>Carne 160 g</td><td>1,52 €</td></tr><tr><td>Pan brioche</td><td>0,45 €</td></tr><tr><td>Queso, verduras y salsa</td><td>0,64 €</td></tr><tr><td>Patatas y aceite</td><td>0,38 €</td></tr><tr><td>Envase</td><td>0,25 €</td></tr><tr class="tot"><td>Coste</td><td>3,24 €</td></tr><tr class="tot"><td>Venta sin IVA</td><td>10,45 €</td></tr></table>
  <p><b class="num">31 %</b> de coste de producto</p></div>
 <div class="card"><h3>Suministros · 3.600 €/mes</h3>{lista(["Electricidad <b>1.500 €</b>: plancha, cámaras, aire", "Envases para llevar 770 € (cartón, sin plástico)", "Mantenimiento y limpieza 450 €", "Gas 280 · gestoría 180 · seguros 150 · agua 130", "Software y licencias: <b>0 €</b>"])}</div>
 <div class="card tint"><h3>El local · 120 m² en alquiler</h3>{lista(["<b>1.000 €/mes</b> + IVA: 8,30 €/m², en la media de Burjassot (7,05 €/m² en idealista)", "Fotocasa: 35 locales en oferta, de 3 a 14 €/m²", "Contrato LAU de 10 años, IPC anual, fianza de 2 meses (art. 36)", "Tasas: licencia, terraza e IBI repercutido, 400 €/mes", "Las obras de red necesitan permiso del propietario"])}</div>
</div>"""))


# 14 · Puntos 5 y 6
S.append(("", f"""
{punto("5 · 6", "Servicios prestados y publicidad")}
<div class="grid c2">
 <div class="card"><h3>Servicios · peso en ventas</h3>
  <div class="barras s"><span class="id">65 %</span><div class="barra"><i style="width:100%"></i></div><span>Sala y terraza</span>
  <span class="id">18 %</span><div class="barra"><i style="width:28%"></i></div><span>Reparto a domicilio</span>
  <span class="id">10 %</span><div class="barra"><i style="width:15%"></i></div><span>Para llevar</span>
  <span class="id">7 %</span><div class="barra"><i style="width:11%"></i></div><span>Barra</span></div>
  <p>Más reservas, menú de mediodía, celebraciones, wifi y alérgenos. Las plataformas cobran <b>2.100 €/mes</b>: el doble del alquiler. El pedido para llevar directo es la salida.</p></div>
 <div class="card tint"><h3>Publicidad · 450 €/mes (1 %)</h3>
  <div class="minis"><div><b class="num m">62 %</b><span>descarta un local por una mala reseña</span></div><div><b class="num m">73 %</b><span>lee opiniones antes de ir</span></div><div><b class="num m">17 %</b><span>mira redes o web</span></div></div>
  {lista(["<b>Perfil de Google</b> y carta digital: coste 0, prioridad 1", "Instagram y TikTok: 3 publicaciones por semana", "Menú universitario con carné; fidelización desde el TPV", "Calendario: inicio de curso, exámenes, Fallas"])}</div>
</div>
<p class="nota">Estudio de TheFork Lab, julio de 2026 (L'Express Franchise, 2026).</p>"""))

# Lab 3 (tras los servicios)
S.append(lab("Simulación: una hora punta con papel y con KDS", "hora_punta.html"))

# 15 · Punto 7: conclusiones
S.append(("dark", f"""
{punto(7, "Conclusiones")}
<div class="pasos">{''.join(f'<div class="fila"><span class="dot g">{k}</span><p>{t}</p></div>' for k, t in enumerate([
  "Un negocio <b>sano en un sector con márgenes estrechos</b>: 45.000 €/mes, ratios del sector, 16 % antes de impuestos… que se evapora con dos meses flojos.",
  "Lo que más pesa: producto (32 %) y personal (33 %). Lo que más margen tiene de bajar: las <b>comisiones de reparto</b>.",
  "El entorno pone fecha: <b>Verifactu el 1/1/2027</b>, Windows 10 sin soporte, y un cliente que decide por las reseñas.",
  "No le falta dinero: le falta <b>alguien que diseñe la infraestructura</b> y la deje funcionando sola. Ese es el proyecto."], 1))}</div>"""))

# 17 · Bibliografía y preguntas
S.append(("dark", f"""
{punto(8, "Bibliografía")}
<div class="grid c3 bib">
 <div class="card oscura"><h3>Sector y empresas</h3>{lista(["INE (2025) · Profesional Horeca (2025) · Hosteltur (2026)", "Buenavista Equity Partners (2025) · Economía 3 (2024)", "Forbes España (2026) · El Confidencial Digital (2025)"])}</div>
 <div class="card oscura"><h3>Finanzas y trabajo</h3>{lista(["Convenio de hostelería de Valencia (CCOO, 2025; Turnozo, 2026)", "Real Decreto 126/2026 (SMI) · Ibermutua (2026)", "Cámara de España (2022) · ICO (s.f.) · idealista/news (2026)"])}</div>
 <div class="card oscura"><h3>Mercado y normativa</h3>{lista(["idealista, Fotocasa, Habitaclia y Nuroa (2026)", "Qamarero (2025) · L'Express Franchise (2026)", "Leyes 11/2021, 7/2022, 7/2024, 29/1994 · RD 1007/2023 · RGPD"])}</div>
</div>
<p class="pie">45 referencias en formato APA (7.ª ed.) en el punto 8 del informe.</p>"""))

# 16 · Cuestionario
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
 {q:'¿Qué parte de las ventas de Burglar King se va en personal?',o:['16 %','28 %','33 %','45 %'],ok:2,
  x:'<b>33 %</b>: 14.800 € de 45.000 €. Dentro de la banda del 30-35 % habitual en el servicio en mesa. El producto se lleva otro 32 %.'},
 {q:'Burglar King es una sociedad limitada. ¿Desde cuándo debe tener su facturación adaptada a Verifactu?',o:['1 de enero de 2026','1 de enero de 2027','1 de julio de 2027','No le afecta: es una microempresa'],ok:1,
  x:'<b>1 de enero de 2027</b> para las sociedades (1 de julio de 2027 para el resto), tras el aplazamiento del Real Decreto-ley 15/2025. Su TPV de 2016 no se va a adaptar.'},
 {q:'Según el estudio de TheFork (2026), ¿qué hace que más españoles descarten un restaurante?',o:['El precio','La ubicación','No poder reservar en línea','Una mala reseña en internet'],ok:3,
  x:'<b>Una mala reseña</b>, para el 62 %; el precio solo para el 24 %. Por eso la prioridad del marketing es el perfil de Google, que cuesta 0 €.'}];
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
shutil.copy(AQUI.parent / "logos" / "logo.svg", ENTREGA / "fig" / "logo.svg")
shutil.copytree(AQUI / "laboratorios", ENTREGA / "laboratorios")
(ENTREGA / "css" / "presentacion.css").write_text(CSS, encoding="utf-8")
(ENTREGA / "js" / "presentacion.js").write_text(JS, encoding="utf-8")
doc = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reto 1 · Burglar King</title><link rel="stylesheet" href="css/presentacion.css"></head>
<body><div id="prog"><i></i></div><div id="deck">{cuerpo}</div><div id="notas"></div>
<div id="toast"></div><div id="reloj"></div><div id="ayuda">← → avanzar · N guion · T cronómetro · M movimiento · F pantalla completa</div><script src="js/presentacion.js"></script></body></html>"""
(ENTREGA / "presentacion.html").write_text(doc, encoding="utf-8")
MIN = sum(d["min"] for d in GUION.values())
(ENTREGA / "LEEME.txt").write_text(f"""Reto 1 · Proyecto Intermodular I · Burglar King
Riches Manuel y Roca · 1.º CFGS ASIR · IES Conselleria · octubre de 2026

Descomprimir la carpeta entera y abrir los ficheros con cualquier navegador (no hace falta conexión ni servidor).

presentacion.html      Presentación ({len(S)} diapositivas, {MIN:g} min).
                       Teclas: flechas o espacio para avanzar, N guion del orador, T cronómetro de ensayo,
                       M animaciones sí/no, F pantalla completa. Tres diapositivas cargan los laboratorios (se pueden abrir
                       también en una pestaña aparte); la última es un cuestionario de 3 preguntas.
css/presentacion.css   Estilos y animaciones de la presentación.
js/presentacion.js     Navegación, contadores, cronómetro y cuestionario.
fig/                   Figuras del informe (organigrama, flujo de la comanda, red actual, costes) y logo.
laboratorios/          Tres simulaciones (abrir laboratorios/index.html); cada una se lanza con «Simular» y tiene modo manual:
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
