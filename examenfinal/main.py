import flet as ft
import pandas as pd
import mysql.connector
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime
import os
from sqlalchemy import create_engine

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Cambia según tu configuración
    'password': '',  # Cambia según tu configuración
    'database': 'amazon_dashboard'
}

# SQLAlchemy engine para pandas
SQLALCHEMY_ENGINE = create_engine(
    f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}",
    echo=False
)

def create_tables():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Tabla productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            product_id VARCHAR(255) PRIMARY KEY,
            product_name TEXT,
            category TEXT,
            discounted_price FLOAT,
            actual_price FLOAT,
            discount_percentage FLOAT,
            rating FLOAT,
            rating_count INT,
            about_product TEXT,
            img_link TEXT,
            product_link TEXT
        )
    ''')
    
    # Tabla reviews
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            review_id VARCHAR(255) PRIMARY KEY,
            product_id VARCHAR(255),
            user_id VARCHAR(255),
            user_name TEXT,
            review_title TEXT,
            review_content TEXT,
            FOREIGN KEY (product_id) REFERENCES productos(product_id)
        )
    ''')
    
    # Tabla system_users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE,
            password VARCHAR(255),
            role ENUM('admin', 'employee')
        )
    ''')
    
    # Insertar usuarios por defecto
    cursor.execute("INSERT IGNORE INTO system_users (username, password, role) VALUES ('admin', 'admin', 'admin')")
    cursor.execute("INSERT IGNORE INTO system_users (username, password, role) VALUES ('employee', 'employee', 'employee')")
    
    # Tabla logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id INT,
            product_id VARCHAR(255),
            change_description TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES system_users(id),
            FOREIGN KEY (product_id) REFERENCES productos(product_id)
        )
    ''')
    
    # Tabla blocked_reviews
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blocked_reviews (
            review_id VARCHAR(255) PRIMARY KEY,
            FOREIGN KEY (review_id) REFERENCES reviews(review_id)
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

def load_csv_to_db(csv_path):
    separators = [',', ';', '\t', '|']
    df = None
    for sep in separators:
        try:
            df = pd.read_csv(csv_path, encoding='utf-8', sep=sep, quoting=3, quotechar='"', on_bad_lines='skip')
            break
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(csv_path, encoding='latin-1', sep=sep, quoting=3, quotechar='"', on_bad_lines='skip')
                break
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(csv_path, encoding='cp1252', sep=sep, quoting=3, quotechar='"', on_bad_lines='skip')
                    break
                except UnicodeDecodeError:
                    continue
        except pd.errors.ParserError:
            continue
    if df is None:
        raise ValueError("No se pudo parsear el CSV con los separadores comunes.")
    
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    for _, row in df.iterrows():
        try:
            product_id = str(row.get('product_id', '')).strip()
            product_name = str(row.get('product_name', '')).strip()
            category = str(row.get('category', '')).strip()
            discounted_price = float(row.get('discounted_price', 0)) if row.get('discounted_price') else 0
            actual_price = float(row.get('actual_price', 0)) if row.get('actual_price') else 0
            discount_percentage = float(row.get('discount_percentage', 0)) if row.get('discount_percentage') else 0
            rating = float(row.get('rating', 0)) if row.get('rating') else 0
            rating_count = int(float(row.get('rating_count', 0))) if row.get('rating_count') else 0
            about_product = str(row.get('about_product', '')).strip()
            img_link = str(row.get('img_link', '')).strip()
            product_link = str(row.get('product_link', '')).strip()
            
            # Insertar producto (solo si no existe)
            cursor.execute('''
                INSERT IGNORE INTO productos (product_id, product_name, category, discounted_price, actual_price, discount_percentage, rating, rating_count, about_product, img_link, product_link)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (product_id, product_name, category, discounted_price, actual_price, discount_percentage, rating, rating_count, about_product, img_link, product_link))
            
            # Parsear reviews (múltiples por fila, separadas por comas)
            user_ids = str(row.get('user_id', '')).split(',') if row.get('user_id') else []
            user_names = str(row.get('user_name', '')).split(',') if row.get('user_name') else []
            review_ids = str(row.get('review_id', '')).split(',') if row.get('review_id') else []
            review_titles = str(row.get('review_title', '')).split(',') if row.get('review_title') else []
            review_contents = str(row.get('review_content', '')).split(',') if row.get('review_content') else []
            
            # Insertar cada review
            for i in range(len(review_ids)):
                try:
                    review_id = review_ids[i].strip() if i < len(review_ids) else None
                    user_id = user_ids[i].strip() if i < len(user_ids) else None
                    user_name = user_names[i].strip() if i < len(user_names) else None
                    review_title = review_titles[i].strip() if i < len(review_titles) else None
                    review_content = review_contents[i].strip() if i < len(review_contents) else None
                    
                    if review_id and user_id and user_name and review_title and review_content:
                        cursor.execute('''
                            INSERT IGNORE INTO reviews (review_id, product_id, user_id, user_name, review_title, review_content)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (review_id, product_id, user_id, user_name, review_title, review_content))
                except Exception as e:
                    pass  # Skip problematic reviews
        except Exception as e:
            pass  # Skip problematic rows
    
    conn.commit()
    cursor.close()
    conn.close()

def get_products(filters=None):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM productos WHERE 1=1"
    params = []
    
    if filters:
        if 'category' in filters and filters['category']:
            query += " AND category LIKE %s"
            params.append(f"%{filters['category']}%")
        if 'discount_min' in filters and filters['discount_min']:
            query += " AND discount_percentage >= %s"
            params.append(float(filters['discount_min']))
        if 'discount_max' in filters and filters['discount_max']:
            query += " AND discount_percentage <= %s"
            params.append(float(filters['discount_max']))
        if 'rating_min' in filters and filters['rating_min']:
            query += " AND rating >= %s"
            params.append(float(filters['rating_min']))
        if 'rating_count_min' in filters and filters['rating_count_min']:
            query += " AND rating_count >= %s"
            params.append(int(filters['rating_count_min']))
        if 'name' in filters and filters['name']:
            query += " AND product_name LIKE %s"
            params.append(f"%{filters['name']}%")
    
    query += " ORDER BY product_name ASC"
    cursor.execute(query, params)
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return products

def get_categories():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM productos")
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    if total == 0 and os.path.exists('amazon_dataset.csv'):
        load_csv_to_db('amazon_dataset.csv')

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM productos")
    categories = [row[0] for row in cursor.fetchall() if row[0]]
    cursor.close()
    conn.close()

    # Separar categorías múltiples
    all_cats = set()
    for cat in categories:
        if cat:
            all_cats.update([c.strip() for c in cat.split('||') if c.strip()])
    return sorted(list(all_cats))

def get_reviews(product_id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reviews WHERE product_id = %s AND review_id NOT IN (SELECT review_id FROM blocked_reviews)", (product_id,))
    reviews = cursor.fetchall()
    cursor.close()
    conn.close()
    return reviews

def ensure_data_loaded():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM productos")
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    if total == 0 and os.path.exists('amazon_dataset.csv'):
        load_csv_to_db('amazon_dataset.csv')

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reviews")
    total_reviews = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    if total_reviews == 0 and os.path.exists('amazon_dataset.csv'):
        load_csv_to_db('amazon_dataset.csv')


def block_review(review_id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("INSERT IGNORE INTO blocked_reviews (review_id) VALUES (%s)", (review_id,))
    conn.commit()
    cursor.close()
    conn.close()

def update_product(product_id, updates, employee_id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
    values = list(updates.values()) + [product_id]
    
    cursor.execute(f"UPDATE productos SET {set_clause} WHERE product_id = %s", values)
    
    # Log the change
    change_desc = f"Updated {', '.join(updates.keys())}"
    cursor.execute("INSERT INTO logs (employee_id, product_id, change_description) VALUES (%s, %s, %s)", (employee_id, product_id, change_desc))
    
    conn.commit()
    cursor.close()
    conn.close()


def generate_rating_by_category():
    df = pd.read_sql("SELECT category, rating FROM productos", SQLALCHEMY_ENGINE)

    df['category'] = df['category'].str.split('||').str[0]
    avg_rating = df.groupby('category')['rating'].mean()

    fig, ax = plt.subplots()
    avg_rating.plot(kind='bar', ax=ax, color='blue')
    ax.set_title('Promedio de Rating por Categoría')
    ax.set_ylabel('Rating')

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{img_str}"


def generate_discount_by_category():
    df = pd.read_sql("SELECT category, discount_percentage FROM productos", SQLALCHEMY_ENGINE)
    
    df['category'] = df['category'].str.split('||').str[0]
    avg_discount = df.groupby('category')['discount_percentage'].mean()
    
    fig, ax = plt.subplots()
    avg_discount.plot(kind='bar', ax=ax, color='orange')
    ax.set_title('Promedio de Descuento por Categoría')
    ax.set_ylabel('Descuento (%)')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{img_str}"

def generate_price_comparison(product_id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT actual_price, discounted_price FROM productos WHERE product_id = %s", (product_id,))
    product = cursor.fetchone()
    conn.close()
    
    if not product:
        return None
    
    fig, ax = plt.subplots()
    ax.bar(['Precio Real', 'Precio con Descuento'], [product['actual_price'], product['discounted_price']], color=['red', 'green'])
    ax.set_title('Comparación de Precios')
    ax.set_ylabel('Precio')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{img_str}"

def generate_rating_count_by_category():
    df = pd.read_sql("SELECT category, rating_count FROM productos", SQLALCHEMY_ENGINE)
    
    df['category'] = df['category'].str.split('||').str[0]
    total_ratings = df.groupby('category')['rating_count'].sum()
    
    fig, ax = plt.subplots()
    total_ratings.plot(kind='pie', ax=ax, autopct='%1.1f%%')
    ax.set_title('Distribución de Cantidad de Valoraciones por Categoría')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{img_str}"

# Agregar más funciones de gráficos similares

def main(page: ft.Page):
    page.title = "Dashboard Análisis Productos Amazon"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1200
    page.window_height = 800
    
    # Variables globales
    current_user = None
    products = []
    selected_product = None
    filters = {}
    
    # Elementos de UI
    login_view = ft.Column()
    dashboard_view = ft.Container()
    
    # Login
    username_field = ft.TextField(label="Usuario", width=300)
    password_field = ft.TextField(label="Contraseña", password=True, width=300)
    login_button = ft.Button("Iniciar Sesión", on_click=lambda e: login(), width=300)
    
    def login():
        nonlocal current_user
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM system_users WHERE username = %s AND password = %s", (username_field.value, password_field.value))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            current_user = user
            page.controls.clear()
            build_dashboard()
            page.update()
        else:
            page.snack_bar = ft.SnackBar(ft.Text("Credenciales incorrectas"))
            page.snack_bar.open = True
            page.update()
    
    login_view.controls = [
        ft.Container(height=100),
        ft.Text("Inicio de Sesión - Dashboard Amazon", size=30, weight=ft.FontWeight.BOLD),
        ft.Container(height=50),
        username_field,
        password_field,
        login_button,
        ft.Container(height=100)
    ]
    
    def build_dashboard():
        nonlocal dashboard_view, products
        products = get_products()
        categories = get_categories()
        selected_product = None
        
        # Filtros
        category_dd = ft.Dropdown(label="Categoría", options=[ft.dropdown.Option(cat) for cat in categories], on_select=lambda e: apply_filters())
        discount_min = ft.TextField(label="Descuento Mín (%)", on_change=lambda e: apply_filters())
        discount_max = ft.TextField(label="Descuento Máx (%)", on_change=lambda e: apply_filters())
        rating_min = ft.TextField(label="Rating Mín", on_change=lambda e: apply_filters())
        rating_count_min = ft.TextField(label="Valoraciones Mín", on_change=lambda e: apply_filters())
        name_search = ft.TextField(label="Buscar por nombre", on_change=lambda e: apply_filters())
        
        # Productos dropdown
        product_options = [ft.dropdown.Option(p['product_id'], p['product_name']) for p in products]
        product_dd = ft.Dropdown(label="Seleccionar Producto", options=product_options, on_select=lambda e: show_product_details())
        
        # Detalles producto
        details_text = ft.Text("", size=12)
        
        # Reseñas
        reviews_list = ft.Column(scroll=ft.ScrollMode.AUTO, height=200)
        
        # Campos para employee editar producto
        edit_name = ft.TextField(label="Nombre", visible=current_user['role']== 'employee')
        edit_price = ft.TextField(label="Precio Descuento", visible=current_user['role']== 'employee')
        edit_rating = ft.TextField(label="Rating", visible=current_user['role']== 'employee')
        save_button = ft.Button("Guardar Cambios", on_click=lambda e: save_changes(), visible=current_user['role']== 'employee')

        # Para admin: agregar producto
        add_product_id = ft.TextField(label="ID Producto")
        add_product_name = ft.TextField(label="Nombre")
        add_category = ft.TextField(label="Categoría")
        add_discounted_price = ft.TextField(label="Precio Descuento")
        add_actual_price = ft.TextField(label="Precio Real")
        add_discount_percentage = ft.TextField(label="Porcentaje Descuento")
        add_rating = ft.TextField(label="Rating")
        add_rating_count = ft.TextField(label="Cantidad Valoraciones")
        add_about = ft.TextField(label="Acerca del Producto")
        add_img_link = ft.TextField(label="Enlace Imagen")
        add_product_link = ft.TextField(label="Enlace Producto")
        add_product_button = ft.Button("Agregar Producto", on_click=lambda e: add_product())
        
        # Gestionar usuarios
        users_list = ft.Column(scroll=ft.ScrollMode.AUTO)
        new_username = ft.TextField(label="Nuevo Usuario")
        new_password = ft.TextField(label="Contraseña", password=True)
        new_role = ft.Dropdown(label="Rol", options=[ft.dropdown.Option("admin"), ft.dropdown.Option("employee")])
        add_user_button = ft.Button("Agregar Usuario", on_click=lambda e: add_user())
        
        # Logs
        logs_list = ft.Column(scroll=ft.ScrollMode.AUTO)
        
        # Imagen producto
        placeholder_img = "https://via.placeholder.com/200?text=Selecciona+un+producto"
        product_image = ft.Image(src=placeholder_img, width=200, height=200)
        chart_image = ft.Image(src="", width=600, height=400)
        chart_buttons = ft.Row([
            ft.Button("Rating por Categoría", on_click=lambda e: show_chart('rating_by_category')),
            ft.Button("Descuento por Categoría", on_click=lambda e: show_chart('discount_by_category')),
            ft.Button("Comparación Precios", on_click=lambda e: show_chart('price_comparison')),
            ft.Button("Valoraciones por Categoría", on_click=lambda e: show_chart('rating_count_by_category')),
        ], wrap=True)
        
        def apply_filters():
            nonlocal filters, products
            filters = {
                'category': category_dd.value,
                'discount_min': discount_min.value if discount_min.value else None,
                'discount_max': discount_max.value if discount_max.value else None,
                'rating_min': rating_min.value if rating_min.value else None,
                'rating_count_min': rating_count_min.value if rating_count_min.value else None,
                'name': name_search.value
            }
            products = get_products(filters)
            product_options = [ft.dropdown.Option(p['product_id'], p['product_name']) for p in products]
            product_dd.options = product_options
            product_dd.value = None
            selected_product = None
            details_text.value = ""
            reviews_list.controls.clear()
            page.update()
        
        def clear_filters():
            category_dd.value = None
            discount_min.value = ""
            discount_max.value = ""
            rating_min.value = ""
            rating_count_min.value = ""
            name_search.value = ""
            apply_filters()
        
        clear_button = ft.Button("Limpiar Filtros", on_click=lambda e: clear_filters())
        
        def show_chart(chart_type):
            try:
                if chart_type == 'rating_by_category':
                    img_src = generate_rating_by_category()
                elif chart_type == 'discount_by_category':
                    img_src = generate_discount_by_category()
                elif chart_type == 'price_comparison' and selected_product:
                    img_src = generate_price_comparison(selected_product['product_id'])
                elif chart_type == 'rating_count_by_category':
                    img_src = generate_rating_count_by_category()
                else:
                    img_src = None
                if img_src:
                    chart_image.src = img_src
                else:
                    chart_image.src = ""
                page.update()
            except Exception as e:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error generando gráfico: {str(e)}"))
                page.snack_bar.open = True
                page.update()
        
        def clear_screen():
            product_dd.value = None
            details_text.value = ""
            reviews_list.controls.clear()
            product_image.src = placeholder_img
            chart_image.src = ""
            if current_user['role'] == 'employee':
                edit_name.value = ""
                edit_price.value = ""
                edit_rating.value = ""
            page.update()
        
        def show_product_details():
            nonlocal selected_product
            if product_dd.value:
                selected_product = next((p for p in products if p['product_id'] == product_dd.value), None)
                if selected_product:
                    details = f"ID: {selected_product['product_id']}\nNombre: {selected_product['product_name']}\nCategoría: {selected_product['category']}\nPrecio Desc: {selected_product['discounted_price']}\nPrecio Real: {selected_product['actual_price']}\nDescuento: {selected_product['discount_percentage']}%\nRating: {selected_product['rating']}\nValoraciones: {selected_product['rating_count']}\nAcerca: {selected_product['about_product']}"
                    details_text.value = details
                    
                    # Mostrar reseñas
                    reviews = get_reviews(selected_product['product_id'])
                    reviews_list.controls.clear()
                    for r in reviews:
                        review_text = f"Título: {r['review_title']}\nContenido: {r['review_content']}\nUsuario: {r['user_name']}"
                        if current_user['role'] == 'admin':
                            block_btn = ft.Button("Bloquear", on_click=lambda e, rid=r['review_id']: block_review_action(rid))
                            reviews_list.controls.append(ft.Container(content=ft.Column([ft.Text(review_text), block_btn])))
                        else:
                            reviews_list.controls.append(ft.Text(review_text))
                    
                    # Para employee, llenar campos de edición
                    if current_user['role'] == 'employee':
                        edit_name.value = selected_product['product_name']
                        edit_price.value = str(selected_product['discounted_price'])
                        edit_rating.value = str(selected_product['rating'])
                    
                    # Mostrar imagen
                    if selected_product['img_link']:
                        product_image.src = selected_product['img_link']
                    else:
                        product_image.src = placeholder_img
                    
                    page.update()
        
        def block_review_action(review_id):
            block_review(review_id)
            show_product_details()  # Refresh
        
        def save_changes():
            if selected_product and current_user['role'] == 'employee':
                updates = {}
                if edit_name.value != selected_product['product_name']:
                    updates['product_name'] = edit_name.value
                try:
                    if edit_price.value and float(edit_price.value) != selected_product['discounted_price']:
                        updates['discounted_price'] = float(edit_price.value)
                except ValueError:
                    page.snack_bar = ft.SnackBar(ft.Text("Precio inválido"))
                    page.snack_bar.open = True
                    page.update()
                    return
                try:
                    if edit_rating.value and float(edit_rating.value) != selected_product['rating']:
                        updates['rating'] = float(edit_rating.value)
                except ValueError:
                    page.snack_bar = ft.SnackBar(ft.Text("Rating inválido"))
                    page.snack_bar.open = True
                    page.update()
                    return
                if updates:
                    update_product(selected_product['product_id'], updates, current_user['id'])
                    show_product_details()  # Refresh
        
        def add_product():
            if current_user['role'] == 'admin':
                try:
                    conn = mysql.connector.connect(**DB_CONFIG)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO productos (product_id, product_name, category, discounted_price, actual_price, discount_percentage, rating, rating_count, about_product, img_link, product_link)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (add_product_id.value, add_product_name.value, add_category.value, float(add_discounted_price.value), float(add_actual_price.value), float(add_discount_percentage.value), float(add_rating.value), int(add_rating_count.value), add_about.value, add_img_link.value, add_product_link.value))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    categories[:] = get_categories()
                    category_dd.options = [ft.dropdown.Option(cat) for cat in categories]
                    product_dd.options = [ft.dropdown.Option(p['product_id'], p['product_name']) for p in get_products()]
                    page.snack_bar = ft.SnackBar(ft.Text("Producto agregado"))
                    page.snack_bar.open = True
                    page.update()
                except Exception as e:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(e)}"))
                    page.snack_bar.open = True
                    page.update()
        
        def add_user():
            if current_user['role'] == 'admin':
                try:
                    conn = mysql.connector.connect(**DB_CONFIG)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO system_users (username, password, role) VALUES (%s, %s, %s)", (new_username.value, new_password.value, new_role.value))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    load_users()
                    page.snack_bar = ft.SnackBar(ft.Text("Usuario agregado"))
                    page.snack_bar.open = True
                    page.update()
                except Exception as e:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Error: {str(e)}"))
                    page.snack_bar.open = True
                    page.update()
        
        def load_users():
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT username, role FROM system_users")
            users = cursor.fetchall()
            cursor.close()
            conn.close()
            users_list.controls.clear()
            for u in users:
                users_list.controls.append(ft.Text(f"{u['username']} - {u['role']}"))
            page.update()
        
        def load_logs():
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT l.change_description, l.timestamp, u.username, p.product_name FROM logs l JOIN system_users u ON l.employee_id = u.id JOIN productos p ON l.product_id = p.product_id ORDER BY l.timestamp DESC")
            logs = cursor.fetchall()
            cursor.close()
            conn.close()
            logs_list.controls.clear()
            for lg in logs:
                logs_list.controls.append(ft.Text(f"{lg['timestamp']} - {lg['username']} cambió {lg['product_name']}: {lg['change_description']}"))
            page.update()
        
        def clear_screen():
            product_dd.value = None
            details_text.value = ""
            reviews_list.controls.clear()
            product_image.src = placeholder_img
            chart_image.src = ""
            if current_user['role'] == 'employee':
                edit_name.value = ""
                edit_price.value = ""
                edit_rating.value = ""
            page.update()
        
        # Layout con tabs
        filters_row = ft.Row([category_dd, discount_min, discount_max, rating_min, rating_count_min, name_search, clear_button], wrap=True)
        edit_row = ft.Row([edit_name, edit_price, edit_rating, save_button]) if current_user['role'] == 'employee' else ft.Row()

        general_content = ft.Column([
            filters_row,
            ft.Row([product_dd, ft.Column([details_text, product_image, reviews_list])]),
            edit_row,
            ft.Button("Limpiar Pantalla", on_click=lambda e: clear_screen()),
            ft.Row([chart_buttons, chart_image])
        ], scroll=ft.ScrollMode.AUTO)
        
        admin_content = ft.Column([
            ft.Text("Agregar Producto", size=20),
            ft.Row([add_product_id, add_product_name, add_category]),
            ft.Row([add_discounted_price, add_actual_price, add_discount_percentage]),
            ft.Row([add_rating, add_rating_count, add_about]),
            ft.Row([add_img_link, add_product_link, add_product_button]),
            ft.Text("Gestionar Usuarios", size=20),
            users_list,
            ft.Row([new_username, new_password, new_role, add_user_button]),
        ], scroll=ft.ScrollMode.AUTO)
        
        employee_content = ft.Column([
            ft.Text("Logs de Cambios", size=20),
            logs_list,
        ], scroll=ft.ScrollMode.AUTO)
        
        general_tab = ft.Tab(
            label="General"
        )
        
        admin_tab = ft.Tab(
            label="Admin"
        )
        
        employee_tab = ft.Tab(
            label="Empleado"
        )
        
        tab_list = [general_tab]
        content_list = [general_content]
        if current_user['role'] == 'admin':
            tab_list.append(admin_tab)
            content_list.append(admin_content)
        if current_user['role'] == 'employee':
            tab_list.append(employee_tab)
            content_list.append(employee_content)
        
        tab_view = ft.TabBarView(controls=content_list, expand=1)
        tab_bar = ft.TabBar(
            tabs=tab_list,
            on_click=lambda e: (
                setattr(tab_view, 'selected_index', e.data if e.data is not None else e.control.selected_index),
                page.update()
            )
        )

        tabs = ft.Tabs(
            content=ft.Column([tab_bar, tab_view], expand=True),
            length=len(content_list),
            selected_index=0,
            on_change=lambda e: (
                setattr(tab_view, 'selected_index', e.data if e.data is not None else e.control.selected_index),
                page.update()
            ),
        )

        dashboard_view.content = tabs
        page.add(dashboard_view)
        
        # Cargar datos iniciales
        load_users()
        load_logs()
    
    page.add(login_view)
    
    # Crear tablas y cargar datos si es necesario
    create_tables()
    ensure_data_loaded()

ft.run(main)
