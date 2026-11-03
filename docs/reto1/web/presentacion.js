'use strict';
// Presentación del Reto 1. Con servidor.py todo es global (diapositiva, cronómetro, animaciones, cuestionario y
// laboratorios) y cada equipo elige su vista: presentación (pizarra, principal), público (sigue y vota),
// pc (guion con edición) o mando (móvil). Abierta como fichero, cada equipo va por su cuenta.
const $=s=>document.querySelector(s);
const sl=[...document.querySelectorAll('.slide')],notas=document.getElementById('notas'),prog=document.querySelector('#prog i'),deck=document.getElementById('deck');
const PAR=new URLSearchParams(location.search);
const VISTA=(v=>({guion:'pc',diapositiva:'presentacion'})[v]||(['presentacion','publico','pc','mando'].includes(v)?v:'presentacion'))(PAR.get('vista'));
const CONTROL=VISTA!=='publico';
const NOMBRE={presentacion:'Presentación (pizarra)',publico:'Público',pc:'PC · guion del orador',mando:'Móvil · mando'};
document.body.classList.add('v-'+VISTA);
const EN_RED=location.protocol.startsWith('http');
let red=EN_RED;                              // pasa a false si resulta que no hay servidor.py detrás
const guarda=(k,v)=>{try{localStorage.setItem(k,typeof v==='string'?v:JSON.stringify(v))}catch(e){}};
const lee=(k,def)=>{try{const v=localStorage.getItem(k);return v===null?def:v}catch(e){return def}};
const leeJSON=(k,def)=>{try{return JSON.parse(lee(k,''))||def}catch(e){return def}};

/* ---------- Movimiento ---------- */
const SO_QUIETO=matchMedia('(prefers-reduced-motion: reduce)').matches;
let eleccion=lee('reto1_mov',null);
const pedido=PAR.get('movimiento');
if(pedido==='1'||pedido==='0'){eleccion=pedido==='1'?'on':'off';guarda('reto1_mov',eleccion)}
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
 if(!m||quieto||/^\d$/.test(f))return;                // una sola cifra (los 3 socios) sale ya con su valor: contando, se leía un 2
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
const toast=document.getElementById('toast');let tt=null;
function aviso(t,ms){toast.textContent=t;toast.classList.add('on');clearTimeout(tt);tt=setTimeout(()=>toast.classList.remove('on'),ms||2200)}
function ponQuieto(v){quieto=v;document.documentElement.dataset.mov=v?'off':'on';guarda('reto1_mov',v?'off':'on');
 if(VISTA==='presentacion')aviso(v?'Movimiento desactivado':'Movimiento activado');
 const s=sl[i];if(s){s.classList.remove('on','sale');void s.offsetWidth;s.classList.add('on');const t=++tok;s.querySelectorAll('.num').forEach(el=>contar(el,t))}
 UI.ctx()}
function alterna(){if(red)return manda('mov',{mov:quieto?'on':'off'});ponQuieto(!quieto)}
addEventListener('beforeprint',()=>{tok++;sl.forEach(restaura)});

/* ---------- Guion y notas rápidas (editables desde el PC) ---------- */
sl.forEach(s=>{s.dataset.notasOrig=s.dataset.notas;s.dataset.rapidasOrig=s.dataset.rapidas||'[]'});
const rapidas=s=>{try{return JSON.parse(s.dataset.rapidas||'[]')}catch(e){return[]}};
let editando=null;
function pintaNotas(){if(editando!==null)return;
 const s=sl[i],cab=document.createElement('span'),txt=document.createElement('div');cab.className='cab';txt.className='texto';
 cab.textContent=`Diapositiva ${i+1} de ${sl.length} · ${s.dataset.min} min · acumulado ${mmss(s.dataset.acum*60)} de ${mmss(TOTAL*60)}`;
 conTachado(txt,s.dataset.notas);notas.replaceChildren(cab,txt);notas.scrollTop=0}
// En el guion y en las notas rápidas, lo escrito entre <tachar> y <tachar> (o </tachar>) se ve tachado.
function conTachado(el,texto){el.replaceChildren();let tachar=false;
 for(const trozo of String(texto||'').split(/<\/?tachar>/i)){if(trozo)el.append(tachar?Object.assign(document.createElement('s'),{textContent:trozo}):trozo);tachar=!tachar}}
function aplicaGuion(d){const s=sl[d.n-1];if(!s)return;
 if(d.borrar){s.dataset.notas=s.dataset.notasOrig;s.dataset.rapidas=s.dataset.rapidasOrig}
 else{s.dataset.notas=d.texto;s.dataset.rapidas=JSON.stringify(d.rapidas||[])}
 if(d.n-1===i)UI.pinta()}

/* ---------- Cronómetro (global) ---------- */
let crono={corre:false,acum:0,desde:0},desfase=0;     // desfase: reloj del servidor menos el de este equipo (ms)
const tiempo=()=>crono.acum+(crono.corre?(Date.now()+desfase-crono.desde)/1000:0);
const reloj=document.getElementById('reloj');
let diapoT0={i:-1,t:0};                               // en qué momento de la presentación se entró en la diapositiva actual
function tic(){if(i<0)return;const t=tiempo(),fin=parseFloat(sl[i].dataset.acum)*60,ini=fin-parseFloat(sl[i].dataset.min)*60,
 d=t<ini?t-ini:t>fin?t-fin:0,hora=d===0?'en hora':mmss(d)+(d>0?' de retraso':' de adelanto');
 // Estado del ritmo, que da el color: en hora (verde), adelanto (azul), retraso < 1 min (ámbar), retraso mayor (rojo).
 const est=!crono.corre&&t===0?'parado':d===0?'en-hora':d<0?'adelanto':d<60?'retraso':'tarde',T=TOTAL*60||1;
 const txt=!crono.corre?(t>0?'en pausa · '+hora:'pulsa ▶ para empezar'):hora;
 const html=`<b class="cr-t">${mmss(t)}</b><span class="cr-de">de ${mmss(T)}</span><span class="cr-est">${txt}</span>`+
  `<span class="cr-dia">Diapositiva ${i+1}: debería ir entre ${mmss(ini)} y ${mmss(fin)}</span>`+
  `<span class="cr-barra"><i class="v" style="left:${(ini/T*100).toFixed(2)}%;width:${((fin-ini)/T*100).toFixed(2)}%"></i><i class="p" style="width:${Math.min(100,t/T*100).toFixed(2)}%"></i></span>`;
 if(diapoT0.i!==i||t<diapoT0.t)diapoT0={i,t};
 if(VISTA==='pc')pintaGrande(reloj,{ed:t-diapoT0.t,nd:fin-ini,t,T,txt});else reloj.innerHTML=html;reloj.dataset.estado=est;
 reloj.classList.toggle('corre',crono.corre);UI.tic(t,ini,fin,hora,html,est);pintaFlot()}
