-- Plano del local en 2D, visto desde arriba y editable.
--
-- Hasta ahora el «mapa» era una rejilla de cajas de trabajo. Esto es el plano de verdad:
-- muros, puertas, zonas (comedor, mirador, atraque, cocina), mesas y equipos de cocina, cada
-- cosa con su sitio. Sirve para dos cosas a la vez:
--   · el encargado coloca las mesas como están de verdad y las enlaza con la tabla `mesas`,
--     así el TPV enseña la sala tal cual es;
--   · las fichas de personal del plano de puestos se pintan encima, sobre el local real.
--
-- Coordenadas en MILÉSIMAS del ancho/alto del plano (0..1000): enteros, sin comas flotantes,
-- y el plano se puede pintar a cualquier tamaño sin perder precisión.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS plano_elementos (
  id      INT AUTO_INCREMENT PRIMARY KEY,
  tipo    ENUM('muro','zona','mesa','equipo','puerta','barra') NOT NULL,
  nombre  VARCHAR(40)  NOT NULL DEFAULT '',
  mesa_id INT          NULL,               -- si es una mesa, la fila de `mesas` que representa
  puesto  VARCHAR(20)  NULL,               -- si es zona o equipo, el puesto de trabajo asociado
  x       SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  y       SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  ancho   SMALLINT UNSIGNED NOT NULL DEFAULT 60,
  alto    SMALLINT UNSIGNED NOT NULL DEFAULT 60,
  forma   ENUM('rect','circ') NOT NULL DEFAULT 'rect',
  icono   VARCHAR(8)   NOT NULL DEFAULT '',
  color   CHAR(7)      NOT NULL DEFAULT '#3a3f49',
  z       TINYINT UNSIGNED NOT NULL DEFAULT 1,
  KEY idx_tipo (tipo),
  FOREIGN KEY (mesa_id) REFERENCES mesas(id) ON DELETE SET NULL
) ENGINE=InnoDB;
