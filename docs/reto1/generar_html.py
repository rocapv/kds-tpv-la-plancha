#!/usr/bin/env python3
"""Presentación del Reto 1 en un solo HTML autónomo (figuras incrustadas en base64).

Teclas: ← → / espacio / clic para avanzar, N muestra el guion del orador, F pantalla completa.
Uso: python3 generar_html.py  ->  reto1_presentacion.html
"""
import base64, html
from pathlib import Path

AQUI = Path(__file__).resolve().parent
img = lambda f: "data:image/png;base64," + base64.b64encode((AQUI / "fig" / f).read_bytes()).decode()
e = html.escape

def tarjetas(items, cols, clase="card"):
    return f'<div class="grid c{cols}">' + "".join(f'<div class="{clase}">{x}</div>' for x in items) + "</div>"

def lista(items):
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"

S = []   # (clase, html, notas)

S.append(("dark portada", f"""
<div class="badge">R1</div>
<h1 class="big">Lo que hay detrás de la barra</h1>
<p class="sub">Análisis del contexto tecnológico de Burglar King</p>
<p class="pie">Reto 1 · Proyecto Intermodular I · 1.º CFGS ASIR · IES Conselleria<br>Riches Manuel y Roca · octubre de 2026</p>""",
"Presentamos el análisis del contexto tecnológico de Burglar King, la empresa para la que estamos desarrollando el TPV con pantallas de cocina. El objetivo del reto es entender qué tecnología tiene hoy la empresa, en qué entorno se mueve y qué necesita, antes de proponer nada."))

S.append(("", f"""
<h2>Burglar King: una hamburguesería de barrio</h2>
{tarjetas([f'<b class="num">{n}</b><span>{t}</span>' for n, t in [("13","mesas en sala, terraza y barra"),("4","personas en plantilla"),("15-25 €","ticket medio por comensal"),("4","canales: sala, barra, llevar y reparto")]], 4, "card stat")}
<p class="lead"><b>Burjassot (València), junto al campus universitario.</b> Servicio concentrado en franjas cortas y mucho pedido para llevar: el peor escenario para el papel.</p>
<p class="nota">Empresa ficticia (Burglar King Burjassot, S.L.), construida con datos reales del sector. Restauración independiente, CNAE 56.10.</p>""",
"Burglar King es una hamburguesería de barrio en Burjassot, al lado del campus. Trece mesas y cuatro personas. Es ficticia, como permite el enunciado, pero construida con datos reales. Pertenece al grupo más numeroso: el local independiente, el 93 % de los establecimientos. El servicio se concentra en franjas cortas, y ahí la tecnología no puede fallar."))

S.append(("", f"""
<h2>Una persona lo concentra todo</h2>
<div class="split"><img src="{img('organigrama.png')}" alt="Organigrama de Burglar King">
<div class="card tint"><h3>El encargado es…</h3>{lista(["dirección y compras","caja y cierre del día","relación con la gestoría","<b>y, sin quererlo, el informático</b>"])}</div></div>
<p class="lead"><i>Si él falta, nadie sabe reiniciar el router ni recuperar la contraseña del TPV: un punto único de fallo humano.</i></p>""",
"La estructura es plana: sala, cocina y una persona que lo concentra todo. El encargado es dirección, compras, caja, administración y, en la práctica, el único responsable de informática. Igual que hay puntos únicos de fallo técnicos, aquí hay uno humano."))

S.append(("", f"""
<h2>El dato llega cuando el cliente ya se va</h2>
<img class="ancho" src="{img('flujo_comanda.png')}" alt="Flujo actual de una comanda">
<div class="banda">Durante el servicio, el local trabaja a ciegas: no sabe qué mesa espera ni cuánto tarda la cocina.</div>""",
"La comanda nace en papel, viaja a la cocina pinchada y a voz, se prepara de memoria, sale al pase con un grito y solo entra en un sistema cuando el camarero la teclea para cobrar. El dato llega cuando el cliente ya se va. En cada paso hay un problema: letra ilegible, sin hora, nadie ve el retraso, platos fríos y doble tecleo."))