setInterval(tic,500);
function cronoAlterna(){if(red)return manda('crono',{accion:'alterna'});
 const ahora=Date.now();if(crono.corre){crono.acum+=(ahora-crono.desde)/1000;crono.corre=false}else{crono.desde=ahora;crono.corre=true}
 reloj.classList.add('on');tic();UI.ctx()}
function cronoReinicia(){if(red)return manda('crono',{accion:'reinicia'});crono.acum=0;crono.desde=Date.now();tic()}
/* Cronómetro grande del PC. Primera línea: tiempo en esta diapositiva / previsto · diapositiva n/total · tiempo total;
   debajo, lo que queda de esta diapositiva (diez veces mayor) y lo que queda de la presentación (cinco veces).
   Se construye una sola vez y luego solo cambian los textos, para que el recuadro de ayuda no parpadee. */
function pintaGrande(el,v){
 if(!el.querySelector('.cg1'))el.innerHTML='<div class="cg1"><span class="cg-ed" data-tip="Tiempo que llevas en esta diapositiva"></span> / '+
  '<span class="cg-nd" data-tip="Tiempo previsto en el guion para esta diapositiva"></span> · <span class="cg-n" data-tip="Diapositiva actual / número de diapositivas"></span> · '+
  '<span class="cg-tt"></span><span class="cg-pausa"></span></div><div class="cg2"><span></span></div><div class="cg3"><span></span></div>';
 const q=s=>el.querySelector(s),rd=v.nd-v.ed,rp=v.T-v.t,d2=q('.cg2 span'),d3=q('.cg3 span');
 q('.cg-ed').textContent=mmss(v.ed);q('.cg-nd').textContent=mmss(v.nd);q('.cg-n').textContent=`${i+1}/${sl.length}`;q('.cg-tt').textContent=mmss(v.t);
 q('.cg-tt').dataset.tip=`Tiempo total transcurrido de la presentación (${v.txt})`;
 q('.cg-pausa').textContent=crono.corre?'':' · '+(v.t>0?'⏸ en pausa':'pulsa ▶ para empezar');
 d2.textContent=(rd<0?'−':'')+mmss(rd);d2.parentElement.classList.toggle('pasado',rd<0);
 d2.dataset.tip=rd<0?`Cuenta atrás de esta diapositiva: te pasas en ${mmss(rd)} de los ${mmss(v.nd)} previstos`:`Cuenta atrás de esta diapositiva: queda ${mmss(rd)} de los ${mmss(v.nd)} previstos`;
 d3.textContent=(rp<0?'−':'')+mmss(rp);d3.parentElement.classList.toggle('pasado',rp<0);
 d3.dataset.tip=rp<0?`Cuenta atrás de la presentación: te pasas en ${mmss(rp)} de los ${mmss(v.T)} previstos`:`Cuenta atrás de la presentación: queda ${mmss(rp)} de los ${mmss(v.T)} previstos`;
 const h=el.offsetHeight+'px';if(document.body.style.getPropertyValue('--rh')!==h)document.body.style.setProperty('--rh',h)}
const textoCrono=()=>crono.corre?'⏸ Pausar':crono.acum>0?'▶ Seguir':'▶ Cronómetro';

/* ---------- Navegación ---------- */
function fit(){const k=Math.min(deck.clientWidth/1280,deck.clientHeight/720);sl.forEach(s=>s.style.transform=`scale(${k})`)}
// ir(): lo que pide un control (teclas, clic, botones); ver(): lo que se muestra, también cuando llega del servidor.
// Las diapositivas .opcional (el cuestionario) solo se abren a propósito: ir(n,true).
const opcional=k=>!!sl[k]&&sl[k].classList.contains('opcional');
const ultimaNormal=()=>{let k=sl.length-1;while(k>0&&opcional(k))k--;return k};
function ir(n,forzar){if(!CONTROL&&red)return;n=Math.max(0,Math.min(sl.length-1,n));
 if(!forzar&&opcional(n)&&!opcional(i))return;ver(n);if(red)manda('ir',{i:n})}
function ver(n){n=Math.max(0,Math.min(sl.length-1,n));if(n===i)return;
 document.body.dataset.dir=n<i?'atras':'adelante';
 if(i>=0){const v=sl[i];restaura(v);v.classList.remove('on');
  if(!quieto){v.classList.add('sale');clearTimeout(salida);salida=setTimeout(()=>sl.forEach(s=>s.classList.remove('sale')),650)}}
 i=n;sl[i].classList.remove('sale');sl[i].classList.add('on');
 prog.style.transform=`scaleX(${(i+1)/sl.length})`;
 try{history.replaceState(null,'','#'+(i+1))}catch(e){}
 const t=++tok;sl[i].querySelectorAll('.num').forEach(el=>contar(el,t));
 document.body.classList.toggle('lab',sl[i].classList.contains('labframe'));
 cargaLabs(sl[i]);
 if(sl[i].classList.contains('quiz'))quizMuestra();
 UI.pinta();tic()}
function pantallaCompleta(){document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen().catch(()=>{})}
// Dentro de un laboratorio, del cuestionario o de una barra, el teclado y el ratón son suyos.
const interactivo=el=>el&&el.closest&&el.closest('#quiz,.labbar,#barra,#herr,#lateral,#movil,#voto,iframe,input,button,textarea,select');
addEventListener('keydown',ev=>{const tg=ev.target;
 if(document.getElementById('pin')||(tg&&tg.closest&&tg.closest('input,textarea,select,[contenteditable]')))return;
 if(interactivo(tg)&&['ArrowRight','ArrowLeft',' '].includes(ev.key))return;
 if(ev.key==='f'||ev.key==='F')return pantallaCompleta();
 if(!CONTROL)return;
 if(['ArrowRight','PageDown',' '].includes(ev.key)){ev.preventDefault();ir(i+1)}
 else if(['ArrowLeft','PageUp'].includes(ev.key))ir(i-1);else if(ev.key==='Home')ir(0);else if(ev.key==='End')ir(ultimaNormal());
 else if((ev.key==='n'||ev.key==='N')&&VISTA==='presentacion')notas.classList.toggle('on');
 else if(ev.key==='m'||ev.key==='M')alterna();
 else if(ev.key==='T')cronoReinicia();
 else if(ev.key==='t')cronoAlterna()});
