# Guía Express (10 minutos) para defender el examen DAI

## 0) Objetivo de defensa
Demostrar rápidamente que tu app cumple:
- Carga CSV + MySQL.
- Filtros dinámicos.
- Gráficos con Matplotlib.
- Login por roles (admin/employee).
- Bloqueo de reseñas tóxicas (admin).
- Edición de productos con logs (employee).

---

## 1) Setup ultra-rápido

1. Abre MySQL Workbench y ejecuta:
   - `create_db.sql`
2. Verifica que el CSV exista en la carpeta `examenfinal/`.
3. Instala dependencias:

```bash
pip install flet matplotlib pandas mysql-connector-python sqlalchemy
```

4. Ejecuta:

```bash
python main.py
```

> Usuario admin: `admin` / `admin`  
> Usuario empleado: `employee` / `employee`

---

## 2) Script de exposición (lo dices tal cual)

### A) Carga y visualización
- “La aplicación crea tablas automáticamente y carga `amazon_dataset.csv` si la base está vacía.”
- “El dropdown de productos se ordena alfabéticamente por `product_name`.”
- “Al seleccionar un producto, muestro detalle completo: precios, descuento, rating, valoraciones, descripción e imagen.”

### B) Filtros dinámicos
- “Puedo filtrar por categoría, rango de descuento, rating mínimo, cantidad mínima de valoraciones y búsqueda por texto parcial.”
- “Las categorías se separan desde `Casa||Electrónica` a categorías únicas, para que un mismo producto aparezca en ambas.”
- “El botón **Limpiar Filtros** reinicia el estado y recarga la lista.”

### C) Gráficos
- “Tengo 4 gráficos: rating por categoría, descuento promedio por categoría, comparación de precio real vs descuento del producto seleccionado y distribución de valoraciones por categoría.”
- “Antes de graficar, valido datos numéricos para evitar errores de conversión.”

### D) Seguridad por roles
- “Admin puede gestionar usuarios, agregar productos y bloquear reseñas con mal tono.”
- “Empleado no agrega productos; solo edita datos permitidos del producto.”
- “Cada edición del empleado se guarda en la tabla `logs` con fecha/hora y descripción de cambio.”

### E) Persistencia
- “Todo se persiste en MySQL: productos, reseñas, usuarios del sistema, reseñas bloqueadas y logs.”
- “El cliente que reseña es un dato de negocio (`user_id`, `user_name` en reviews), no un usuario del sistema.”

---

## 3) Checklist mínimo de evaluación

- [ ] Login funciona para admin/employee.
- [ ] Dropdown de productos ordenado.
- [ ] Filtro por categoría devuelve productos multi-categoría correctamente.
- [ ] Búsqueda por prefijo (`co`) devuelve coincidencias parciales.
- [ ] Gráficos se muestran sin crash.
- [ ] Admin bloquea una reseña y deja de mostrarse.
- [ ] Employee edita producto y aparece registro en logs.
- [ ] Botón limpiar filtros y limpiar pantalla funcionales.

---

## 4) Preguntas trampa y respuestas rápidas

### “¿Cómo normalizaste la BD?”
Respuesta corta:
- Entidades separadas: `productos`, `reviews`, `system_users`, `logs`, `blocked_reviews`.
- Relaciones por FK: `reviews.product_id -> productos.product_id`, `logs.employee_id -> system_users.id`, `logs.product_id -> productos.product_id`.
- Usuarios del sistema y usuarios que reseñan se separan conceptualmente.

### “¿Cómo manejas datos inconsistentes?”
Respuesta corta:
- Parseo defensivo de CSV con separadores y codificaciones alternativas.
- Conversión validada para campos numéricos.
- Filas/reseñas dañadas se omiten para no romper la carga total.

### “¿Cómo justificas usabilidad?”
Respuesta corta:
- Flujo por pestañas (General/Admin/Empleado).
- Acciones clave con botones claros (filtrar, limpiar, graficar, guardar).
- Feedback inmediato con `SnackBar` en éxito/error.

---

## 5) Plan B si algo falla en vivo

- Si falla login: verifica en Workbench la tabla `system_users`.
- Si no hay productos: confirma que `amazon_dataset.csv` está en la misma carpeta que `main.py`.
- Si falla conexión: revisa `DB_CONFIG` en `main.py` (host/user/password/database).
- Si no se ven gráficos: verifica instalación de `matplotlib` y que hay datos numéricos válidos.

---

## 6) Cierre para el docente (30 segundos)

“Este dashboard integra ingesta de datos CSV, persistencia relacional en MySQL, filtros dinámicos, visualización analítica con Matplotlib y control de acceso por roles. Admin y empleado tienen permisos diferenciados y trazabilidad por logs, cumpliendo requerimientos funcionales y de gestión.”
