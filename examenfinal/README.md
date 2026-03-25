# Dashboard Análisis de Productos Amazon

Este proyecto es un dashboard para analizar productos de Amazon usando Flet, MySQL y Matplotlib.

## Requisitos

- Python 3.8+
- MySQL Server
- MySQL Workbench (opcional, para gestión visual)

## Instalación

1. Clona o descarga el proyecto.
2. Instala las dependencias:
   ```
   pip install flet matplotlib pandas mysql-connector-python
   ```
3. Configura la base de datos:
   - Crea una base de datos llamada `amazon_dashboard` en MySQL.
   - Ejecuta el script `create_db.sql` en MySQL Workbench o línea de comandos.
4. Coloca el archivo `amazon_dataset.csv` en la carpeta del proyecto.
5. Ejecuta la aplicación:
   ```
   python main.py
   ```

## Uso

- **Login**: Usa 'admin'/'admin' para administrador o 'employee'/'employee' para empleado.
- **Pestaña General**: Filtros, productos, detalles con imagen, reseñas, edición (empleado), gráficos, limpiar pantalla.
- **Pestaña Admin**: Agregar productos, gestionar usuarios (ver lista, agregar nuevos).
- **Pestaña Empleado**: Ver logs de cambios en productos.
- **Gráficos**: Rating por categoría, descuento por categoría, comparación precios del producto seleccionado, valoraciones por categoría.

## Funcionalidades

- Carga y visualización de datos desde CSV.
- Filtros dinámicos por categoría, descuento, rating, valoraciones, nombre.
- Menú desplegable de productos ordenado alfabéticamente.
- Detalles del producto con imagen, reseñas (admin puede bloquear).
- Edición de productos (empleado, con logs).
- Gráficos con Matplotlib y validación de datos.
- Sistema de login con roles.
- Gestión de usuarios y productos (admin).
- Interfaz con pestañas, colores amigables, manejo de errores.

## Notas

- Asegúrate de que el CSV tenga las columnas correctas.
- Configura la conexión a MySQL en `DB_CONFIG` en main.py.
- Los gráficos requieren datos válidos para generarse.