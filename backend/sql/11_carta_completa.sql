-- La ficha de producto completa: alérgenos de verdad, inventario y foto.
--
-- Tres cosas que faltaban:
--   1) Los alérgenos eran un campo de texto libre. Pasan a ser un catálogo (los 14 de
--      declaración obligatoria del Reglamento UE 1169/2011) con su PROTOCOLO: qué hacer en
--      sala si alguien reacciona. El texto libre se conserva para no romper el KDS, pero se
--      genera a partir del catálogo.
--   2) Cada producto de la carta apunta a un artículo de INVENTARIO (lo que se compra), que
--      es lo que permite escandallo y stock. La carta busca por nombre desde tres letras.
--   3) Foto: ruta o URL. El sistema sabe dibujar una si no hay ninguna.
--
-- Idempotente.
SET NAMES utf8mb4;

-- ── Catálogo de alérgenos ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alergenos (
  clave     VARCHAR(20) PRIMARY KEY,
  nombre    VARCHAR(40)  NOT NULL,
  icono     VARCHAR(8)   NOT NULL DEFAULT '⚠',
  gravedad  ENUM('leve','grave','muy_grave') NOT NULL DEFAULT 'grave',
  presente_en VARCHAR(200) NOT NULL DEFAULT '',
  protocolo TEXT         NOT NULL,
  orden     TINYINT UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB;

INSERT INTO alergenos (clave, nombre, icono, gravedad, presente_en, protocolo, orden) VALUES
 ('gluten', 'Cereales con gluten', '🌾', 'grave',
  'Trigo, centeno, cebada, avena, espelta, kamut y todo lo rebozado o empanado.',
  'Retirar el plato y no servir nada más de la misma tabla o freidora. Si hay dolor abdominal intenso, vómitos o diarrea que no cede, avisar al 112. Anotar el plato exacto y guardar una muestra.', 1),
 ('crustaceos', 'Crustáceos', '🦐', 'muy_grave',
  'Gamba, langostino, cangrejo, cigala, langosta; caldos y salsas hechos con sus cabezas.',
  'Reacción frecuente y rápida: vigilar hinchazón de labios o lengua y dificultad para respirar. Si aparece cualquiera de las dos, es anafilaxia: llamar al 112, tumbar con las piernas en alto y ayudar con el autoinyector de adrenalina si el cliente lo lleva.', 2),
 ('huevos', 'Huevos', '🥚', 'grave',
  'Mayonesas, salsas, rebozados, masas, merengues y pastas al huevo.',
  'Retirar el plato. Vigilar ronchas, picor de garganta y vómitos. Si cuesta respirar o hay mareo, 112 y adrenalina si la lleva.', 3),
 ('pescado', 'Pescado', '🐟', 'grave',
  'Pescado, caldos, salsas, gelatinas y algunos aliños (anchoa en la salsa césar).',
  'Retirar el plato y separar los cubiertos. Si hay hinchazón, ahogo o mareo, 112 y adrenalina si la lleva.', 4),
 ('cacahuetes', 'Cacahuetes', '🥜', 'muy_grave',
  'Cacahuete, su aceite, salsas satay y muchos postres industriales.',
  'Es el alérgeno que más anafilaxias graves provoca: al mínimo síntoma (picor de garganta, ronchas, tos seca), llamar al 112 SIN esperar a ver si mejora, usar el autoinyector si el cliente lo lleva y no dejarle solo ni levantarle de golpe.', 5),
 ('soja', 'Soja', '🌱', 'grave',
  'Salsa de soja, tofu, lecitina de soja, panes y salsas industriales.',
  'Retirar el plato. Vigilar ronchas y molestias digestivas; si hay ahogo o hinchazón, 112.', 6),
 ('lacteos', 'Leche y lácteos', '🥛', 'grave',
  'Leche, nata, mantequilla, queso, suero; también muchos panes y purés.',
  'Distinguir intolerancia (digestivo, sin urgencia vital) de alergia a la proteína (ronchas, ahogo). En el segundo caso, 112 y adrenalina si la lleva.', 7),
 ('frutos_cascara', 'Frutos de cáscara', '🌰', 'muy_grave',
  'Almendra, avellana, nuez, anacardo, pistacho, macadamia; turrones, salsas y aceites.',
  'Como el cacahuete: síntomas rápidos y graves. 112 al primer signo respiratorio, adrenalina si la lleva y vigilar aunque parezca mejorar, porque puede haber una segunda reacción horas después.', 8),
 ('apio', 'Apio', '🥬', 'grave',
  'Apio en rama, apionabo, sal de apio, caldos y sofritos.',
  'Retirar el plato. Vigilar hinchazón de boca; si hay ahogo, 112.', 9),
 ('mostaza', 'Mostaza', '🌭', 'grave',
  'Mostaza, salsas, adobos, currys y muchos encurtidos.',
  'Retirar el plato y revisar las salsas servidas aparte. Si hay hinchazón o ahogo, 112.', 10),
 ('sesamo', 'Granos de sésamo', '🫓', 'muy_grave',
  'Pan de hamburguesa, panes de semillas, humus, tahini y aceites.',
  'Muy presente en panes: retirar TODO el pan de la mesa, no solo el plato. Al primer signo respiratorio, 112 y adrenalina si la lleva.', 11),
 ('sulfitos', 'Sulfitos (SO2)', '🍷', 'grave',
  'Vino, cerveza, zumos, frutos secos, patatas procesadas y conservas.',
  'Cuidado con los asmáticos: el sulfito les provoca broncoespasmo. Si aparece pitido al respirar, ayudar con su inhalador, sentarle inclinado hacia delante y llamar al 112 si no cede en minutos.', 12),
 ('altramuces', 'Altramuces', '🫘', 'grave',
  'Harina de altramuz en panes y masas sin gluten, y en aperitivos.',
  'Retirar el plato. Frecuente reacción cruzada con el cacahuete: si el cliente es alérgico a este, tratarlo con la misma urgencia.', 13),
 ('moluscos', 'Moluscos', '🦑', 'muy_grave',
  'Mejillón, almeja, calamar, pulpo, berberecho; caldos y salsas.',
  'Como los crustáceos: vigilar hinchazón y ahogo. 112 y adrenalina si la lleva.', 14)
ON DUPLICATE KEY UPDATE nombre=VALUES(nombre), icono=VALUES(icono), gravedad=VALUES(gravedad),
  presente_en=VALUES(presente_en), protocolo=VALUES(protocolo), orden=VALUES(orden);

-- El protocolo general no cabe en el VARCHAR corto de ajustes: se le da sitio.
ALTER TABLE ajustes MODIFY valor VARCHAR(600) NOT NULL;

-- Qué hacer SIEMPRE, sea cual sea el alérgeno. Se muestra arriba del protocolo concreto.
INSERT INTO ajustes (clave, valor) VALUES
 ('protocolo_general',
  'PARA TODOS LOS CASOS: 1) Retirar el plato y avisar de inmediato al encargado de turno. '
  '2) Preguntar al cliente si es alérgico conocido y si lleva autoinyector de adrenalina; si lo '
  'lleva, ayudarle a usarlo cuanto antes: la adrenalina no espera. 3) Llamar al 112 ante cualquier '
  'dificultad para respirar, hinchazón de labios, lengua o garganta, mareo o desmayo. '
  '4) No dejar sola a la persona y no ponerla de pie de golpe. 5) Guardar el plato y su ficha: '
  'sanidad los va a pedir. 6) Anotar la hora de los primeros síntomas.')
ON DUPLICATE KEY UPDATE valor=VALUES(valor);

CREATE TABLE IF NOT EXISTS producto_alergenos (
  producto_id INT         NOT NULL,
  alergeno    VARCHAR(20) NOT NULL,
  PRIMARY KEY (producto_id, alergeno),
  FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
  FOREIGN KEY (alergeno) REFERENCES alergenos(clave) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ── Inventario ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inventario (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  sku        VARCHAR(20)  NOT NULL UNIQUE,
  nombre     VARCHAR(80)  NOT NULL,
  unidad     VARCHAR(12)  NOT NULL DEFAULT 'ud',
  stock      DECIMAL(10,2) NOT NULL DEFAULT 0,
  coste_cent INT          NOT NULL DEFAULT 0,
  proveedor  VARCHAR(60)  NULL,
  activo     BOOLEAN      NOT NULL DEFAULT TRUE,
  KEY idx_nombre (nombre)
) ENGINE=InnoDB;

ALTER TABLE productos
  ADD COLUMN IF NOT EXISTS inventario_id INT NULL AFTER estacion,
  ADD COLUMN IF NOT EXISTS foto VARCHAR(200) NULL;

INSERT INTO inventario (sku, nombre, unidad, stock, coste_cent, proveedor) VALUES
 ('MAT-0001','Proteína cultivada en bloque','kg', 48.00, 1450,'Hidrocultivos Vesta'),
 ('MAT-0002','Pan de semillas de sésamo','ud', 320.00,  35,'Panificadora Ceres'),
 ('MAT-0003','Queso fundido de cabra lunar','kg', 12.50, 2100,'Granja Selene'),
 ('MAT-0004','Tubérculo de invernadero','kg', 90.00,  480,'Hidrocultivos Vesta'),
 ('MAT-0005','Aceite de fritura reciclable','l',  60.00,  390,'Refinería del Cinturón'),
 ('MAT-0006','Hoja verde hidropónica','kg',  18.00, 1250,'Hidrocultivos Vesta'),
 ('MAT-0007','Salsa de soja fermentada','l',  24.00,  810,'Comercial Tycho'),
 ('MAT-0008','Concentrado de tomate','kg', 30.00,  520,'Comercial Tycho'),
 ('MAT-0009','Agua carbonatada reciclada','l', 500.00,  22,'Planta de ciclo cerrado'),
 ('MAT-0010','Sirope de algas dulces','l',  15.00, 1150,'Granja Selene'),
 ('MAT-0011','Crustáceo criado en tanque','kg',  9.00, 3900,'Acuicultura Pallas'),
 ('MAT-0012','Harina sin gluten de altramuz','kg', 22.00,  940,'Panificadora Ceres'),
 ('MAT-0013','Huevo deshidratado','kg',  14.00, 1680,'Granja Selene'),
 ('MAT-0014','Frutos de cáscara variados','kg',  7.50, 2750,'Comercial Tycho'),
 ('MAT-0015','Cerveza de ciclo corto','l',  80.00,  260,'Destilería Vesta-9')
ON DUPLICATE KEY UPDATE nombre=VALUES(nombre), unidad=VALUES(unidad),
  coste_cent=VALUES(coste_cent), proveedor=VALUES(proveedor);
