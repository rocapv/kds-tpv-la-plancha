-- Ampliación: el almacén de verdad, con entradas, salidas y un producto que se cae solo de la
-- carta cuando se acaba el género.
--
-- Hasta hoy «agotado» era una casilla que alguien tenía que acordarse de marcar, y el stock un
-- número suelto en `inventario` que nadie movía. Eso no es un inventario: es una foto vieja.
-- Lo que hacía falta, tal y como lo pidió RocaPV, es que cada kilo tenga su **entrada** («se ha
-- comprado pollo al proveedor X») y su **salida** («se ha vendido Y de pollo»), y que el TPV
-- pueda mirar ese saldo para decidir si algo se puede pedir o no.
--
-- Las piezas ya existentes se reaprovechan: `inventario` (los artículos), `albaranes` y
-- `movimientos_inventario` (el libro mayor, que estaba creado y sin usar). Lo que se añade aquí
-- es lo que faltaba para cerrar el círculo: **la receta** y el **saldo que cuadra**.
SET NAMES utf8mb4;

-- ── 1 · La receta: qué gasta cada plato ────────────────────────────────────────────────────
-- Sin esto no se puede descontar nada: vender una hamburguesa no gasta «una hamburguesa», gasta
-- 180 g de proteína, un pan y 30 g de queso. Un producto puede gastar varios artículos y un
-- artículo lo usan varios productos, así que es una tabla N:M con cantidad.
CREATE TABLE IF NOT EXISTS producto_receta (
  producto_id   INT NOT NULL,
  inventario_id INT NOT NULL,
  cantidad      DECIMAL(10,3) NOT NULL DEFAULT 1,   -- en la unidad del artículo (kg, ud, l)
  PRIMARY KEY (producto_id, inventario_id),
  FOREIGN KEY (producto_id)   REFERENCES productos(id)  ON DELETE CASCADE,
  FOREIGN KEY (inventario_id) REFERENCES inventario(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Lo que ya había: `productos.inventario_id` era una relación de uno a uno y sin cantidad, que
-- servía para calcular el precio pero no para descontar. Se convierte en receta de una unidad,
-- sin perder nada.
INSERT IGNORE INTO producto_receta (producto_id, inventario_id, cantidad)
SELECT id, inventario_id, 1 FROM productos WHERE inventario_id IS NOT NULL;

-- ── 2 · Mínimo por artículo, para avisar antes de quedarse a cero ──────────────────────────
ALTER TABLE inventario
  ADD COLUMN IF NOT EXISTS minimo DECIMAL(10,2) NOT NULL DEFAULT 0 AFTER stock;

-- ── 3 · El libro mayor arranca cuadrado ────────────────────────────────────────────────────
-- `movimientos_inventario` existía vacío mientras `inventario.stock` ya traía cantidades: el
-- saldo y su historia no cuadraban. Se abre el libro con un recuento inicial por artículo, de
-- modo que a partir de hoy **saldo = suma de movimientos** y se puede demostrar.
INSERT INTO movimientos_inventario (inventario_id, cantidad, motivo, nota, empleado_id, creado_en)
SELECT i.id, i.stock, 'recuento', 'Saldo inicial al abrir el libro de inventario',
       (SELECT id FROM empleados WHERE activo ORDER BY id LIMIT 1), NOW()
  FROM inventario i
 WHERE i.stock <> 0
   AND NOT EXISTS (SELECT 1 FROM movimientos_inventario m WHERE m.inventario_id = i.id);

-- ── 4 · Interruptores ──────────────────────────────────────────────────────────────────────
INSERT IGNORE INTO ajustes (clave, valor) VALUES
 -- Descontar del almacén al mandar la comanda a cocina. Se puede apagar para dar de alta la
 -- carta o para un servicio en el que el almacén todavía no está al día.
 ('inventario_descontar', 'si'),
 -- Dar de baja de la carta automáticamente lo que ya no se puede hacer por falta de género.
 ('inventario_agota_carta', 'si');

-- ── 5 · Un albarán puede no tener foto ─────────────────────────────────────────────────────
-- `albaranes` nació para la lectura de fotos con el modelo de visión, y por eso exigía imagen.
-- Pero el albarán existe lo fotografíe alguien o no: si el encargado prefiere teclear las
-- cuatro líneas que trae el repartidor, tiene que poder, y quedar en el mismo sitio.
ALTER TABLE albaranes MODIFY COLUMN imagen_id INT NULL;
