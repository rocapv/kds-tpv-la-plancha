-- Puestos: el plano de la cantina y quién está en cada sitio.
--
-- La idea es la del turno escrito en la pizarra: el encargado arrastra la ficha de cada
-- empleado al puesto donde va a trabajar, y ese puesto decide a qué pantalla entra y qué
-- puede hacer. El rol sigue existiendo, pero para lo operativo manda el puesto:
--   · un camarero puesto en la placa térmica trabaja en el KDS de plancha;
--   · un encargado puesto en el comedor cobra como cualquier camarero.
-- Lo administrativo (carta, usuarios, ajustes, informes, arqueo) sigue pidiendo rol
-- encargado de verdad, para que nadie se quede fuera de la gestión por moverse de sitio.
--
-- Idempotente: se puede pasar sobre una base de datos en uso.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS puestos (
  clave         VARCHAR(20) PRIMARY KEY,
  nombre        VARCHAR(40) NOT NULL,
  gui           VARCHAR(80) NULL,                                  -- pantalla de entrada; NULL = ninguna
  rol_operativo ENUM('camarero','cocina') NULL,                    -- NULL = fuera de servicio
  x             TINYINT UNSIGNED NOT NULL DEFAULT 0,               -- caja del plano, en % del ancho
  y             TINYINT UNSIGNED NOT NULL DEFAULT 0,
  ancho         TINYINT UNSIGNED NOT NULL DEFAULT 20,
  alto          TINYINT UNSIGNED NOT NULL DEFAULT 20,
  color         CHAR(7)     NOT NULL DEFAULT '#3a3f49',
  orden         TINYINT UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB;

-- Dónde está cada empleado y en qué punto exacto del plano quedó su ficha.
ALTER TABLE empleados
  ADD COLUMN IF NOT EXISTS puesto VARCHAR(20)     NULL AFTER rol,
  ADD COLUMN IF NOT EXISTS mapa_x TINYINT UNSIGNED NULL AFTER puesto,
  ADD COLUMN IF NOT EXISTS mapa_y TINYINT UNSIGNED NULL AFTER mapa_x;

-- Sala a la izquierda, cocina a la derecha, y abajo la franja de quien no está en servicio.
INSERT INTO puestos (clave, nombre, gui, rol_operativo, x, y, ancho, alto, color, orden) VALUES
 ('comedor',  'Comedor presurizado',    'tpv.html',                 'camarero',  2,  8, 30, 34, '#2471a3', 1),
 ('mirador',  'Mirador de la fractura', 'tpv.html',                 'camarero',  2, 46, 30, 22, '#1f618d', 2),
 ('atraque',  'Atraque',                'tpv.html',                 'camarero', 34,  8, 14, 22, '#5499c7', 3),
 ('caja',     'Caja',                   'facturas.html',            'camarero', 34, 34, 14, 20, '#117864', 4),
 ('plancha',  'Placa térmica',          'kds.html?estacion=plancha','cocina',   52,  8, 22, 20, '#c0392b', 5),
 ('freidora', 'Fritura',                'kds.html?estacion=freidora','cocina',  76,  8, 22, 20, '#d68910', 6),
 ('frios',    'Cámara fría',            'kds.html?estacion=frios',  'cocina',   52, 30, 22, 20, '#8e44ad', 7),
 ('barra',    'Barra de oxígeno',       'kds.html?estacion=barra',  'cocina',   76, 30, 22, 20, '#229954', 8),
 ('pase',     'Pase',                   'kds.html',                 'cocina',   52, 52, 22, 16, '#7d6608', 9),
 ('recogida', 'Recogida',               'recogida.html',            'cocina',   76, 52, 22, 16, '#b9770e', 10),
 ('oficina',  'Oficina',                'index.html',                NULL,       2, 72, 22, 20, '#566573', 11),
 ('descanso', 'Fuera de servicio',       NULL,                       NULL,      26, 72, 72, 20, '#2b2f36', 12)
ON DUPLICATE KEY UPDATE
  nombre=VALUES(nombre), gui=VALUES(gui), rol_operativo=VALUES(rol_operativo),
  x=VALUES(x), y=VALUES(y), ancho=VALUES(ancho), alto=VALUES(alto),
  color=VALUES(color), orden=VALUES(orden);