deck.addEventListener('click',ev=>{if(interactivo(ev.target)||VISTA!=='presentacion')return;ir(ev.clientX>innerWidth/3?i+1:i-1)});
let x0=null;addEventListener('touchstart',e=>{x0=!CONTROL||interactivo(e.target)?null:e.touches[0].clientX});
addEventListener('touchend',e=>{if(x0===null)return;const d=e.changedTouches[0].clientX-x0;if(Math.abs(d)>40)ir(d<0?i+1:i-1);x0=null});
// Tras pulsar un botón de una barra, el foco vuelve a la página para que las flechas sigan avanzando.
document.addEventListener('click',ev=>{const b=ev.target.closest&&ev.target.closest('#barra button,#herr button,#lateral button,#movil button');if(b)b.blur()});

/* ---------- Laboratorios: se ejecutan en la pizarra principal y los demás reciben un espejo ---------- */
const BOTONES_LAB={'red.html':[['sim_actual','Red actual'],['sim_prop','Red segmentada'],['sim_ambas','Las dos seguidas'],['reiniciar','Reiniciar']],
 'verifactu.html':[['simular','Simular'],['alterar','Rebajar la factura 2'],['restaurar','Restaurar las originales']],
 'hora_punta.html':[['empezar','Simular el servicio'],['pausa','Pausa / seguir']]};
const labDe=f=>(f.dataset.lab||f.dataset.src||'').split('/').pop();
let miId=null,soyPrincipal=false;
// Los espejos cargan el laboratorio sin sus scripts (srcdoc en un sandbox): solo muestran lo que manda la pizarra.
const ejecutaLabs=()=>!red||(VISTA==='presentacion'&&soyPrincipal);
const LABS={};
function cargaLab(f){const url=f.dataset.lab;
 if(ejecutaLabs()){f.removeAttribute('sandbox');f.removeAttribute('srcdoc');f.src=url;return}
 f.setAttribute('sandbox','allow-same-origin');f.removeAttribute('src');
 fetch(url).then(r=>r.text()).then(t=>{f.srcdoc=t.replace(/<script[\s\S]*?<\/script>/gi,'').replace(/<head>/i,`<head><base href="${new URL(url,location.href).href}">`)})}
function cargaLabs(s){if(VISTA==='mando')return;
 s.querySelectorAll('iframe[data-src]').forEach(f=>{f.dataset.lab=f.dataset.src;f.removeAttribute('data-src');
  f.addEventListener('load',()=>labCargado(f));cargaLab(f)})}
function rolLabs(){document.body.classList.toggle('espejo',red&&!ejecutaLabs());
 document.querySelectorAll('iframe[data-lab]').forEach(f=>{if(ejecutaLabs()!==!f.hasAttribute('sandbox'))cargaLab(f)})}
function labCargado(f){const lab=labDe(f),L=LABS[lab]||(LABS[lab]={});L.f=f;L.listo=false;
 if(L.obs){L.obs.disconnect();L.obs=null}
 if(!red)return;
 if(!ejecutaLabs())return pideFoto(lab);
 const doc=f.contentDocument;if(!doc||!doc.body)return;
 L.sucias=new Set();L.todo=false;
 L.obs=new MutationObserver(rs=>{rs.forEach(r=>{let n=r.target.nodeType===1?r.target:r.target.parentElement;
   while(n&&n!==doc.body&&!n.id)n=n.parentElement;if(!n||n===doc.body)L.todo=true;else L.sucias.add(n)});programa(lab)});
 L.obs.observe(doc.body,{subtree:true,childList:true,attributes:true,characterData:true});
 ['input','change','scroll'].forEach(t=>doc.addEventListener(t,()=>programa(lab),true));
 setTimeout(()=>mandaFoto(lab),250)}
function programa(lab){const L=LABS[lab];if(L.temp)return;L.temp=setTimeout(()=>{L.temp=null;mandaParche(lab)},120)}
// El documento entero (html) no entra aquí: su desplazamiento viaja aparte, en «arriba».
function ruta(el,doc){if(el.id)return '#'+el.id;const p=[];while(el&&el!==doc.body&&el.parentElement){p.unshift([...el.parentElement.children].indexOf(el));el=el.parentElement}return p.join('.')}
function busca(r,doc){if(r[0]==='#')return doc.getElementById(r.slice(1));let el=doc.body;for(const k of r.split('.').filter(x=>x!==''))el=el&&el.children[+k];return el}
function extras(doc){return{valores:[...doc.querySelectorAll('input,select,textarea')].map(e=>[ruta(e,doc),e.value,e.checked===true]),
 scroll:[...doc.querySelectorAll('*')].filter(e=>e.scrollTop>0&&e!==doc.documentElement&&e!==doc.body).map(e=>[ruta(e,doc),e.scrollTop]),arriba:(doc.scrollingElement||doc.documentElement).scrollTop}}
function mandaParche(lab){const L=LABS[lab],doc=L.f&&L.f.contentDocument;if(!doc||!doc.body||!ejecutaLabs())return;
 let raices=[...L.sucias].filter(n=>doc.body.contains(n));L.sucias.clear();
 if(L.todo||raices.length>40){L.todo=false;return mandaFoto(lab)}
 raices=raices.filter(n=>!raices.some(o=>o!==n&&o.contains(n)));
 manda('lab/parche',{id:miId,lab,raices:raices.map(n=>[n.id,n.outerHTML]),...extras(doc)})}
function mandaFoto(lab){const L=LABS[lab],doc=L&&L.f&&L.f.contentDocument;if(!doc||!doc.body||!ejecutaLabs())return;
 manda('lab/foto',{id:miId,lab,html:doc.body.innerHTML,clase:doc.body.className,...extras(doc)})}
