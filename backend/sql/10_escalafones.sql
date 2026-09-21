-- Escalafón: la posición de cada persona EN LA EMPRESA, que no es lo mismo que su puesto
-- de cocina (ese lo decide el plano, 08_puestos.sql) ni el rol operativo del turno.
--
--   base_junior → primer año
--   base        → mismo trabajo, 5 % más de sueldo que el junior
--   encargado   → manager: abre la gestión (carta, usuarios, ajustes, informes, arqueo)
--   gerente     → el encargado que manda; puede tocar escalafones
--   admin       → por encima del gerente: administra el sistema y crea gerentes
--
-- Se añade además lo que faltaba en la ficha del empleado: apellidos, contraseña (para la
-- gestión; el PIN sigue siendo la llave de las pantallas de servicio) y fecha de alta, que es
-- la que dice si alguien sigue siendo junior.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS escalafones (
  clave       VARCHAR(20) PRIMARY KEY,
  nombre      VARCHAR(40)      NOT NULL,
  nivel       TINYINT UNSIGNED NOT NULL,              -- a mayor nivel, más mando
  plus_pct    DECIMAL(4,1)     NOT NULL DEFAULT 0,    -- sobre el sueldo del junior
  gestion     BOOLEAN          NOT NULL DEFAULT FALSE,-- ¿entra en carta/usuarios/ajustes/informes?
  descripcion VARCHAR(160)     NOT NULL DEFAULT ''
) ENGINE=InnoDB;

INSERT INTO escalafones (clave, nombre, nivel, plus_pct, gestion, descripcion) VALUES
 ('base_junior', 'Empleado base junior', 1, 0.0, FALSE, 'Primer año en la empresa.'),
 ('base',        'Empleado base',        2, 5.0, FALSE, 'Mismo trabajo que el junior, 5 % más de sueldo.'),
 ('encargado',   'Encargado',            3, 25.0, TRUE, 'Manager de turno: gestiona carta, usuarios, ajustes e informes.'),
 ('gerente',     'Gerente',              4, 45.0, TRUE, 'El encargado que manda; toca escalafones y sueldos.'),
 ('admin',       'Administrador',        5, 60.0, TRUE, 'Administra el sistema y crea gerentes.')
ON DUPLICATE KEY UPDATE nombre=VALUES(nombre), nivel=VALUES(nivel), plus_pct=VALUES(plus_pct),
  gestion=VALUES(gestion), descripcion=VALUES(descripcion);

ALTER TABLE empleados
  ADD COLUMN IF NOT EXISTS apellidos   VARCHAR(80)  NULL AFTER nombre,
  ADD COLUMN IF NOT EXISTS escalafon   VARCHAR(20)  NOT NULL DEFAULT 'base' AFTER rol,
  ADD COLUMN IF NOT EXISTS contrasena  VARCHAR(160) NULL,          -- pbkdf2, nunca en claro
  ADD COLUMN IF NOT EXISTS alta_en     DATE         NULL;

-- Arranque razonable para los que ya estaban: los encargados de antes son encargados de escalafón.
UPDATE empleados SET escalafon = 'encargado' WHERE rol = 'encargado' AND escalafon = 'base';
UPDATE empleados SET alta_en = CURDATE() WHERE alta_en IS NULL;

-- El encargado más antiguo pasa a gerente (si no hay ninguno ya).
UPDATE empleados SET escalafon = 'gerente'
 WHERE id = (SELECT * FROM (SELECT MIN(id) FROM empleados WHERE escalafon = 'encargado' AND activo) x)
   AND NOT EXISTS (SELECT * FROM (SELECT 1 FROM empleados WHERE escalafon IN ('gerente','admin')) y);

-- Y un administrador del sistema, que arriba del todo tiene que haber alguien.
INSERT INTO empleados (nombre, apellidos, rol, escalafon, pin, activo, alta_en)
SELECT 'Root', 'Administración', 'encargado', 'admin', '0000', TRUE, CURDATE()
 WHERE NOT EXISTS (SELECT * FROM (SELECT 1 FROM empleados WHERE escalafon = 'admin') z)
   AND NOT EXISTS (SELECT * FROM (SELECT 1 FROM empleados WHERE pin = '0000') w);
