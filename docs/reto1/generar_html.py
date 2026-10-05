#!/usr/bin/env python3
"""Presentación del Reto 1 en un solo HTML autónomo (figuras incrustadas en base64).

Teclas: ← → / espacio / clic para avanzar, N guion del orador, T cronómetro de ensayo, F pantalla completa.
Animado con CSS y JS a pelo: transición con dirección, aparición escalonada, contadores, barras que
crecen y barra de progreso. Respeta `prefers-reduced-motion` y no toca la impresión.
Uso: python3 generar_html.py  ->  reto1_presentacion.html
"""
import base64, html, json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
img = lambda f: "data:image/png;base64," + base64.b64encode((AQUI / "fig" / f).read_bytes()).decode()
e = html.escape
LOGO = "data:image/svg+xml;base64," + base64.b64encode((AQUI.parent / "logos" / "logo.svg").read_bytes()).decode()

def tarjetas(items, cols, clase="card"):
    return f'<div class="grid c{cols}">' + "".join(f'<div class="{clase}">{x}</div>' for x in items) + "</div>"

def lista(items):
    return "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"

# El guion hablado (notas del orador) vive en guion.json: lo leen este generador y generar_pptx.js,
# así el HTML y el PowerPoint dicen lo mismo. 30 min = suma de `min`.
GUION = {d["n"]: d for d in json.loads((AQUI / "guion.json").read_text(encoding="utf-8"))["diapositivas"]}

S = []   # (clase, html)

S.append(("dark portada", f"""
<div class="badge">R1</div>
<img class="logo" src="{LOGO}" alt="Logo de Burglar King">
<h1 class="big">Lo que hay detrás de la barra</h1>
<p class="sub">Análisis del contexto tecnológico de Burglar King</p>
<p class="pie">Reto 1 · Proyecto Intermodular I · 1.º CFGS ASIR · IES Conselleria<br>Riches Manuel y Roca · octubre de 2026</p>"""))

S.append(("", f"""
<h2>Burglar King: una hamburguesería de barrio</h2>
{tarjetas([f'<b class="num">{n}</b><span>{t}</span>' for n, t in [("13","mesas en sala, terraza y barra"),("4","personas en plantilla"),("15-25 €","ticket medio por comensal"),("4","canales: sala, barra, llevar y reparto")]], 4, "card stat")}
<p class="lead"><b>Burjassot (València), junto al campus universitario.</b> Servicio concentrado en franjas cortas y mucho pedido para llevar: el peor escenario para el papel.</p>
<p class="nota">Empresa ficticia (Burglar King Burjassot, S.L.), construida con datos reales del sector. Restauración independiente, CNAE 56.10.</p>"""))

S.append(("", f"""
<h2>Una persona lo concentra todo</h2>
<div class="split"><img src="{img('organigrama.png')}" alt="Organigrama de Burglar King">
<div class="card tint"><h3>El encargado es…</h3>{lista(["dirección y compras","caja y cierre del día","relación con la gestoría","<b>y, sin quererlo, el informático</b>"])}</div></div>
<p class="lead"><i>Si él falta, nadie sabe reiniciar el router ni recuperar la contraseña del TPV: un punto único de fallo humano.</i></p>"""))

S.append(("", f"""
<h2>El dato llega cuando el cliente ya se va</h2>
<img class="ancho" src="{img('flujo_comanda.png')}" alt="Flujo actual de una comanda">
<div class="banda">Durante el servicio, el local trabaja a ciegas: no sabe qué mesa espera ni cuánto tarda la cocina.</div>"""))

inv = [("PC del TPV","2015 · Celeron · 4 GB · disco mecánico con sectores reasignados"),("Sin SAI","un corte de luz apaga la caja de golpe"),("Router de la operadora","en una balda del almacén, junto a la cámara frigorífica"),("Grabador de vídeo","firmware de 2019 y contraseña de fábrica"),("Tableta de reparto","Android 9, siempre enchufada"),("Portátil y móviles","personales: el negocio vive en cuentas privadas")]
S.append(("", f"""
<h2>Inventario: lo que hay, sin diseño</h2>
{tarjetas([f'<div class="fila"><span class="dot">{i+1}</span><b>{t}</b></div><p>{d}</p>' for i,(t,d) in enumerate(inv)], 3)}
<p class="nota">Equipos y estados del escenario ficticio.</p>"""))