function aplicaLab(d,foto){const L=LABS[d.lab],doc=L&&L.f&&L.f.contentDocument;if(!doc||!doc.body||ejecutaLabs())return;
 if(foto){doc.body.innerHTML=d.html;doc.body.className=d.clase||'';L.listo=true}
 else{if(!L.listo)return pideFoto(d.lab);
  for(const[id,html]of d.raices){const el=doc.getElementById(id);if(!el){L.listo=false;return pideFoto(d.lab)}el.outerHTML=html}}
 for(const[r,v,c]of d.valores||[]){const el=busca(r,doc);if(el){el.value=v;if(el.type==='checkbox'||el.type==='radio')el.checked=c}}
 for(const[r,top]of d.scroll||[]){const el=busca(r,doc);if(el)el.scrollTop=top}
 (doc.scrollingElement||doc.documentElement).scrollTop=d.arriba||0}
function pideFoto(lab){if(red)fetch('lab/pedir',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lab})}).catch(()=>{})}
function pulsaLab(lab,id){const L=LABS[lab],b=L&&L.f&&L.f.contentDocument&&L.f.contentDocument.getElementById(id);if(b&&!b.disabled)b.click()}
function labAccion(lab,id){if(red)return manda('lab/accion',{lab,id});pulsaLab(lab,id)}

/* ---------- Cuestionario ---------- */
const PREG=[
 {q:'¿Cuántas instalaciones al año necesita ServiPass para no perder dinero?',o:['18','22','27','45'],ok:2,
  x:'<b>Unas 27</b> (26 el primer año): cada instalación deja 3.340 € de margen, o 2.440 € si el local ya tiene la licencia por ser mecenas, y los costes fijos que deben cubrir son unos 76.200 € el primer año. Con 18 instalaciones, el primer año cierra con −24.158 €.'},
 {q:'¿Desde cuándo tiene que facturar Burglar King, que es una sociedad, con un sistema que cumpla Verifactu?',o:['1 de enero de 2026','1 de julio de 2026','1 de enero de 2027','1 de julio de 2027'],ok:2,
  x:'<b>El 1 de enero de 2027</b> para las sociedades; el resto, el 1 de julio de 2027 (Real Decreto-ley 15/2025). Por eso el TPV de ServiPass cumple Verifactu antes de vender la primera licencia.'},
 {q:'¿Cuánto pagaría en diez años un local por el plan básico de Last.app con su pantalla de cocina?',o:['1.800 €','4.250 €','10.700 €','25.000 €'],ok:2,
  x:'<b>10.700 €</b>: 85 € al mes durante diez años más 500 € de alta, solo por el software. La licencia de ServiPass del mismo periodo cuesta 1.800 €.'},
 {q:'En la cadena de facturas, alguien rebaja el precio de la factura 2 de 3. ¿Qué se ve al verificar?',o:['Nada: la huella solo usa el número de factura','Solo cambia el total de la factura 2','La huella de la 2 deja de cuadrar y la 3 ya no encaja con ella','Hacienda corrige el precio sola'],ok:2,
  x:'<b>Se rompe la cadena</b>: la huella de la factura 2 se calcula con su importe, así que al recalcularla ya no coincide con la registrada, y la 3 guarda la huella antigua de la 2. La única corrección válida es una factura rectificativa.'},
 {q:'Con la red segmentada que instala ServiPass, ¿qué puede hacer el móvil de un cliente conectado a la wifi del local?',o:['Llegar a la caja para pagar','Ver las cámaras','Navegar por internet, pero no llegar a la caja ni al grabador','Nada: la wifi de clientes desaparece'],ok:2,
  x:'<b>Solo internet</b>: la red de clientes queda separada de la del negocio y de la de las cámaras. Lo necesario funciona y lo peligroso queda bloqueado.'},
 {q:'En la campaña de micromecenazgo de ServiPass, ¿qué recibe quien aporta 10 €?',o:['Nada: es una donación','Diez años de licencia','La licencia de por vida','Una participación en la empresa'],ok:2,
  x:'<b>La licencia de por vida</b>. Desde 1 € son diez años; desde 100 €, además, las expansiones de la siguiente versión, y desde 500 €, soporte gratis para siempre. Es micromecenazgo de recompensa: no es un préstamo ni una participación, sino una venta anticipada que lleva IVA.'}];
const letra=k=>String.fromCharCode(65+k);
const Q=document.getElementById('quiz');
const msgFinal=n=>{const N=PREG.length;return n===N?'¡Pleno! Habéis escuchado de verdad.':n===N-1?'Muy bien: solo una se ha escapado.':n*2>=N?'Más de la mitad: buen trabajo.':n>0?`${n} de ${N}: el informe tiene las respuestas.`:'Ninguna… toca releer el informe.'};
function confeti(){if(quieto)return;const c=document.createElement('div');c.className='conf';
 for(let k=0;k<80;k++){const e=document.createElement('i');e.style.left=Math.random()*100+'%';e.style.background=['#e67e22','#27ae60','#f1c40f','#3498db'][k%4];e.style.animationDelay=Math.random()*1.2+'s';e.style.animationDuration=(2+Math.random()*1.5)+'s';c.append(e)}
 sl[i].append(c);setTimeout(()=>c.remove(),4500)}
// Sin servidor: cada equipo responde su cuestionario, como siempre.
let qi=0,qp=0;
function quizInicio(){qi=0;qp=0;quizPinta()}
function quizPinta(){if(qi>=PREG.length){quizFin();return}
 const p=PREG[qi];Q.innerHTML=`<div class="qn">Pregunta ${qi+1} de ${PREG.length} · aciertos: ${qp}</div><div class="q">${p.q}</div>
  <div class="ops">${p.o.map((o,k)=>`<button data-k="${k}">${letra(k)}. ${o}</button>`).join('')}</div><div class="fb"></div><div class="qbar"><span class="pts"></span></div>`;
 Q.querySelectorAll('.ops button').forEach(b=>b.addEventListener('click',()=>{const k=+b.dataset.k,ok=k===p.ok;if(ok)qp++;
  Q.querySelectorAll('.ops button').forEach(x=>{x.disabled=true;if(+x.dataset.k===p.ok)x.classList.add('ok')});if(!ok)b.classList.add('ko');
  Q.querySelector('.fb').innerHTML=(ok?'✔ Correcto. ':'✘ No. ')+p.x;
  const sig=document.createElement('button');sig.textContent=qi<PREG.length-1?'Siguiente pregunta →':'Ver resultado';sig.addEventListener('click',()=>{qi++;quizPinta()});
  Q.querySelector('.qbar').append(sig)}))}