inv = [("PC del TPV","2015 · Celeron · 4 GB · disco mecánico con sectores dañados"),("Sin SAI","un corte de luz apaga la caja de golpe"),("Router de la operadora","en una balda del almacén, junto a la cámara frigorífica"),("Grabador de vídeo","firmware de 2019 y contraseña de fábrica"),("Tableta de reparto","Android 9, siempre enchufada"),("Portátil y móviles","personales: el negocio vive en cuentas privadas")]
S.append(("", f"""
<h2>Inventario: lo que hay, sin diseño</h2>
{tarjetas([f'<div class="fila"><span class="dot">{i+1}</span><b>{t}</b></div><p>{d}</p>' for i,(t,d) in enumerate(inv)], 3)}
<p class="nota">Equipos y estados del escenario ficticio.</p>""",
"El único equipo que guarda datos del negocio, el PC del TPV, es el más viejo y con el disco en peor estado. No hay SAI. Router y grabador están en una balda del almacén con calor y grasa. El grabador tiene la contraseña de fábrica. Y los datos del negocio están en el portátil y el móvil personales del encargado."))

S.append(("", f"""
<h2>Una sola red para todo y para todos</h2>
<div class="split"><img src="{img('red_actual.png')}" alt="Esquema de la red actual">
<div class="pasos">{''.join(f'<div class="fila"><span class="dot rojo">{k}</span><p>{t}</p></div>' for k,t in [("1","Los móviles de los clientes están en la misma red que la caja, el datáfono y las cámaras."),("2","La clave del wifi está en la pizarra y la del router, en su etiqueta."),("3","El grabador se ve desde internet por un puerto abierto.")])}</div></div>""",
"La red es la que dejó la operadora: un router que hace de módem, cortafuegos, DHCP y punto de acceso. Una estrella con una sola subred, sin VLAN. El móvil de cualquier cliente está en el mismo dominio de difusión que la caja, el datáfono y el grabador, que además está expuesto a internet."))

S.append(("", f"""
<h2>La caja funciona con un sistema sin soporte</h2>
<div class="split mitad"><div><b class="num xl">14/10/2025</b><p class="lead">fin del soporte de Windows 10, el sistema del PC del TPV. Su procesador no admite Windows 11: hay que sustituirlo o cambiar de sistema.</p><p class="nota">Fuente: Microsoft (2025).</p></div>
<div class="pila">{''.join(f'<div class="card fila2"><b>{a}</b><span>{b}</span></div>' for a,b in [("Windows 11 Home","no puede unirse a un dominio ni cifrar con BitLocker"),("Android 9","sin parches del fabricante"),("Firmware del grabador","de 2019, sin actualizar"),("Datos del negocio","repartidos: no hay ningún servidor")])}</div></div>""",
"El 14 de octubre de 2025 terminó el soporte de Windows 10, el sistema del ordenador de cobro, y su procesador no admite Windows 11. El portátil lleva Windows 11 Home, que no se une a un dominio. No hay ningún servidor que centralice datos, cuentas ni copias: para cuatro personas un dominio no tiene sentido, pero un servidor local sí."))

