# Mejoras pendientes

De las diez propuestas el 21/09/2026 están hechas la **7** (carta editable), la **4** (dividir
cuenta y pago mixto), la **1** (sesiones con token y roles) y la **2** (HTTPS). Las seis restantes
quedan aquí, ordenadas por lo que aportan al proyecto.

## Administración de sistemas (lo que más peso tiene en el ciclo)

### 6. Copia de seguridad automática de MariaDB
`mariadb-dump` diario con un `systemd timer`, retención de una semana y comprobación de que la copia
se puede restaurar. Perder un día de servicio es perder la facturación de ese día.

### 10. Pruebas automáticas y despliegue
`pytest` contra la API sobre una base de datos de pruebas, ejecutado antes de cada despliegue.
Convierte «funciona» en algo que se puede demostrar delante del tribunal.

## Funcionalidad del negocio

### 3. Modo sin red en el TPV
Si cae el wifi, el camarero no puede ni tomar nota. Guardando la comanda en IndexedDB y
sincronizándola al volver la conexión, el servicio no se para.

### 5. Arqueo de caja y cierre Z
El informe enseña lo vendido, pero no el descuadre: fondo inicial, efectivo contado al cerrar,
diferencia y cierre firmado por el encargado.

### 8. Alérgenos en el TPV y en cocina
El campo ya existe en la carta desde la mejora 7; falta enseñarlo al tomar la comanda y en la
pantalla de cocina. Es información obligatoria por normativa.

### 9. Pantalla de cliente para recogida
Para los pedidos «para llevar»: una pantalla que enseña los números listos en cuanto el KDS los
marca. Reaprovecha el WebSocket que ya existe.