S.append(("", f"""
<h2>Una sola red para todo y para todos</h2>
<div class="split"><img src="{img('red_actual.png')}" alt="Esquema de la red actual">
<div class="pasos">{''.join(f'<div class="fila"><span class="dot rojo">{k}</span><p>{t}</p></div>' for k,t in [("1","Los móviles de los clientes están en la misma red que la caja, el datáfono y las cámaras."),("2","La clave del wifi está en la pizarra y la del router, en su etiqueta."),("3","El grabador se ve desde internet por un puerto abierto.")])}</div></div>"""))

S.append(("", f"""
<h2>La caja funciona con un sistema sin soporte</h2>
<div class="split mitad"><div><b class="num xl">14/10/2025</b><p class="lead">fin del soporte de Windows 10, el sistema del PC del TPV. Su procesador no admite Windows 11: hay que sustituirlo o cambiar de sistema.</p><p class="nota">Fuente: Microsoft (2025).</p></div>
<div class="pila">{''.join(f'<div class="card fila2"><b>{a}</b><span>{b}</span></div>' for a,b in [("Windows 11 Home","no puede unirse a un dominio ni cifrar con BitLocker"),("Android 9","sin parches del fabricante"),("Firmware del grabador","de 2019, sin actualizar"),("Datos del negocio","repartidos: no hay ningún servidor")])}</div></div>"""))

riesgos = [("R1","Grabador accesible desde internet con credenciales de fábrica",9),("R2","Red única: caja, datáfono, cámaras y clientes",9),("R3","Sin copias de la base de datos del TPV",6),("R4","Sistema operativo sin soporte en la caja",6),("R5","Cuenta única compartida en el TPV",6),("R6","Disco dañado y sin SAI",6)]
S.append(("", f"""
<h2>Diez riesgos; seis, críticos</h2>
<div class="barras">{''.join(f'<span class="id">{i}</span><span>{t}</span><span class="barra"><i style="width:{v/9*100:.0f}%" class="{"r" if v>=9 else ""}"></i><b>{v}</b></span>' for i,t,v in riesgos)}</div>
<p class="nota">Probabilidad × impacto (1-3 cada uno). Críticos ≥ 6. Hay además cuatro riesgos altos: router de fábrica, datos en cuentas personales, videovigilancia sin cartel y contraseñas a la vista.</p>"""))

S.append(("", f"""
<h2>El sector: grande, atomizado y con poco margen</h2>
{tarjetas([f'<b class="num{" neg" if "−" in n else ""}">{n}</b><span>{t}</span><small>{f}</small>' for n,t,f in [("280.403","establecimientos de hostelería en España","Profesional Horeca, 2025"),("93 %","son locales independientes","Profesional Horeca, 2025"),("−0,9 %","rentabilidad de la restauración en 2025","Hosteltur, 2026"),("31.186","bares y restaurantes en la Comunitat Valenciana","El Periòdic, 2025")]], 2, "card stat")}"""))

pestel = [("P","Político","Verifactu aplazado: 1/1/2027 para sociedades"),("E","Económico","Factura más, gana menos: cada euro cuenta"),("S","Social","Cliente joven que paga con móvil y espera wifi"),("T","Tecnológico","Fin de Windows 10; la cocina sigue en papel"),("E","Ambiental","Bisfenol A en el papel térmico; equipos viejos como RAEE"),("L","Legal","Ley antifraude, RGPD, alérgenos, registro de jornada")]
S.append(("", f"""
<h2>PESTEL: lo que no controla, pero le condiciona</h2>
{tarjetas([f'<div class="fila"><span class="dot g">{k}</span><b>{t}</b></div><p>{d}</p>' for k,t,d in pestel], 3)}"""))