riesgos = [("R1","Grabador accesible desde internet con credenciales de fábrica",9),("R2","Red única: caja, datáfono, cámaras y clientes",9),("R3","Sin copias de la base de datos del TPV",6),("R4","Sistema operativo sin soporte en la caja",6),("R5","Cuenta única compartida en el TPV",6),("R6","Disco dañado y sin SAI",6)]
S.append(("", f"""
<h2>Diez riesgos; la mitad, críticos</h2>
<div class="barras">{''.join(f'<span class="id">{i}</span><span>{t}</span><span class="barra"><i style="width:{v/9*100:.0f}%" class="{"r" if v>=9 else ""}"></i><b>{v}</b></span>' for i,t,v in riesgos)}</div>
<p class="nota">Probabilidad × impacto (1-3 cada uno). Críticos ≥ 6. Hay además cuatro riesgos altos: router de fábrica, datos en cuentas personales, videovigilancia sin cartel y contraseñas a la vista.</p>""",
"Probabilidad por impacto, de 1 a 3. Diez riesgos, seis críticos. Los peores: el grabador expuesto con la contraseña de fábrica y la red compartida con los clientes. Casi ninguno exige dinero: separar redes, cambiar contraseñas y hacer copias cuesta muy poco. Falta conocimiento, no presupuesto."))

S.append(("", f"""
<h2>El sector: grande, atomizado y con poco margen</h2>
{tarjetas([f'<b class="num{" neg" if "−" in n else ""}">{n}</b><span>{t}</span><small>{f}</small>' for n,t,f in [("280.403","establecimientos de hostelería en España","Profesional Horeca, 2025"),("93 %","son locales independientes","Profesional Horeca, 2025"),("−0,9 %","rentabilidad de la restauración en 2025","Hosteltur, 2026"),("31.186","bares y restaurantes en la Comunitat Valenciana","El Periòdic, 2025")]], 2, "card stat")}""",
"Más de 280.000 establecimientos, el 93 % independientes. En la Comunitat Valenciana, más de 31.000 bares y restaurantes. Y el dato clave: el sector factura más, pero la restauración tuvo rentabilidad negativa en 2025. Cualquier inversión se mide en euros ahorrados."))

pestel = [("P","Político","Verifactu aplazado: 1/1/2027 para sociedades"),("E","Económico","Factura más, gana menos: cada euro cuenta"),("S","Social","Cliente joven que paga con móvil y espera wifi"),("T","Tecnológico","Fin de Windows 10; la cocina sigue en papel"),("E","Ambiental","Bisfenol A en el papel térmico; equipos viejos como RAEE"),("L","Legal","Ley antifraude, RGPD, alérgenos, registro de jornada")]
S.append(("", f"""
<h2>PESTEL: lo que no controla, pero le condiciona</h2>
{tarjetas([f'<div class="fila"><span class="dot g">{k}</span><b>{t}</b></div><p>{d}</p>' for k,t,d in pestel], 3)}""",
"Lo político y legal que más pesa es Verifactu: desde el 1 de enero de 2027 una sociedad como Burglar King necesita facturación adaptada, y su TPV de 2016 no lo estará. Márgenes estrechos; cliente que paga con móvil, también en la terraza; fin de Windows 10 y una digitalización que no ha llegado a la cocina; papel térmico y residuos electrónicos; protección de datos, alérgenos y registro de jornada."))

S.append(("", f"""
<h2>Clientes, proveedores y competencia</h2>
{tarjetas([f'<h3>{t}</h3>{lista(i)}' for t,i in [("Clientes",["Estudiantes: rapidez y pago con móvil","Familias: cuenta dividida","Para llevar: saber cuándo está listo","Reparto: que no se pierda el pedido"]),("Proveedores TIC",["Operadora: una sola línea","Banco: datáfono por wifi","TPV de 2016 sin mantenimiento","Plataformas: pedidos fuera del TPV"]),("Competencia",["Cadenas con la comanda en pantalla","TPV de mercado: cobran por terminal","Cada pantalla de cocina es otra cuota","<b>Hueco: pantallas sin licencia</b>"])]], 3)}
<p class="nota">Competencia tecnológica: estudio de mercado del proyecto (Riches Manuel y Roca, 2026).</p>""",
"Clientes en franjas cortas: estudiantes, familias, para llevar y reparto. Los proveedores que importan son los tecnológicos: una sola línea, el datáfono del banco, un TPV sin mantenimiento y plataformas cuyos pedidos no llegan al TPV. La competencia cobra por terminal: añadir una pantalla de cocina es pagar otra licencia. Ahí está el hueco del proyecto."))

