-- Ampliación: cuando a alguien lo cambian de puesto, se entera.
--
-- Hasta ahora el cambio se avisaba con un mensajito de tres segundos por el WebSocket. Eso
-- funciona si la persona está delante de la pantalla en ese preciso instante, que es
-- exactamente cuando NO está: la mueven porque hace falta en otro sitio, así que está andando
-- entre la barra y la cocina. El aviso tiene que esperarla.
--
-- Por eso se guarda: el aviso vive en la base de datos hasta que la persona dice «enterado»,
-- sobrevive a recargas, a cerrar sesión y a cambiar de tableta, y le sale en cuanto entra.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS avisos_empleado (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  empleado_id INT          NOT NULL,
  texto       VARCHAR(200) NOT NULL,
  detalle     VARCHAR(200) NULL,          -- adónde va: la pantalla que le toca ahora
  de_quien    INT          NULL,          -- quién lo movió; un aviso sin firma no vale nada
  creado_en   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  visto_en    DATETIME     NULL,
  FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE,
  FOREIGN KEY (de_quien)    REFERENCES empleados(id),
  KEY ix_pendientes (empleado_id, visto_en)
) ENGINE=InnoDB;