S.append(("", f"""
<h2>Clientes, proveedores y competencia</h2>
{tarjetas([f'<h3>{t}</h3>{lista(i)}' for t,i in [("Clientes",["Estudiantes: rapidez y pago con móvil","Familias: cuenta dividida","Para llevar: saber cuándo está listo","Reparto: que no se pierda el pedido"]),("Proveedores TIC",["Operadora: una sola línea","Banco: datáfono por wifi","TPV de 2016 sin mantenimiento","Plataformas: pedidos fuera del TPV"]),("Competencia",["Cadenas con la comanda en pantalla","TPV de mercado: cobran por terminal","Cada pantalla de cocina es otra cuota","<b>Hueco: pantallas sin licencia</b>"])]], 3)}
<p class="nota">Competencia tecnológica: estudio de mercado del proyecto (Riches Manuel y Roca, 2026).</p>"""))

nec = ["Separar la red: negocio, cocina, cámaras e invitados","Copias automáticas verificadas y un SAI","Caja con soporte y adaptable a Verifactu","Comanda en pantalla de cocina con tiempos","Cuentas individuales y datos fuera de lo personal","Wifi profesional en sala, terraza y cocina","Videovigilancia conforme al RGPD"]
S.append(("", f"""
<h2>Necesidades, por orden de urgencia</h2>
<div class="necesidades">{''.join(f'<div class="fila"><span class="dot{"" if i<3 else " g2"}">{i+1}</span><p>{t}</p></div>' for i,t in enumerate(nec))}
<div class="card tint">Proyecto de implantación: red segmentada, servidor local con el KDS+TPV, puestos de sala y cocina, copias y supervisión.</div></div>"""))

req = [("Sin internet","se sigue tomando nota y cobrando"),("4 redes","desde invitados no se ve el negocio"),("HTTPS","en todo el tráfico"),("< 1 hora","para restaurar todo el sistema"),("1 PIN","por persona: cada cobro tiene autor"),("0 €","por terminal o por pantalla")]
S.append(("", f"""
<h2>Lo que el proyecto tendrá que cumplir</h2>
<div class="split ancho2">{tarjetas([f'<b class="num m">{a}</b><span>{b}</span>' for a,b in req], 3, "card stat")}
<div class="card oscura"><h3>Fechas que obligan</h3><p><b class="nar">1/1/2027</b><br>Verifactu para sociedades</p><p><b class="nar">1/7/2027</b><br>Verifactu para el resto</p></div></div>
<p class="nota">Obligaciones: IVA del 10 % y facturación, registro de jornada, prevención de riesgos con pantallas y RGPD. Ayudas: Kit Digital (Red.es) y líneas del IVACE+i, según convocatoria abierta; el presupuesto se hará sin contar con ellas.</p>"""))

S.append(("dark", f"""
<h1 class="big">No falta dinero.</h1>
<p class="sub grande">Falta alguien que diseñe la infraestructura y la deje funcionando sola.</p>
<div class="linea">{''.join(f'<div><span class="dot xl">{k}</span><p>{t}</p></div>' for k,t in [("R2","Diseño"),("R3","Viabilidad"),("R4","Presupuesto"),("R5","Documentación"),("R6","Plan de intervención")])}</div>"""))

S.append(("dark", """
<h1 class="big">¿Preguntas?</h1>
<p class="sub">Informe completo: «Análisis del contexto tecnológico de Burglar King» (Reto 1).</p>
<p class="pie">Fuentes principales: INE (2025), Profesional Horeca (2025), Hosteltur (2026), El Periòdic (2025), Microsoft (2025), Garrigues (2025), Red.es (s.f.), normativa del BOE y del DOUE. Referencias completas en formato APA en el informe.</p>"""))

