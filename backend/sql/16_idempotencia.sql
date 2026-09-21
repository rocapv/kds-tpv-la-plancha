-- Ampliación: que una comanda guardada sin red no se cobre dos veces al volver la red.
--
-- Cuando el TPV pierde el wifi guarda lo que hace el camarero y lo reenvía al reconectar. El
-- peligro no es perder la comanda: es MANDARLA DOS VECES. Basta con que la petición llegara al
-- servidor y se perdiera la respuesta —wifi que se va justo después de enviar— para que el
-- reenvío cree un pedido gemelo. En una cocina eso son dos platos, y en la caja dos cobros.
--
-- Solución: cada operación del TPV lleva una clave que INVENTA EL CLIENTE (una por acción, no
-- por reintento). El servidor guarda aquí la respuesta que dio la primera vez; si la clave ya
-- está, devuelve esa misma respuesta sin volver a ejecutar nada. Es el mismo mecanismo que usan
-- las pasarelas de pago (`Idempotency-Key`).
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS idempotencia (
  clave       VARCHAR(64)  NOT NULL PRIMARY KEY,   -- la inventa el cliente (uuid)
  ruta        VARCHAR(160) NOT NULL,               -- método y ruta, para poder auditar
  empleado_id INT          NULL,
  estado      SMALLINT     NOT NULL,               -- código HTTP que se devolvió
  respuesta   MEDIUMTEXT   NOT NULL,               -- cuerpo tal cual se devolvió
  creada_en   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_creada (creada_en),
  CONSTRAINT fk_idem_empleado FOREIGN KEY (empleado_id) REFERENCES empleados(id)
) ENGINE=InnoDB;

-- Días que se guarda cada clave. Una comanda sin red se reenvía en minutos; tres días cubre de
-- sobra un puente en el que nadie encendió la tableta, y evita que la tabla crezca sin fin.
INSERT IGNORE INTO ajustes (clave, valor) VALUES
 ('idempotencia_dias', '3');
