# Presentación del proyecto

`kds_presentacion.html` — **un solo fichero**, sin dependencias y sin salida a internet. Se abre
con doble clic en cualquier ordenador (también sin wifi) y se puede llevar en un pendrive.

| Tecla | Qué hace |
|---|---|
| `→` `espacio` `AvPág` | siguiente |
| `←` `RePág` | anterior |
| `Inicio` · `Fin` | primera · última |
| `O` | vista general de las 20 diapositivas |
| `F` | pantalla completa |
| `P` | cronómetro de quien presenta |

También se pasa con el ratón (mitad derecha avanza, izquierda retrocede) y con el dedo
(deslizando). La dirección lleva el número: `…kds_presentacion.html#9` abre la diapositiva 9.

## PDF para entregar

`Ctrl+P` → *Guardar como PDF*, **horizontal**, con «Gráficos de fondo» activado: sale una
diapositiva por hoja. El PDF ya generado está al lado (`kds_presentacion.pdf`, 20 páginas).

## Por qué se ve como el sistema

Usa los mismos colores y la misma tipografía que el TPV y el KDS (`frontend/css/estilo.css`), a
propósito: al pasar de la presentación a la demostración en vivo no parece que se cambie de
proyecto. Si se cambia la paleta del sistema, conviene cambiarla también aquí (bloque `:root`).