function quizFin(){Q.innerHTML=`<div class="final"><div class="qn">Resultado</div><b class="num">${qp} / ${PREG.length}</b><p>${msgFinal(qp)}</p><button class="otra">Repetir el cuestionario</button></div>`;
 Q.querySelector('.otra').addEventListener('click',quizInicio);if(qp*3>=PREG.length*2)confeti()}
// Con servidor: vota el público y la pizarra enseña el recuento en directo.
let quiz=null,ultimo={};
const cid=lee('reto1_cid','')||(()=>{const c=Math.random().toString(36).slice(2)+Date.now().toString(36);guarda('reto1_cid',c);return c})();
let misVotos=leeJSON('reto1_votos',{ronda:0,v:{}});
const enQuiz=()=>!!sl[i]&&sl[i].classList.contains('quiz');
function quizMuestra(){if(!red)return quizInicio();if(!quiz)return;
 if(VISTA==='presentacion'&&soyPrincipal&&quiz.fase==='espera')manda('quiz',{accion:'abrir'});
 pintaQuiz()}
const ctl=(a,t)=>`<button class="ctl" onclick="quizAccion('${a}')">${t}</button>`;
function quizAccion(a){if(red)manda('quiz',{accion:a})}
const botonQuiz=(q,n)=>q.fase==='espera'?ctl('abrir','Abrir la votación'):q.fase==='votando'?ctl('cerrar','Cerrar y ver la respuesta'):q.fase==='resuelta'?ctl('siguiente',n<PREG.length-1?'Siguiente pregunta →':'Ver el resultado'):ctl('reiniciar','Repetir el cuestionario');
function htmlPizarra(){const q=quiz,n=q.q,p=PREG[n],r=q.recuentos[n],tot=r.reduce((a,b)=>a+b,0),pub=(ultimo.clientes||{}).publico||0;
 const unete=`<span class="unete">Vota desde el móvil: <b>${ultimo.publico_url||''}</b></span>`;
 if(q.fase==='fin')return `<div class="qn">Resultado de la votación</div>${PREG.map((p,k)=>{const r=q.recuentos[k],t=r.reduce((a,b)=>a+b,0),pc=t?Math.round(100*r[p.ok]/t):0;
   return `<div class="res-q"><span>${k+1}. ${p.q}</span><div class="barra-voto" style="--p:${pc}%"><b>${pc} %</b> ha acertado (${r[p.ok]} de ${t})</div></div>`}).join('')}<div class="qbar">${unete}${botonQuiz(q,n)}</div>`;
 const res=q.fase==='resuelta',est=q.fase==='espera'?'la votación aún no está abierta':q.fase==='votando'?'votación abierta':'votación cerrada';
 return `<div class="qn">Pregunta ${n+1} de ${PREG.length} · ${est} · ${tot} voto${tot===1?'':'s'} de ${pub} conectado${pub===1?'':'s'}</div><div class="q">${p.q}</div>
  <div class="ops votos">${p.o.map((o,k)=>{const pc=tot?Math.round(100*r[k]/tot):0;
   return `<div class="opv${res?(k===p.ok?' ok':' apagada'):''}" style="--p:${pc}%"><span>${letra(k)}. ${o}</span><b>${r[k]} · ${pc} %</b></div>`}).join('')}</div>
  <div class="fb">${res?'✔ '+p.x:''}</div><div class="qbar">${unete}${botonQuiz(q,n)}</div>`}
function htmlVoto(){const q=quiz,n=q.q,p=PREG[n];
 if(misVotos.ronda!==q.ronda){misVotos={ronda:q.ronda,v:{}};guarda('reto1_votos',misVotos)}
 const mio=misVotos.v[n];
 if(q.fase==='espera')return `<div class="qn">Cuestionario</div><div class="q">La votación se abre enseguida.</div><p class="fb">Mira la pizarra.</p>`;
 if(q.fase==='fin'){const ac=PREG.filter((p,k)=>misVotos.v[k]===p.ok).length;
  return `<div class="final"><div class="qn">Tu resultado</div><b class="num">${ac} / ${PREG.length}</b><p>${msgFinal(ac).replace('Habéis escuchado','Has escuchado')}</p></div>`}
 const res=q.fase==='resuelta';
 return `<div class="qn">Pregunta ${n+1} de ${PREG.length}</div><div class="q">${p.q}</div>
  <div class="ops">${p.o.map((o,k)=>`<button data-k="${k}" ${res?'disabled':''} class="${mio===k?'mio':''} ${res&&k===p.ok?'ok':''} ${res&&mio===k&&k!==p.ok?'ko':''}">${letra(k)}. ${o}</button>`).join('')}</div>
  <div class="fb">${res?(mio===undefined?'No has votado. ':mio===p.ok?'✔ Has acertado. ':'✘ No era esa. ')+p.x:mio===undefined?'Toca una respuesta.':`Has votado la <b>${letra(mio)}</b>. Puedes cambiarla hasta que se cierre la votación.`}</div>`}