nec = ["Separar la red: negocio, cocina, cámaras e invitados","Copias automáticas verificadas y un SAI","Caja con soporte y adaptable a Verifactu","Comanda en pantalla de cocina con tiempos","Cuentas individuales y datos fuera de lo personal","Wifi profesional en sala, terraza y cocina","Videovigilancia conforme al RGPD"]
S.append(("", f"""
<h2>Necesidades, por orden de urgencia</h2>
<div class="necesidades">{''.join(f'<div class="fila"><span class="dot{"" if i<3 else " g2"}">{i+1}</span><p>{t}</p></div>' for i,t in enumerate(nec))}
<div class="card tint">Proyecto de implantación: red segmentada, servidor local con el KDS+TPV, puestos de sala y cocina, copias y supervisión.</div></div>""",
"Siete necesidades; las tres primeras, urgentes: separar la red, copias con SAI y una caja con soporte y adaptable a Verifactu. Después, la comanda en pantalla de cocina, cuentas individuales, wifi profesional y cámaras conformes al RGPD. El proyecto que responde es una implantación de infraestructura."))

req = [("Sin internet","se sigue tomando nota y cobrando"),("4 redes","desde invitados no se ve el negocio"),("HTTPS","en todo el tráfico"),("< 1 hora","para restaurar todo el sistema"),("1 PIN","por persona: cada cobro tiene autor"),("0 €","por terminal o por pantalla")]
S.append(("", f"""
<h2>Lo que el proyecto tendrá que cumplir</h2>
<div class="split ancho2">{tarjetas([f'<b class="num m">{a}</b><span>{b}</span>' for a,b in req], 3, "card stat")}
<div class="card oscura"><h3>Fechas que obligan</h3><p><b class="nar">1/1/2027</b><br>Verifactu para sociedades</p><p><b class="nar">1/7/2027</b><br>Verifactu para el resto</p></div></div>
<p class="nota">Obligaciones: IVA del 10 % y facturación, registro de jornada, prevención de riesgos con pantallas y RGPD. Ayudas: Kit Digital (Red.es) y líneas del IVACE+i, según convocatoria abierta; el presupuesto se hará sin contar con ellas.</p>""",
"Características que servirán para evaluar el proyecto: funcionar sin internet, cuatro redes separadas, tráfico cifrado, restaurar en menos de una hora, un PIN por persona y cero euros por pantalla. Verifactu obliga desde el 1 de enero de 2027 para sociedades. Las ayudas dependen de convocatorias, así que el presupuesto se hará sin contar con ellas."))

S.append(("dark", f"""
<h1 class="big">No falta dinero.</h1>
<p class="sub grande">Falta alguien que diseñe la infraestructura y la deje funcionando sola.</p>
<div class="linea">{''.join(f'<div><span class="dot xl">{k}</span><p>{t}</p></div>' for k,t in [("R2","Diseño"),("R3","Viabilidad"),("R4","Presupuesto"),("R5","Documentación"),("R6","Plan de intervención")])}</div>""",
"Burglar King trabaja a ciegas durante el servicio, guarda sus datos en un equipo sin soporte y sin copias y comparte una red plana con sus clientes. Hay una fecha, Verifactu, y una oportunidad, hardware barato y software sin cuotas por pantalla. Las medidas más urgentes casi no cuestan dinero: falta alguien que diseñe la infraestructura. Eso haremos en los próximos retos."))

S.append(("dark", """
<h1 class="big">¿Preguntas?</h1>
<p class="sub">Informe completo: «Análisis del contexto tecnológico de Burglar King» (Reto 1).</p>
<p class="pie">Fuentes principales: INE (2025), Profesional Horeca (2025), Hosteltur (2026), El Periòdic (2025), Microsoft (2025), Garrigues (2025), Red.es (s.f.), normativa del BOE y del DOUE. Referencias completas en formato APA en el informe.</p>""",
"Gracias. Quedamos abiertos a preguntas."))

