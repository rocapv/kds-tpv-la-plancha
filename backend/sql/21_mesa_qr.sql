-- El QR que cambia, y la visita que abre (bloque 1 de PROPUESTA_APP_CLIENTE.md).
--
-- Cada mesa lleva una pantalla pequeña tras un cristal que enseña un QR distinto cada pocos
-- segundos. En cuanto alguien lo lee, ese código **se quema** y se abre una VISITA: el grupo que
-- está sentado en esa mesa. A partir de ahí la pantalla deja de rotar y enseña un código fijo de
-- «únete a la mesa», para que los que llegan tarde entren sin volver a jugar a la lotería.
--
-- Por qué rotar: una pegatina con el QR de la mesa 7 es un cartel permanente. Quien la fotografía
-- una vez puede pedir «desde la mesa 7» meses después y desde la calle. Con un código de un solo
-- uso y caducidad corta, para pedir hay que estar delante del cristal.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS mesa_pantallas (
  id        INT AUTO_INCREMENT PRIMARY KEY,
  mesa_id   INT          NOT NULL,
  nombre    VARCHAR(40)  NULL,           -- «la del rincón», para cuando haya que ir a mirarla
  secreto   CHAR(64)     NOT NULL,       -- con esto pide códigos, y con nada más
  visto_en  DATETIME     NULL,           -- último latido; sin latido en dos minutos, está muerta
  firmware  VARCHAR(20)  NULL,
  activa    BOOLEAN      NOT NULL DEFAULT TRUE,
  UNIQUE KEY uq_secreto (secreto),
  KEY ix_mesa (mesa_id),
  FOREIGN KEY (mesa_id) REFERENCES mesas(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- La visita: el grupo sentado. No es el pedido, aunque acabe teniendo uno: un grupo puede estar
-- un rato sin pedir nada, y puede pedir en dos tandas. El pedido se crea con la primera comanda.
CREATE TABLE IF NOT EXISTS visitas (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  mesa_id       INT       NOT NULL,
  pedido_id     INT       NULL,
  estado        ENUM('activa','cerrada') NOT NULL DEFAULT 'activa',
  codigo_union  CHAR(8)   NOT NULL,      -- el QR fijo mientras dura la visita
  abierta_en    DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  cerrada_en    DATETIME  NULL,
  reserva_id    INT       NULL,          -- si el grupo venía con reserva
  UNIQUE KEY uq_union (codigo_union),
  KEY ix_mesa_estado (mesa_id, estado),
  FOREIGN KEY (mesa_id)    REFERENCES mesas(id),
  FOREIGN KEY (pedido_id)  REFERENCES pedidos(id),
  FOREIGN KEY (reserva_id) REFERENCES reservas(id)
) ENGINE=InnoDB;

-- Los códigos que va escupiendo la pantalla. Se guardan todos, también los que nadie llegó a
-- leer: así se puede mirar si una pantalla está emitiendo y nadie la usa (¿se ve mal? ¿hay
-- reflejo?), que es justo el tipo de cosa que nadie cuenta.
CREATE TABLE IF NOT EXISTS mesa_codigos (
  codigo      CHAR(12)  PRIMARY KEY,
  mesa_id     INT       NOT NULL,
  pantalla_id INT       NULL,
  emitido_en  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  caduca_en   DATETIME  NOT NULL,
  canjeado_en DATETIME  NULL,
  visita_id   INT       NULL,
  KEY ix_mesa (mesa_id, emitido_en),
  FOREIGN KEY (mesa_id)     REFERENCES mesas(id) ON DELETE CASCADE,
  FOREIGN KEY (pantalla_id) REFERENCES mesa_pantallas(id) ON DELETE SET NULL,
  FOREIGN KEY (visita_id)   REFERENCES visitas(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Cada teléfono unido a la visita. Una mesa de cuatro puede pedir desde cuatro móviles contra la
-- misma cuenta. Si el teléfono tiene cuenta de cliente, queda enlazada; si no, es un anónimo con
-- su alias, que es como funciona hoy quien no quiere registrarse.
CREATE TABLE IF NOT EXISTS visita_dispositivos (
  token        CHAR(64)  PRIMARY KEY,
  visita_id    INT       NOT NULL,
  cliente_id   INT       NULL,
  alias        VARCHAR(40) NULL,
  unido_en     DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ultimo_visto DATETIME  NULL,
  KEY ix_visita (visita_id),
  FOREIGN KEY (visita_id)  REFERENCES visitas(id) ON DELETE CASCADE,
  FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE SET NULL
) ENGINE=InnoDB;

INSERT IGNORE INTO ajustes (clave, valor) VALUES
 ('qr_mesas_activo',   'si'),
 ('qr_min_seg',        '5'),    -- lo que menos dura un código en pantalla
 ('qr_max_seg',        '50'),   -- lo que más; el intervalo se sortea entre los dos
 ('qr_margen_seg',     '10'),   -- margen de gracia tras apagarse, por si se lee justo al final
 ('visita_cierre_min', '10');   -- tras saldar la cuenta, cuánto se espera para cerrar la visita