function vota(k){const n=quiz.q;misVotos.v[n]=k;guarda('reto1_votos',misVotos);UI.voto();
 fetch('votar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cid,q:n,o:k})}).then(r=>{if(!r.ok){delete misVotos.v[n];guarda('reto1_votos',misVotos);UI.voto()}}).catch(()=>{})}
function pintaQuiz(){if(!quiz)return;if(VISTA==='publico')return UI.voto();if(enQuiz())Q.innerHTML=htmlPizarra();UI.ctx()}
// Panel de contexto del PC y del móvil: botones del laboratorio o mandos del cuestionario.
function htmlCtx(){const s=sl[i];if(!s)return '';const f=s.querySelector('iframe');
 if(f){const lab=labDe(f);return `<h3>Laboratorio en la pizarra</h3><div class="botones">${(BOTONES_LAB[lab]||[]).map(([id,t])=>`<button onclick="labAccion('${lab}','${id}')">▶ ${t}</button>`).join('')}</div>${red&&!ultimo.principal?'<p class="peq">No hay ninguna pizarra conectada: los botones no harán nada.</p>':''}`}
 if(enQuiz()&&red&&quiz){const n=quiz.q,p=PREG[n],r=quiz.recuentos[n],tot=r.reduce((a,b)=>a+b,0);
  return `<h3>Cuestionario · ${quiz.fase==='fin'?'resultado':`pregunta ${n+1} de ${PREG.length}`}</h3>${quiz.fase==='fin'?'':`<div class="mini-votos">${p.o.map((o,k)=>`<div class="${k===p.ok?'ok':''}" style="--p:${tot?Math.round(100*r[k]/tot):0}%">${letra(k)}. ${o} · <b>${r[k]}</b></div>`).join('')}</div>
   <p class="peq">${tot} voto(s) de ${(ultimo.clientes||{}).publico||0} conectado(s) · correcta: ${letra(p.ok)}</p>`}<div class="botones">${botonQuiz(quiz,n)}${quiz.fase!=='fin'?ctl('reiniciar','Repetir cuestionario'):''}</div>`}
 if(opcional(i+1)&&!opcional(i))return `<h3>Al terminar</h3><div class="botones"><button onclick="ir(i+1,true)">¿? Abrir las preguntas para el público</button></div><p class="peq">Opcional: «Siguiente» no pasa a ellas.</p>`;
 return ''}

/* ---------- Conexión con el servidor ---------- */
let token=lee('reto1_token',''),es=null,caido=false;
function manda(ruta,datos){if(!red)return Promise.resolve(null);
 return fetch(ruta,{method:'POST',headers:{'Content-Type':'application/json','X-Token':token},body:JSON.stringify(datos)})
  .then(r=>{if(r.status===401&&CONTROL)pidePin('La sesión ha caducado: vuelve a escribir el PIN.');return r.ok?r.json():null}).catch(()=>null)}
function sinServidor(txt){red=false;estadoRed(null,txt);rolLabs()}
function compruebaToken(){fetch('token',{headers:{'X-Token':token}}).then(r=>{if(r.status===200)conecta();else if(r.status===401)pidePin();else sinServidor('sin servidor: modo local')})
 .catch(()=>{estadoRed(null);setTimeout(compruebaToken,3000)})}
function pidePin(msg){if(document.getElementById('pin'))return;if(es){es.close();es=null}
 const d=document.createElement('div');d.id='pin';
 d.innerHTML=`<form><img src="fig/logo_servipass.png" alt="Logo de ServiPass"><h2>${NOMBRE[VISTA]}</h2><p>Escribe el PIN que muestra el servidor al arrancar.</p>
  <input inputmode="numeric" pattern="[0-9]*" maxlength="4" autocomplete="off" aria-label="PIN"><button class="prim">Entrar</button><p class="err">${msg||''}</p><a href="presentacion.html?vista=publico">Soy del público</a></form>`;
 document.body.append(d);const inp=d.querySelector('input'),err=d.querySelector('.err');inp.focus();
 d.querySelector('form').addEventListener('submit',ev=>{ev.preventDefault();
  fetch('entrar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin:inp.value})}).then(r=>r.json().then(j=>[r.status,j]))
   .then(([st,j])=>{if(st===200){token=j.token;guarda('reto1_token',token);d.remove();conecta();return}
    err.textContent=st===429?`Demasiados intentos: espera ${j.espera} s.`:`PIN incorrecto${j.intentos!==undefined?` (quedan ${j.intentos} intentos)`:''}.`;inp.value='';inp.focus()})
   .catch(()=>{err.textContent='No se llega al servidor.'})})}
function conecta(){if(es)es.close();
 es=new EventSource(`eventos?vista=${VISTA}`+(CONTROL?`&token=${encodeURIComponent(token)}`:''));
 const json=f=>ev=>f(JSON.parse(ev.data));
 es.addEventListener('hola',json(d=>{miId=d.id}));
 es.addEventListener('estado',json(d=>{aplicaEstado(d);if(caido){caido=false;if(VISTA!=='publico')aviso('Conexión recuperada')}}));
 es.addEventListener('guion',json(aplicaGuion));
 es.addEventListener('equipos',json(d=>{EQUIPOS=d.lista||[];pintaFlot()}));
 es.addEventListener('lab_parche',json(d=>aplicaLab(d,false)));
 es.addEventListener('lab_foto',json(d=>aplicaLab(d,true)));
 es.addEventListener('lab_pedir',json(d=>{if(ejecutaLabs())mandaFoto(d.lab)}));
 es.addEventListener('lab_accion',json(d=>{if(ejecutaLabs())pulsaLab(d.lab,d.id)}));
 es.onerror=()=>{estadoRed(null);
  if(es.readyState===EventSource.CLOSED){es=null;return CONTROL?compruebaToken():sinServidor('sin servidor: modo local')}
  if(!caido){caido=true;aviso('Sin conexión con el servidor: se reintenta solo',4000)}}}
function aplicaEstado(d){ultimo=d;desfase=d.ahora-Date.now();crono=d.crono;
 const p=VISTA==='presentacion'&&d.principal===miId;if(p!==soyPrincipal){soyPrincipal=p;rolLabs()}else document.body.classList.toggle('espejo',!ejecutaLabs());
 if(d.mov&&(d.mov==='off')!==quieto)ponQuieto(d.mov==='off');
 const alFin=quiz&&quiz.fase!=='fin'&&d.quiz.fase==='fin';quiz=d.quiz;
 if(d.i!==i)ver(d.i);else if(enQuiz())pintaQuiz();
 if(alFin&&VISTA==='presentacion'&&enQuiz()){const ac=PREG.map((p,k)=>{const r=quiz.recuentos[k],t=r.reduce((a,b)=>a+b,0);return t?r[p.ok]/t:0});if(ac.reduce((a,b)=>a+b,0)/PREG.length>=.5)confeti()}
 estadoRed(d);UI.ctx();tic()}
const VISTAS_N=[['presentacion','pizarra'],['publico','público'],['pc','PC'],['mando','móvil']];
function estadoRed(d,txt){const el=document.getElementById('sincro');if(!el)return;const det=document.createElement('span');det.className='largo';
 if(!d){el.className='off';det.textContent=' '+(txt||'sin conexión');el.replaceChildren('○',det);return}
 const c=d.clientes||{};el.className='on';
 det.innerHTML=' en red · '+VISTAS_N.map(([v,n])=>`<span class="sv" data-v="${v}" tabindex="0">${c[v]||0} ${n}</span>`).join(' · ');el.replaceChildren('●',det)}
/* Flotante de equipos: al pasar por encima de «pizarra», «público», «PC» o «móvil» (o al tocarlo en el móvil),
   sus equipos con MAC, IP y «visto hace»; los desconectados se ven 10 minutos, con una barra que se vacía. */
let EQUIPOS=[],flotV=null,flotEl=null;
const flot=document.createElement('div');flot.id='flot';document.body.append(flot);
function abreFlot(el){flotV=el.dataset.v;flotEl=el;flot.classList.add('on');pintaFlot()}
function cierraFlot(){flotV=null;flotEl=null;flot.classList.remove('on')}
document.addEventListener('mouseover',ev=>{const s=ev.target.closest&&ev.target.closest('.sv');if(s)abreFlot(s)});
document.addEventListener('mouseout',ev=>{const s=ev.target.closest&&ev.target.closest('.sv');if(s&&!(ev.relatedTarget&&s.contains(ev.relatedTarget)))cierraFlot()});
document.addEventListener('click',ev=>{const s=ev.target.closest&&ev.target.closest('.sv');if(s){ev.stopPropagation();flotV===s.dataset.v?cierraFlot():abreFlot(s)}else if(flotV)cierraFlot()},true);
function pintaFlot(){if(!flotV)return;
 // al entrar o salir alguien se redibuja el contador: el flotante sigue abierto sobre el elemento nuevo
 if(!flotEl||!document.body.contains(flotEl))flotEl=document.querySelector(`#sincro .sv[data-v="${flotV}"]`);
 if(!flotEl)return cierraFlot();
 const nombre=(VISTAS_N.find(x=>x[0]===flotV)||[,''])[1],ahora=Date.now()+desfase;
 const lista=EQUIPOS.filter(e=>e.vista===flotV).map(e=>({...e,hace:Math.max(0,(ahora-e.visto)/1000)})).filter(e=>e.conectado||e.hace<=600);
 flot.innerHTML=`<h4>${nombre} · ${lista.filter(e=>e.conectado).length} conectado(s) · últimos 10 min</h4>`+(!CONTROL?'<p class="peq">Solo se ve con PIN.</p>':
  lista.length?lista.map(e=>`<div class="eq ${e.conectado?'on':'off'}"><b>${e.mac}</b><span>${e.ip}</span><span>${e.conectado?'conectado ahora':'visto hace '+mmss(e.hace)}</span><i style="width:${e.conectado?100:Math.max(0,100-e.hace/6).toFixed(1)}%"></i></div>`).join(''):'<p class="peq">Ningún equipo en los últimos 10 minutos.</p>');
 const r=flotEl.getBoundingClientRect(),w=flot.offsetWidth;
 flot.style.left=Math.max(8,Math.min(innerWidth-w-8,r.left))+'px';flot.style.top=(r.bottom+8)+'px'}

/* ---------- Interfaz de cada vista ---------- */
const UI={pinta(){},ctx(){},tic(){},voto(){}};
const raiz=document.getElementById('ui');
const nodo=h=>{const t=document.createElement('template');t.innerHTML=h.trim();return t.content.firstElementChild};
if(VISTA==='presentacion')UI.pinta=pintaNotas;
if(VISTA==='publico'){
 raiz.append(nodo('<div id="voto" aria-live="polite"></div>'));const V=$('#voto');
 UI.voto=()=>{const on=enQuiz()&&red&&!!quiz;V.classList.toggle('on',on);if(!on)return;V.innerHTML=htmlVoto();
  V.querySelectorAll('.ops button').forEach(b=>b.addEventListener('click',()=>vota(+b.dataset.k)))};
 UI.pinta=()=>UI.voto()}
if(VISTA==='pc'){
 let prefs=Object.assign({tam:26,lectura:false,auto:false,ajustar:true},leeJSON('reto1_pc',{}));
 raiz.append(nodo(`<div id="barra"><button onclick="ir(i-1)">← <span class="largo">Anterior</span></button><span id="posicion"></span><span id="sincro"></span>
  <button id="b_crono" onclick="cronoAlterna()"></button><button onclick="cronoReinicia()" title="Cronómetro a cero">↺</button>
  <button id="b_mov" onclick="alterna()"></button><button onclick="ir(i+1)"><span class="largo">Siguiente</span> →</button></div>`),
  nodo('<div id="lateral"><div id="siguiente"></div><section class="ctx"></section></div>'),
  nodo(`<div id="herr"><button data-h="menos" title="Letra más pequeña">A−</button><button data-h="mas" title="Letra más grande">A+</button><button data-h="ajustar" title="La letra crece hasta que el guion llena la caja">⤢ Ajustar a la caja</button>
  <button data-h="lectura">Modo lectura</button><button data-h="auto" title="El texto avanza solo con el cronómetro">Desplazamiento automático</button><button data-h="editar">✎ Editar</button></div>`));
 // Mayor tamaño de letra con el que el guion cabe entero en la caja (búsqueda binaria, de 14 a 64 px).
 const ajusta=()=>{if(!prefs.ajustar||editando!==null)return;let lo=14,hi=64;notas.style.fontSize=hi+'px';
  if(notas.scrollHeight<=notas.clientHeight)return;
  for(let k=0;k<12;k++){const m=(lo+hi)/2;notas.style.fontSize=m+'px';if(notas.scrollHeight<=notas.clientHeight)lo=m;else hi=m}
  notas.style.fontSize=Math.floor(lo)+'px'};
 addEventListener('resize',()=>requestAnimationFrame(ajusta));
 const H=$('#herr'),aplicaPrefs=()=>{if(prefs.ajustar)ajusta();else notas.style.fontSize=prefs.tam+'px';document.body.classList.toggle('lectura',prefs.lectura);
  H.querySelector('[data-h=ajustar]').classList.toggle('on',prefs.ajustar);
  H.querySelector('[data-h=lectura]').classList.toggle('on',prefs.lectura);H.querySelector('[data-h=auto]').classList.toggle('on',prefs.auto);guarda('reto1_pc',prefs)};
 H.addEventListener('click',ev=>{const h=ev.target.dataset&&ev.target.dataset.h;if(!h)return;
  if(h==='menos'||h==='mas'){if(prefs.ajustar)prefs.tam=Math.round(parseFloat(notas.style.fontSize)||prefs.tam);prefs.ajustar=false;
   prefs.tam=h==='menos'?Math.max(14,prefs.tam-2):Math.min(64,prefs.tam+2)}
  else if(h==='ajustar')prefs.ajustar=!prefs.ajustar;
  else if(h==='lectura')prefs.lectura=!prefs.lectura;else if(h==='auto')prefs.auto=!prefs.auto;else if(h==='editar')return abreEditor();aplicaPrefs()});
 aplicaPrefs();
 function abreEditor(){if(editando!==null)return;editando=i;const s=sl[i];
  const cab=document.createElement('span'),t=document.createElement('textarea'),lbl=document.createElement('label'),r=document.createElement('textarea'),bar=document.createElement('div');
  cab.className='cab';cab.textContent=`Editando la diapositiva ${i+1}: ${s.dataset.titulo}`;t.className='ed-texto';t.value=s.dataset.notas;t.setAttribute('aria-label','Guion');
  lbl.className='ed-lbl';lbl.textContent='Notas rápidas para el móvil (una por línea)';r.className='ed-rapidas';r.value=rapidas(s).join('\n');r.setAttribute('aria-label','Notas rápidas');
  bar.className='ed-bar';bar.innerHTML='<button class="prim" data-a="guardar">Guardar para todos</button><button data-a="cancelar">Cancelar</button><button data-a="original">Volver al original</button><span class="ed-msg"></span>';
  notas.replaceChildren(cab,t,lbl,r,bar);t.focus();
  bar.addEventListener('click',ev=>{const a=ev.target.dataset&&ev.target.dataset.a;if(!a)return;
   if(a==='cancelar'){editando=null;return UI.pinta()}
   const datos=a==='original'?{n:editando+1,borrar:true}:{n:editando+1,texto:t.value,rapidas:r.value.split('\n').map(x=>x.trim()).filter(Boolean)};
   const cierra=()=>{editando=null;UI.pinta()};
   if(!red){aplicaGuion(datos);return cierra()}
   manda('guion',datos).then(res=>{if(res&&res.ok)cierra();else bar.querySelector('.ed-msg').textContent='No se ha podido guardar.'})})}
 UI.pinta=()=>{const s=sl[i],sig=sl[i+1];pintaNotas();requestAnimationFrame(ajusta);
  if(editando!==null&&editando!==i)notas.querySelector('.cab').textContent=`Editando la diapositiva ${editando+1} · la presentación va por la ${i+1}`;
  $('#posicion').textContent=`${i+1} / ${sl.length} · ${s.dataset.titulo}`;
  $('#siguiente').innerHTML=sig&&!opcional(i+1)?`Siguiente: <b>${sig.dataset.titulo}</b>`:sig?'Última diapositiva · las preguntas al público son opcionales':'Última diapositiva';UI.ctx()};
 UI.ctx=()=>{$('#lateral .ctx').innerHTML=htmlCtx();$('#b_mov').textContent=quieto?'✦ Animaciones: no':'✦ Animaciones: sí';$('#b_crono').textContent=textoCrono()};
 UI.tic=(t,ini,fin)=>{$('#b_crono').textContent=textoCrono();
  if(prefs.auto&&crono.corre&&editando===null){const max=notas.scrollHeight-notas.clientHeight;
   if(max>0)notas.scrollTo({top:Math.max(0,Math.min(1,(t-ini)/(fin-ini)))*max,behavior:quieto?'auto':'smooth'})}};
 reloj.classList.add('on')}
if(VISTA==='mando'){
 raiz.append(nodo(`<div id="movil"><header><span id="sincro"></span><span class="reloj-m"></span></header>
  <div class="pos"><b></b><span></span></div><ul class="rapidas"></ul><div class="completo"></div>
  <button class="ver-completo" onclick="$('#movil').classList.toggle('completo-on');UI.pinta()"></button>
  <section class="ctx"></section>
  <section class="ctrl"><button id="m_crono" onclick="cronoAlterna()"></button><button onclick="cronoReinicia()">↺ Crono a 0</button><button id="m_mov" onclick="alterna()"></button></section>
  <footer><button onclick="ir(i-1)">← Anterior</button><button onclick="ir(i+1)">Siguiente →</button></footer></div>`));
 const M=$('#movil');
 UI.pinta=()=>{const s=sl[i],rs=rapidas(s);M.querySelector('.pos b').textContent=`${i+1} / ${sl.length}`;M.querySelector('.pos span').textContent=s.dataset.titulo;
  M.querySelector('.rapidas').replaceChildren(...(rs.length?rs:['(sin notas rápidas: abre el guion completo)']).map(x=>{const li=document.createElement('li');conTachado(li,x);return li}));
  conTachado(M.querySelector('.completo'),s.dataset.notas);
  M.querySelector('.ver-completo').textContent=M.classList.contains('completo-on')?'Ver las notas rápidas':'Ver el guion completo';UI.ctx()};
 UI.ctx=()=>{M.querySelector('.ctx').innerHTML=htmlCtx();$('#m_mov').textContent=quieto?'✦ Animar: no':'✦ Animar: sí';$('#m_crono').textContent=textoCrono()};
 UI.tic=(t,ini,fin,hora,html,est)=>{const r=M.querySelector('.reloj-m');r.innerHTML=html;r.dataset.estado=est;$('#m_crono').textContent=textoCrono()}}

/* ---------- Arranque ---------- */
addEventListener('resize',fit);fit();
ver(red?0:(parseInt(location.hash.slice(1))||1)-1);
if(red){fetch('guion').then(r=>r.ok?r.json():{}).then(g=>Object.entries(g).forEach(([n,d])=>aplicaGuion({n:+n,...d}))).catch(()=>{});
 if(CONTROL)compruebaToken();else conecta()}
else estadoRed(null,'abierta sin servidor: modo local');
if(SO_QUIETO&&!eleccion&&VISTA==='presentacion')aviso('Tu sistema tiene las animaciones desactivadas. Pulsa M para activar el movimiento.',9000);