CSS = """
:root{--osc:#23272b;--nar:#e67e22;--nar2:#fdebd9;--txt:#2b2b2b;--gris:#6b6b6b;--claro:#f4f4f4;--rojo:#c0392b}
*{box-sizing:border-box;margin:0}
html,body{height:100%;background:#111;font-family:Arial,Helvetica,sans-serif;color:var(--txt)}
#deck{position:fixed;inset:0;display:grid;place-items:center}
.slide{position:absolute;width:1280px;height:720px;background:#fff;padding:48px 58px;display:none;transform-origin:center;overflow:hidden}
.slide.on{display:block}
.slide.dark{background:var(--osc);color:#fff}
h1.big{font-size:56px;line-height:1.1;margin-top:150px}
.portada h1.big{margin-top:60px}
h2{font-size:34px;margin-bottom:34px}
h3{font-size:21px;margin-bottom:14px}
.sub{font-size:26px;color:var(--nar);margin-top:16px}.sub.grande{font-size:32px;max-width:1050px}
.pie{position:absolute;left:58px;bottom:60px;font-size:16px;color:#ccc;line-height:1.7;max-width:1100px}
.badge{width:84px;height:84px;border-radius:50%;background:var(--nar);display:grid;place-items:center;font-weight:bold;font-size:24px;margin-top:70px}
.grid{display:grid;gap:22px}.c2{grid-template-columns:1fr 1fr}.c3{grid-template-columns:repeat(3,1fr)}.c4{grid-template-columns:repeat(4,1fr)}
.card{background:var(--claro);border-radius:12px;padding:22px 24px;font-size:17px;line-height:1.4}
.card p{color:var(--gris);margin-top:16px;font-size:19px;line-height:1.45}
.c3>.card{min-height:200px;padding:28px}
.card.tint{background:var(--nar2)}.card.oscura{background:var(--osc);color:#fff}.card.oscura p{color:#fff;font-size:19px}
.stat{display:flex;flex-direction:column;gap:10px;min-height:180px}.c2>.stat{min-height:230px;justify-content:center;font-size:20px}.stat small{color:var(--gris);font-size:13px}
.num{font-size:58px;color:var(--nar);line-height:1}.num.neg{color:var(--rojo)}.num.m{font-size:30px}.num.xl{font-size:76px;display:block;margin:18px 0}
.nar{color:var(--nar);font-size:22px}
.lead{font-size:20px;line-height:1.45;margin-top:28px}
.nota{font-size:13px;color:var(--gris);position:absolute;left:58px;bottom:40px;right:120px}
.split{display:grid;grid-template-columns:1.9fr 1fr;gap:34px;align-items:start}.split img{width:100%}
.split.mitad{grid-template-columns:1fr 1fr}.split.ancho2{grid-template-columns:2fr 1fr}
img.ancho{width:100%;display:block}
.banda{background:var(--osc);color:#fff;font-weight:bold;font-size:21px;padding:20px 26px;border-radius:12px;margin-top:20px}
.fila{display:flex;gap:16px;align-items:center}.fila b{font-size:21px}.fila p{font-size:19px;color:var(--txt);margin:0;line-height:1.35}
.dot{flex:none;width:46px;height:46px;border-radius:50%;background:var(--nar);color:#fff;display:grid;place-items:center;font-weight:bold;font-size:18px}
.dot.rojo{background:var(--rojo)}.dot.g{width:52px;height:52px;font-size:22px}.dot.g2{background:#33383d}.dot.xl{width:74px;height:74px;font-size:20px;margin:0 auto}
.pasos{display:flex;flex-direction:column;gap:46px;margin-top:20px}
.pila{display:flex;flex-direction:column;gap:16px}.fila2{display:grid;grid-template-columns:200px 1fr;align-items:center}.fila2 span{color:var(--gris);font-size:16px}
.barras{display:grid;grid-template-columns:50px 1fr 520px;gap:20px 18px;align-items:center;font-size:19px}
.barras .id{color:var(--gris);font-weight:bold}.barra{display:flex;align-items:center;gap:10px}
.barra i{display:block;height:30px;background:var(--nar)}.barra i.r{background:var(--rojo)}
.necesidades{display:grid;grid-template-columns:1fr 1fr;grid-auto-flow:column;grid-template-rows:repeat(4,auto);gap:26px 50px}
.necesidades .card{grid-column:2;grid-row:4;font-size:17px}
ul{padding-left:22px}li{margin:16px 0;font-size:20px}
.linea{display:flex;justify-content:space-between;margin-top:110px;position:relative}
.linea:before{content:"";position:absolute;left:60px;right:60px;top:37px;height:2px;background:#666}
.linea div{width:180px;text-align:center;position:relative}.linea p{margin-top:14px;font-size:18px}
.num-pag{position:absolute;right:40px;bottom:24px;font-size:14px;color:#999}
#notas{position:fixed;left:0;right:0;bottom:0;background:#fffbe8;color:#222;font-size:16px;line-height:1.5;padding:16px 24px;display:none;max-height:35vh;overflow:auto;border-top:3px solid var(--nar)}
#notas.on{display:block}
#ayuda{position:fixed;right:12px;top:10px;color:#888;font-size:12px}
@media print{@page{size:1280px 720px;margin:0}html,body{background:#fff}#deck{position:static;display:block}
 .slide{display:block!important;position:relative;transform:none!important;page-break-after:always}#notas,#ayuda{display:none!important}}
"""