CSS = """
:root{--osc:#23272b;--nar:#e67e22;--nar2:#fdebd9;--txt:#2b2b2b;--gris:#6b6b6b;--claro:#f4f4f4;--rojo:#c0392b}
*{box-sizing:border-box;margin:0}
html,body{height:100%;background:#111;font-family:Arial,Helvetica,sans-serif;color:var(--txt)}
#deck{position:fixed;inset:0;display:grid;place-items:center}
.slide{position:absolute;width:1280px;height:720px;background:#fff;padding:48px 58px;display:none;transform-origin:center;overflow:hidden}
.slide.on,.slide.sale{display:block}
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
#notas{position:fixed;left:0;right:0;bottom:0;background:#fffbe8;color:#222;font-size:19px;line-height:1.55;padding:14px 28px 18px;display:none;max-height:48vh;overflow:auto;border-top:3px solid var(--nar);white-space:pre-wrap}
#notas .cab{display:block;font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:#8a5a14;margin-bottom:8px;white-space:normal}
#notas.on{display:block}
#ayuda{position:fixed;right:12px;top:10px;color:#888;font-size:12px}
#reloj{position:fixed;left:12px;top:10px;color:#bbb;font-size:13px;font-variant-numeric:tabular-nums;display:none;z-index:11}#reloj.on{display:block}
@media print{@page{size:1280px 720px;margin:0}html,body{background:#fff}#deck{position:static;display:block}
 .slide{display:block!important;position:relative;transform:none!important;page-break-after:always}#notas,#ayuda{display:none!important}}
/* ---- Movimiento ---- */
.slide.on{z-index:2;animation:entra .55s cubic-bezier(.2,.7,.2,1) both}
.slide.sale{z-index:1;pointer-events:none;animation:sale .38s ease both}
body[data-dir=atras] .slide.on{animation-name:entraAtras}
body[data-dir=atras] .slide.sale{animation-name:saleAtras}
@keyframes entra{from{opacity:0;translate:70px 0}to{opacity:1;translate:0 0}}
@keyframes entraAtras{from{opacity:0;translate:-70px 0}to{opacity:1;translate:0 0}}
@keyframes sale{to{opacity:0;translate:-70px 0}}
@keyframes saleAtras{to{opacity:0;translate:70px 0}}
.slide.on .rev{animation:sube .65s cubic-bezier(.2,.7,.2,1) both;animation-delay:calc(var(--i,0)*85ms + 250ms)}
@keyframes sube{from{opacity:0;translate:0 26px}to{opacity:1;translate:0 0}}
.slide.portada{background:linear-gradient(115deg,#23272b 0%,#2f353b 45%,#23272b 100%);background-size:220% 220%}
.slide.on.portada{animation:entra .55s cubic-bezier(.2,.7,.2,1) both,flujo 16s ease-in-out infinite}
body[data-dir=atras] .slide.on.portada{animation-name:entraAtras,flujo}
@keyframes flujo{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.logo{position:absolute;right:90px;top:120px;width:340px;border-radius:30px;box-shadow:0 20px 60px rgba(0,0,0,.45)}
.slide.on .logo.rev{animation:cae .9s cubic-bezier(.3,1.4,.5,1) .35s both,flota 5s ease-in-out 1.5s infinite}
@keyframes cae{from{opacity:0;translate:0 -140px;rotate:-6deg}to{opacity:1;translate:0 0;rotate:0deg}}
@keyframes flota{0%,100%{transform:translateY(0)}50%{transform:translateY(-12px)}}
.slide.on .badge.rev{animation:pop .6s cubic-bezier(.3,1.6,.5,1) .2s both,anillo 2.6s ease-out 1s infinite}
@keyframes pop{from{opacity:0;scale:0}to{opacity:1;scale:1}}
@keyframes anillo{0%{box-shadow:0 0 0 0 rgba(230,126,34,.55)}70%,100%{box-shadow:0 0 0 22px rgba(230,126,34,0)}}
.slide.on .barra i{transform-origin:left;animation:crece .9s cubic-bezier(.2,.7,.2,1) both;animation-delay:calc(var(--i,0)*120ms + 500ms)}
.slide.on .barra i.r{animation:crece .9s cubic-bezier(.2,.7,.2,1) calc(var(--i,0)*120ms + 500ms) both,brillo 2.4s ease-in-out 2.4s infinite}
.slide.on .barra b{animation:sube .5s ease both;animation-delay:calc(var(--i,0)*120ms + 1200ms)}
@keyframes crece{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes brillo{0%,100%{filter:brightness(1)}50%{filter:brightness(1.35)}}
.slide.on .linea:before{transform-origin:left;animation:traza 1.1s cubic-bezier(.3,.7,.2,1) .5s both}
@keyframes traza{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.slide.on .dot.xl{animation:pop .5s cubic-bezier(.3,1.6,.5,1) both;animation-delay:calc(var(--i,0)*140ms + 800ms)}
.card{transition:transform .25s ease,box-shadow .25s ease}
.card:hover{transform:translateY(-5px);box-shadow:0 12px 26px rgba(0,0,0,.16)}
.card.oscura:hover,.card.tint:hover{box-shadow:0 12px 26px rgba(0,0,0,.25)}
.dot{transition:scale .2s ease}.fila:hover .dot{scale:1.12}
#prog{position:fixed;top:0;left:0;right:0;height:4px;background:rgba(255,255,255,.08);z-index:10}
#prog i{display:block;height:100%;background:var(--nar);transform-origin:left;transition:transform .5s cubic-bezier(.2,.7,.2,1)}
@media (prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important}}
@media print{#prog{display:none}.slide,.slide *,.slide *:before{animation:none!important;transition:none!important;translate:none!important;scale:none!important}}
"""

