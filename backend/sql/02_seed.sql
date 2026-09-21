-- Datos de demostración. El decorado (nombres de la cantina Vesta-9) lo pone
-- después sql/06_tema_asteroide.sql, que actualiza estas mismas filas por id.
SET NAMES utf8mb4;

INSERT INTO empleados (nombre, rol, pin) VALUES
 ('Laura',  'camarero',  '1111'),
 ('Marc',   'camarero',  '2222'),
 ('Aitana', 'cocina',    '3333'),
 ('Pau',    'encargado', '9999');

INSERT INTO mesas (nombre, zona, plazas) VALUES
 ('S1','sala',4),('S2','sala',4),('S3','sala',2),('S4','sala',6),('S5','sala',4),('S6','sala',2),
 ('T1','terraza',4),('T2','terraza',4),('T3','terraza',6),('T4','terraza',2),
 ('B1','barra',1),('B2','barra',1),('B3','barra',1);

INSERT INTO categorias (id, nombre, orden, color) VALUES
 (1,'Hamburguesas',1,'#c0392b'),
 (2,'Entrantes',   2,'#d68910'),
 (3,'Ensaladas',   3,'#229954'),
 (4,'Bebidas',     4,'#2471a3'),
 (5,'Postres',     5,'#8e44ad');

INSERT INTO productos (categoria_id, nombre, precio_cent, estacion) VALUES
 (1,'Clásica',            950,'plancha'),
 (1,'Cheeseburger',      1050,'plancha'),
 (1,'Bacon BBQ',         1190,'plancha'),
 (1,'Doble smash',       1350,'plancha'),
 (1,'Pollo crujiente',   1090,'freidora'),
 (1,'Veggie',            1050,'plancha'),
 (2,'Patatas fritas',     350,'freidora'),
 (2,'Patatas deluxe',     450,'freidora'),
 (2,'Aros de cebolla',    490,'freidora'),
 (2,'Nuggets (8)',        590,'freidora'),
 (2,'Nachos con queso',   790,'frios'),
 (3,'César',              890,'frios'),
 (3,'Caprese',            850,'frios'),
 (4,'Agua',               200,'barra'),
 (4,'Refresco',           280,'barra'),
 (4,'Caña',               250,'barra'),
 (4,'Cerveza artesana',   450,'barra'),
 (4,'Batido',             450,'barra'),
 (5,'Brownie',            550,'frios'),
 (5,'Cheesecake',         590,'frios'),
 (5,'Helado',             390,'frios');
