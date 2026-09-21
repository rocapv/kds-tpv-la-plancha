-- Decorado: la hamburguesería pasa a ser la cantina de una estación minera
-- excavada dentro de un asteroide. Solo cambia la «piel»: nombres del local,
-- de las mesas y de la carta. La estructura, los roles, los ENUM de estación
-- (plancha/freidora/frios/barra) y la facturación siguen igual.
--
-- Es idempotente y se puede pasar sobre una base de datos en uso: actualiza por
-- id, así que ningún pedido antiguo pierde la referencia a su producto.
SET NAMES utf8mb4;

-- ── El local ────────────────────────────────────────────────────────────────
INSERT INTO ajustes (clave, valor) VALUES
 ('local_nombre',    'Cantina Vesta-9'),
 ('local_direccion', 'Galería Central, nivel -3 · Estación Vesta-9 · Cinturón Principal')
ON DUPLICATE KEY UPDATE valor = VALUES(valor);

-- ── Las mesas ───────────────────────────────────────────────────────────────
-- zona sigue siendo el ENUM sala/terraza/barra; el rótulo que ve el camarero
-- lo pone el front (comedor presurizado / mirador de la fractura / atraque).
UPDATE mesas SET nombre='C1' WHERE id=1;   UPDATE mesas SET nombre='C2' WHERE id=2;
UPDATE mesas SET nombre='C3' WHERE id=3;   UPDATE mesas SET nombre='C4' WHERE id=4;
UPDATE mesas SET nombre='C5' WHERE id=5;   UPDATE mesas SET nombre='C6' WHERE id=6;
UPDATE mesas SET nombre='M1' WHERE id=7;   UPDATE mesas SET nombre='M2' WHERE id=8;
UPDATE mesas SET nombre='M3' WHERE id=9;   UPDATE mesas SET nombre='M4' WHERE id=10;
UPDATE mesas SET nombre='A1' WHERE id=11;  UPDATE mesas SET nombre='A2' WHERE id=12;
UPDATE mesas SET nombre='A3' WHERE id=13;

-- ── Las categorías ──────────────────────────────────────────────────────────
INSERT INTO categorias (id, nombre, orden, color) VALUES
 (1,'Placas calientes',   1,'#c0392b'),
 (2,'Fritura sin gravedad',2,'#d68910'),
 (3,'Hidroponía',         3,'#229954'),
 (4,'Barra de oxígeno',   4,'#2471a3'),
 (5,'Cámara fría',        5,'#8e44ad')
ON DUPLICATE KEY UPDATE nombre=VALUES(nombre), orden=VALUES(orden), color=VALUES(color);

-- ── La carta ────────────────────────────────────────────────────────────────
-- Los alérgenos son los de siempre (son obligatorios por normativa y no se
-- decoran): pan de trigo = gluten, queso = lácteos, salsas = huevo/mostaza.
UPDATE productos SET nombre='Roca Madre',              alergenos='Gluten, sésamo'                    WHERE id=1;
UPDATE productos SET nombre='Fundido de Ceres',        alergenos='Gluten, lácteos, sésamo'           WHERE id=2;
UPDATE productos SET nombre='Brasa de Perihelio',      alergenos='Gluten, lácteos, mostaza, sésamo'  WHERE id=3;
UPDATE productos SET nombre='Doble Impacto',           alergenos='Gluten, lácteos, huevo, sésamo'    WHERE id=4;
UPDATE productos SET nombre='Ave de corral orbital',   alergenos='Gluten, huevo, mostaza'            WHERE id=5;
UPDATE productos SET nombre='Cultivo del nivel 4',     alergenos='Gluten, soja, sésamo'              WHERE id=6;
UPDATE productos SET nombre='Regolito frito',          alergenos=NULL                                WHERE id=7;
UPDATE productos SET nombre='Regolito especiado',      alergenos='Mostaza'                           WHERE id=8;
UPDATE productos SET nombre='Anillos de Saturno',      alergenos='Gluten, huevo'                     WHERE id=9;
UPDATE productos SET nombre='Meteoritos de pollo (8)', alergenos='Gluten, huevo'                     WHERE id=10;
UPDATE productos SET nombre='Fragmentos con queso',    alergenos='Lácteos'                           WHERE id=11;
UPDATE productos SET nombre='César del invernadero',   alergenos='Gluten, lácteos, huevo, pescado'   WHERE id=12;
UPDATE productos SET nombre='Caprese hidropónica',     alergenos='Lácteos'                           WHERE id=13;
UPDATE productos SET nombre='Agua de deshielo',        alergenos=NULL                                WHERE id=14;
UPDATE productos SET nombre='Refresco presurizado',    alergenos=NULL                                WHERE id=15;
UPDATE productos SET nombre='Caña de la estación',     alergenos='Gluten'                            WHERE id=16;
UPDATE productos SET nombre='Rubia de gravedad baja',  alergenos='Gluten'                            WHERE id=17;
UPDATE productos SET nombre='Batido de nebulosa',      alergenos='Lácteos'                           WHERE id=18;
UPDATE productos SET nombre='Brownie de carbón',       alergenos='Gluten, lácteos, huevo, frutos secos' WHERE id=19;
UPDATE productos SET nombre='Tarta de cráter',         alergenos='Gluten, lácteos, huevo'            WHERE id=20;
UPDATE productos SET nombre='Helado de cara oculta',   alergenos='Lácteos'                           WHERE id=21;

-- ── Añadidos desde la aplicación de carta ───────────────────────────────────
-- En la estación se come por turnos, no «del día»: la categoría y el menú
-- combinado se renombran por nombre, porque se crearon a mano y su id cambia
-- de una instalación a otra.
UPDATE categorias SET nombre='Raciones de turno' WHERE nombre='Menús';
UPDATE productos  SET nombre='Ración de turno', alergenos='Gluten, lácteos'
 WHERE nombre IN ('Menú del día', 'Menu del dia');