JS = r"""
const sl=[...document.querySelectorAll('.slide')],notas=document.getElementById('notas'),prog=document.querySelector('#prog i');
const quieto=matchMedia('(prefers-reduced-motion: reduce)').matches;
let i=-1,tok=0,salida=null;
// Qué entra escalonado en cada diapositiva: lo más exterior de cada bloque, en orden de lectura.
const SEL='h1,h2,.badge,.logo,.sub,.pie,.lead,.nota,.banda,.card,.fila,.num.xl,.split>img,img.ancho,.pila>*,.necesidades>*,.barras>*,.linea>div';
sl.forEach(s=>{const c=[...s.querySelectorAll(SEL)];
 c.filter(a=>!c.some(o=>o!==a&&o.contains(a))).forEach((el,k)=>{el.classList.add('rev');
  el.style.setProperty('--i',el.parentElement.classList.contains('barras')?Math.floor(k/3):Math.min(k,12))})});
// Contadores: solo cifras limpias («280.403», «93 %», «−0,9 %»); fechas, rangos y textos se quedan como están.
const CIFRA=/^([−-]?)(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?(\s*%)?$/;
function contar(el,t){
 const f=el.dataset.final||(el.dataset.final=el.textContent.trim()),m=f.match(CIFRA);el.textContent=f;
 if(!m||quieto)return;
 const dec=(m[3]||'').length,val=parseFloat(m[2].replace(/\./g,'')+(dec?'.'+m[3]:'')),suf=m[4]||'';
 const fmt=x=>{const[a,b]=x.toFixed(dec).split('.');return a.replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(b?','+b:'')};
 const r=el.closest('.rev'),ini=performance.now()+250+85*(r?parseInt(r.style.getPropertyValue('--i'))||0:0)+150;
 el.textContent=fmt(0)+suf;
 const paso=now=>{if(t!==tok){el.textContent=f;return}
  const p=Math.min(1,Math.max(0,(now-ini)/1300));{const v=fmt(val*(1-Math.pow(1-p,3)));el.textContent=p<1?(/[1-9]/.test(v)?m[1]:'')+v+suf:f}
  if(p<1)requestAnimationFrame(paso)};
 requestAnimationFrame(paso)}
const restaura=v=>v.querySelectorAll('.num[data-final]').forEach(e=>e.textContent=e.dataset.final);
const mmss=s=>{s=Math.round(Math.abs(s));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')};
function pinta(){const s=sl[i],cab=document.createElement('span');cab.className='cab';
 cab.textContent=`Diapositiva ${i+1} de ${sl.length} · ${s.dataset.min} min · acumulado ${mmss(s.dataset.acum*60)} de ${mmss(sl.reduce((a,x)=>a+parseFloat(x.dataset.min),0)*60)}`;
 notas.replaceChildren(cab,document.createTextNode(s.dataset.notas));notas.scrollTop=0}
// Cronómetro de ensayo (tecla T: arranca/pausa; Mayús+T: a cero). Compara con el plan de cada diapositiva.
const reloj=document.getElementById('reloj');let t0=0,acum=0,corre=false;
// «En hora» = dentro de la ventana prevista de la diapositiva actual (de cuándo debería empezar a cuándo debería acabar).
function tic(){const t=acum+(corre?(performance.now()-t0)/1000:0),fin=parseFloat(sl[i].dataset.acum)*60,ini=fin-parseFloat(sl[i].dataset.min)*60,
 d=t<ini?t-ini:t>fin?t-fin:0;
 reloj.textContent=`${mmss(t)} / ${mmss(sl.reduce((a,x)=>a+parseFloat(x.dataset.min),0)*60)} · diapositiva ${i+1}: ${mmss(ini)}–${mmss(fin)} · ${d===0?'en hora':mmss(d)+(d>0?' de retraso':' de adelanto')}`}
setInterval(tic,500);
function fit(){const k=Math.min(innerWidth/1280,innerHeight/720);sl.forEach(s=>s.style.transform=`scale(${k})`)}
function ver(n){n=Math.max(0,Math.min(sl.length-1,n));if(n===i)return;
 document.body.dataset.dir=n<i?'atras':'adelante';
 if(i>=0){const v=sl[i];restaura(v);v.classList.remove('on');
  if(!quieto){v.classList.add('sale');clearTimeout(salida);salida=setTimeout(()=>sl.forEach(s=>s.classList.remove('sale')),400)}}
 i=n;sl[i].classList.remove('sale');sl[i].classList.add('on');
 prog.style.transform=`scaleX(${(i+1)/sl.length})`;
 pinta();try{history.replaceState(null,'','#'+(i+1))}catch(e){}
 const t=++tok;sl[i].querySelectorAll('.num').forEach(el=>contar(el,t))}
addEventListener('beforeprint',()=>{tok++;sl.forEach(restaura)});
addEventListener('keydown',ev=>{if(['ArrowRight','PageDown',' '].includes(ev.key)){ev.preventDefault();ver(i+1)}
 else if(['ArrowLeft','PageUp'].includes(ev.key))ver(i-1);else if(ev.key==='Home')ver(0);else if(ev.key==='End')ver(sl.length-1);
 else if(ev.key==='n'||ev.key==='N')notas.classList.toggle('on');
 else if(ev.key==='T'){acum=0;t0=performance.now();tic()}
 else if(ev.key==='t'){if(corre){acum+=(performance.now()-t0)/1000;corre=false}else{t0=performance.now();corre=true;reloj.classList.add('on')}tic()}
 else if(ev.key==='f'||ev.key==='F'){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen()}});
document.getElementById('deck').addEventListener('click',ev=>ver(ev.clientX>innerWidth/3?i+1:i-1));
let x0=null;addEventListener('touchstart',e=>x0=e.touches[0].clientX);addEventListener('touchend',e=>{if(x0===null)return;const d=e.changedTouches[0].clientX-x0;if(Math.abs(d)>40)ver(d<0?i+1:i-1);x0=null});
addEventListener('resize',fit);fit();ver((parseInt(location.hash.slice(1))||1)-1);
"""

cuerpo = "".join(
    f'<section class="slide {c}" data-notas="{e(GUION[k]["texto"])}" data-min="{GUION[k]["min"]}" '
    f'data-acum="{sum(GUION[j]["min"] for j in range(1, k + 1))}" aria-label="Diapositiva {k}">{h}'
    + (f'<span class="num-pag">{k}</span>' if k > 1 else "") + "</section>"
    for k, (c, h) in enumerate(S, 1))
doc = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reto 1 · Burglar King</title><style>{CSS}</style></head>
<body><div id="prog"><i></i></div><div id="deck">{cuerpo}</div><div id="notas"></div>
<div id="reloj"></div><div id="ayuda">← → avanzar · N guion · T cronómetro · F pantalla completa</div><script>{JS}</script></body></html>"""
out = AQUI / "reto1_presentacion.html"
out.write_text(doc, encoding="utf-8")
print("HTML:", out, f"{out.stat().st_size/1024:.0f} KB · {len(S)} diapositivas")