JS = """
const sl=[...document.querySelectorAll('.slide')],notas=document.getElementById('notas');let i=0;
function fit(){const k=Math.min(innerWidth/1280,innerHeight/720);sl.forEach(s=>s.style.transform=`scale(${k})`)}
function ver(n){i=Math.max(0,Math.min(sl.length-1,n));sl.forEach((s,k)=>s.classList.toggle('on',k===i));
 notas.textContent=sl[i].dataset.notas;try{history.replaceState(null,'','#'+(i+1))}catch(e){}}
addEventListener('keydown',ev=>{if(['ArrowRight','PageDown',' '].includes(ev.key)){ev.preventDefault();ver(i+1)}
 else if(['ArrowLeft','PageUp'].includes(ev.key))ver(i-1);else if(ev.key==='Home')ver(0);else if(ev.key==='End')ver(sl.length-1);
 else if(ev.key==='n'||ev.key==='N')notas.classList.toggle('on');
 else if(ev.key==='f'||ev.key==='F'){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()}});
document.getElementById('deck').addEventListener('click',ev=>ver(ev.clientX>innerWidth/3?i+1:i-1));
let x0=null;addEventListener('touchstart',e=>x0=e.touches[0].clientX);addEventListener('touchend',e=>{if(x0===null)return;const d=e.changedTouches[0].clientX-x0;if(Math.abs(d)>40)ver(d<0?i+1:i-1);x0=null});
addEventListener('resize',fit);fit();ver((parseInt(location.hash.slice(1))||1)-1);
"""

cuerpo = "".join(
    f'<section class="slide {c}" data-notas="{e(n)}" aria-label="Diapositiva {k}">{h}'
    + (f'<span class="num-pag">{k}</span>' if k > 1 else "") + "</section>"
    for k, (c, h, n) in enumerate(S, 1))
doc = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reto 1 · Burglar King</title><style>{CSS}</style></head>
<body><div id="deck">{cuerpo}</div><div id="notas"></div>
<div id="ayuda">← → avanzar · N guion · F pantalla completa</div><script>{JS}</script></body></html>"""
out = AQUI / "reto1_presentacion.html"
out.write_text(doc, encoding="utf-8")
print("HTML:", out, f"{out.stat().st_size/1024:.0f} KB · {len(S)} diapositivas")
