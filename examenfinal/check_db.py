#!/usr/bin/env python
import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'amazon_dashboard'
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Verificar productos
    cursor.execute("SELECT COUNT(*) FROM productos")
    product_count = cursor.fetchone()[0]
    print(f"Total productos: {product_count}")
    
    # Verificar reviews
    cursor.execute("SELECT COUNT(*) FROM reviews")
    review_count = cursor.fetchone()[0]
    print(f"Total reviews: {review_count}")
    
    # Mostrar categorías
    cursor.execute("SELECT DISTINCT SUBSTR(category, 1, 60) as cat_sample FROM productos LIMIT 5")
    cats = cursor.fetchall()
    print(f"Categorías (muestras): {[c[0] for c in cats]}")
    
    # Mostrar un producto
    cursor.execute("SELECT product_id, product_name FROM productos LIMIT 1")
    prod = cursor.fetchone()
    if prod:
        print(f"Producto ejemplo: {prod[0]} - {prod[1][:60]}")
    
    cursor.close()
    conn.close()
    print("✓ Conexión a BD exitosa")
except Exception as e:
    print(f"✗ Error: {e}")
