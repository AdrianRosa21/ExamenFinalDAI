import base64
import csv
import io
import os
import re
from datetime import datetime

import flet as ft
import matplotlib.pyplot as plt
import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "amazon_dashboard",
}

DATASET_PATH = os.path.join(os.path.dirname(__file__), "amazon_dataset.csv")


def db_conn():
    return mysql.connector.connect(**DB_CONFIG)


def parse_float(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^0-9.\-]", "", str(value).strip())
    if cleaned.count(".") > 1:
        first, *rest = cleaned.split(".")
        cleaned = first + "." + "".join(rest)
    try:
        return float(cleaned) if cleaned else default
    except ValueError:
        return default


def parse_int(value, default=0):
    return int(parse_float(value, default))


def normalize_discount(raw):
    d = parse_float(raw, 0.0)
    return d * 100 if 0 <= d <= 1 else d


def split_categories(category_text):
    if not category_text:
        return []
    parts = re.split(r"\|\||\|", str(category_text))
    return [p.strip() for p in parts if p.strip()]


def create_tables():
    conn = db_conn()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            product_id VARCHAR(255) PRIMARY KEY,
            product_name TEXT,
            category_raw TEXT,
            discounted_price DOUBLE,
            actual_price DOUBLE,
            discount_percentage DOUBLE,
            rating DOUBLE,
            rating_count INT,
            about_product LONGTEXT,
            img_link TEXT,
            product_link TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS product_categories (
            product_id VARCHAR(255),
            category_id INT,
            PRIMARY KEY (product_id, category_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            review_id VARCHAR(255) PRIMARY KEY,
            product_id VARCHAR(255),
            reviewer_external_id VARCHAR(255),
            reviewer_name TEXT,
            review_title TEXT,
            review_content LONGTEXT,
            blocked TINYINT(1) DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(80) UNIQUE,
            password VARCHAR(255),
            role ENUM('admin','employee')
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id INT,
            product_id VARCHAR(255),
            changed_fields TEXT,
            changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS observations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id VARCHAR(255),
            note LONGTEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute("INSERT IGNORE INTO users (username,password,role) VALUES ('admin','admin','admin')")
    cursor.execute("INSERT IGNORE INTO users (username,password,role) VALUES ('employee','employee','employee')")

    conn.commit()
    cursor.close()
    conn.close()


def load_csv_to_db(csv_path=DATASET_PATH):
    if not os.path.exists(csv_path):
        return 0

    inserted = 0
    conn = db_conn()
    cursor = conn.cursor()

    with open(csv_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            product_id = str(row.get("product_id", "")).strip()
            if not product_id:
                continue

            cursor.execute(
                """
                INSERT INTO products
                (product_id, product_name, category_raw, discounted_price, actual_price,
                 discount_percentage, rating, rating_count, about_product, img_link, product_link)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    product_name=VALUES(product_name),
                    category_raw=VALUES(category_raw),
                    discounted_price=VALUES(discounted_price),
                    actual_price=VALUES(actual_price),
                    discount_percentage=VALUES(discount_percentage),
                    rating=VALUES(rating),
                    rating_count=VALUES(rating_count),
                    about_product=VALUES(about_product),
                    img_link=VALUES(img_link),
                    product_link=VALUES(product_link)
                """,
                (
                    product_id,
                    row.get("product_name", "").strip(),
                    row.get("category", "").strip(),
                    parse_float(row.get("discounted_price")),
                    parse_float(row.get("actual_price")),
                    normalize_discount(row.get("discount_percentage")),
                    parse_float(row.get("rating")),
                    parse_int(row.get("rating_count")),
                    row.get("about_product", "").strip(),
                    row.get("img_link", "").strip(),
                    row.get("product_link", "").strip(),
                ),
            )

            # categories normalized
            for cat in split_categories(row.get("category", "")):
                cursor.execute("INSERT IGNORE INTO categories (name) VALUES (%s)", (cat,))
                cursor.execute("SELECT id FROM categories WHERE name=%s", (cat,))
                cat_id = cursor.fetchone()[0]
                cursor.execute(
                    "INSERT IGNORE INTO product_categories (product_id, category_id) VALUES (%s,%s)",
                    (product_id, cat_id),
                )

            review_ids = [x.strip() for x in str(row.get("review_id", "")).split(",") if x.strip()]
            user_ids = [x.strip() for x in str(row.get("user_id", "")).split(",")]
            user_names = [x.strip() for x in str(row.get("user_name", "")).split(",")]
            titles = [x.strip() for x in str(row.get("review_title", "")).split(",")]
            contents = [x.strip() for x in str(row.get("review_content", "")).split(",")]

            for i, rid in enumerate(review_ids):
                cursor.execute(
                    """
                    INSERT INTO reviews
                    (review_id, product_id, reviewer_external_id, reviewer_name, review_title, review_content)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        review_title=VALUES(review_title),
                        review_content=VALUES(review_content)
                    """,
                    (
                        rid,
                        product_id,
                        user_ids[i] if i < len(user_ids) else "",
                        user_names[i] if i < len(user_names) else "",
                        titles[i] if i < len(titles) else "",
                        contents[i] if i < len(contents) else "",
                    ),
                )
            inserted += 1

    conn.commit()
    cursor.close()
    conn.close()
    return inserted


def ensure_data_loaded():
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    if count == 0:
        load_csv_to_db()


def get_categories():
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories ORDER BY name ASC")
    rows = [r[0] for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows


def get_products(filters=None):
    filters = filters or {}
    conn = db_conn()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT DISTINCT p.*
        FROM products p
        LEFT JOIN product_categories pc ON p.product_id = pc.product_id
        LEFT JOIN categories c ON pc.category_id = c.id
        WHERE 1=1
    """
    params = []

    if filters.get("category"):
        query += " AND c.name = %s"
        params.append(filters["category"])
    if filters.get("discount_min"):
        query += " AND p.discount_percentage >= %s"
        params.append(parse_float(filters["discount_min"]))
    if filters.get("discount_max"):
        query += " AND p.discount_percentage <= %s"
        params.append(parse_float(filters["discount_max"]))
    if filters.get("rating_min"):
        query += " AND p.rating >= %s"
        params.append(parse_float(filters["rating_min"]))
    if filters.get("rating_count_min"):
        query += " AND p.rating_count >= %s"
        params.append(parse_int(filters["rating_count_min"]))
    if filters.get("name"):
        query += " AND p.product_name LIKE %s"
        params.append(f"%{filters['name']}%")

    query += " ORDER BY p.product_name ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_reviews(product_id, include_blocked=False):
    conn = db_conn()
    cursor = conn.cursor(dictionary=True)
    sql = "SELECT * FROM reviews WHERE product_id=%s"
    params = [product_id]
    if not include_blocked:
        sql += " AND blocked=0"
    sql += " ORDER BY review_id"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def block_review(review_id):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE reviews SET blocked=1 WHERE review_id=%s", (review_id,))
    conn.commit()
    cursor.close()
    conn.close()


def update_product(product_id, updates, employee_id):
    if not updates:
        return
    conn = db_conn()
    cursor = conn.cursor()
    set_part = ", ".join([f"{k}=%s" for k in updates.keys()])
    vals = list(updates.values()) + [product_id]
    cursor.execute(f"UPDATE products SET {set_part} WHERE product_id=%s", vals)
    cursor.execute(
        "INSERT INTO logs (employee_id, product_id, changed_fields) VALUES (%s,%s,%s)",
        (employee_id, product_id, ", ".join(updates.keys())),
    )
    conn.commit()
    cursor.close()
    conn.close()


def add_product(data):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO products
        (product_id, product_name, category_raw, discounted_price, actual_price,
         discount_percentage, rating, rating_count, about_product, img_link, product_link)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            data["product_id"],
            data["product_name"],
            data["category"],
            parse_float(data["discounted_price"]),
            parse_float(data["actual_price"]),
            normalize_discount(data["discount_percentage"]),
            parse_float(data["rating"]),
            parse_int(data["rating_count"]),
            data["about_product"],
            data["img_link"],
            data["product_link"],
        ),
    )
    for cat in split_categories(data["category"]):
        cursor.execute("INSERT IGNORE INTO categories (name) VALUES (%s)", (cat,))
        cursor.execute("SELECT id FROM categories WHERE name=%s", (cat,))
        cat_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT IGNORE INTO product_categories (product_id, category_id) VALUES (%s,%s)",
            (data["product_id"], cat_id),
        )
    conn.commit()
    cursor.close()
    conn.close()


def add_user(username, password, role):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (username,password,role) VALUES (%s,%s,%s)", (username, password, role))
    conn.commit()
    cursor.close()
    conn.close()


def list_users():
    conn = db_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, role FROM users ORDER BY username")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users


def list_logs():
    conn = db_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT l.changed_at, u.username, l.product_id, l.changed_fields
        FROM logs l
        JOIN users u ON l.employee_id = u.id
        ORDER BY l.changed_at DESC
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def add_observation(product_id, note):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO observations (product_id, note) VALUES (%s,%s)", (product_id, note))
    conn.commit()
    cursor.close()
    conn.close()


def chart_to_data_uri(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    uri = "data:image/png;base64," + base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return uri


def chart_rating_by_category():
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT c.name, AVG(p.rating)
        FROM products p
        JOIN product_categories pc ON p.product_id = pc.product_id
        JOIN categories c ON c.id = pc.category_id
        GROUP BY c.name
        ORDER BY c.name
        """
    )
    data = cursor.fetchall()
    cursor.close()
    conn.close()

    if not data:
        return ""

    names = [d[0] for d in data]
    vals = [float(d[1]) for d in data]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(names, vals, color="#3b82f6")
    ax.set_title("Distribución de rating por categoría")
    ax.set_ylabel("Rating promedio")
    ax.tick_params(axis="x", labelrotation=60)
    return chart_to_data_uri(fig)


def chart_discount_by_category():
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT c.name, AVG(p.discount_percentage)
        FROM products p
        JOIN product_categories pc ON p.product_id = pc.product_id
        JOIN categories c ON c.id = pc.category_id
        GROUP BY c.name
        ORDER BY c.name
        """
    )
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    if not data:
        return ""

    names = [d[0] for d in data]
    vals = [float(d[1]) for d in data]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(names, vals, color="#f97316")
    ax.set_title("Promedio de descuento por categoría")
    ax.set_ylabel("Descuento promedio (%)")
    ax.tick_params(axis="x", labelrotation=60)
    return chart_to_data_uri(fig)


def chart_price_comparison(product_id):
    conn = db_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT actual_price, discounted_price FROM products WHERE product_id=%s", (product_id,))
    p = cursor.fetchone()
    cursor.close()
    conn.close()
    if not p:
        return ""

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(["Real", "Descuento"], [p["actual_price"] or 0, p["discounted_price"] or 0], color=["#ef4444", "#22c55e"])
    ax.set_title("Comparación precio real vs descuento")
    ax.set_ylabel("Precio")
    return chart_to_data_uri(fig)


def chart_rating_count_by_category():
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT c.name, SUM(p.rating_count)
        FROM products p
        JOIN product_categories pc ON p.product_id = pc.product_id
        JOIN categories c ON c.id = pc.category_id
        GROUP BY c.name
        ORDER BY c.name
        """
    )
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    if not data:
        return ""

    labels = [d[0] for d in data]
    values = [int(d[1] or 0) for d in data]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(values, labels=labels, autopct="%1.1f%%")
    ax.set_title("Distribución de cantidad de valoraciones")
    return chart_to_data_uri(fig)


def main(page: ft.Page):
    create_tables()
    ensure_data_loaded()

    page.title = "Dashboard Análisis de Productos Amazon"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1400
    page.window_height = 900
    page.scroll = ft.ScrollMode.AUTO

    current_user = {"data": None}
    state = {"products": [], "selected": None}

    username = ft.TextField(label="Usuario", width=280)
    password = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=280)
    login_msg = ft.Text("", color=ft.Colors.RED)

    # Controls shared by dashboard
    category_dd = ft.Dropdown(label="Categoría", width=220)
    discount_min = ft.TextField(label="Descuento mín (%)", width=160)
    discount_max = ft.TextField(label="Descuento máx (%)", width=160)
    rating_min = ft.TextField(label="Rating mín", width=120)
    rating_count_min = ft.TextField(label="Valoraciones mín", width=160)
    name_search = ft.TextField(label="Buscar por nombre", width=250)
    product_dd = ft.Dropdown(label="Producto", width=500)
    details = ft.TextField(multiline=True, min_lines=7, max_lines=9, read_only=True, expand=True)
    product_image = ft.Image(width=220, height=220, fit=ft.ImageFit.CONTAIN)
    chart_image = ft.Image(width=700, height=420, fit=ft.ImageFit.CONTAIN)
    observation = ft.TextField(label="Observación sobre producto seleccionado", multiline=True, min_lines=2, max_lines=4)

    reviews_col = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=260)
    logs_col = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=260)
    users_col = ft.Column(scroll=ft.ScrollMode.ALWAYS, height=170)

    edit_name = ft.TextField(label="Nombre")
    edit_discounted = ft.TextField(label="Precio descuento")
    edit_rating = ft.TextField(label="Rating")

    add_fields = {
        "product_id": ft.TextField(label="ID"),
        "product_name": ft.TextField(label="Nombre", width=380),
        "category": ft.TextField(label="Categorías (separar con |)", width=300),
        "discounted_price": ft.TextField(label="Precio descuento"),
        "actual_price": ft.TextField(label="Precio real"),
        "discount_percentage": ft.TextField(label="Descuento (%)"),
        "rating": ft.TextField(label="Rating"),
        "rating_count": ft.TextField(label="Cantidad valoraciones"),
        "about_product": ft.TextField(label="Descripción", multiline=True, min_lines=2, width=500),
        "img_link": ft.TextField(label="URL imagen", width=500),
        "product_link": ft.TextField(label="URL producto", width=500),
    }

    new_username = ft.TextField(label="Usuario")
    new_password = ft.TextField(label="Contraseña")
    new_role = ft.Dropdown(label="Rol", options=[ft.dropdown.Option("admin"), ft.dropdown.Option("employee")], value="employee")

    def toast(msg):
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    def selected_product():
        pid = product_dd.value
        return next((p for p in state["products"] if p["product_id"] == pid), None)

    def refresh_products():
        filters = {
            "category": category_dd.value,
            "discount_min": discount_min.value,
            "discount_max": discount_max.value,
            "rating_min": rating_min.value,
            "rating_count_min": rating_count_min.value,
            "name": name_search.value,
        }
        state["products"] = get_products(filters)
        product_dd.options = [ft.dropdown.Option(key=p["product_id"], text=p["product_name"]) for p in state["products"]]
        product_dd.value = None
        details.value = ""
        reviews_col.controls.clear()
        product_image.src = ""
        state["selected"] = None
        page.update()

    def refresh_categories():
        category_dd.options = [ft.dropdown.Option(text=c) for c in get_categories()]

    def render_reviews():
        reviews_col.controls.clear()
        p = selected_product()
        if not p:
            return
        data = get_reviews(p["product_id"], include_blocked=current_user["data"]["role"] == "admin")
        for r in data:
            lines = [
                ft.Text(f"Título: {r['review_title'] or '(sin título)'}", weight=ft.FontWeight.BOLD),
                ft.Text(f"Usuario: {r['reviewer_name'] or 'N/A'}"),
                ft.Text(r["review_content"] or ""),
            ]
            if current_user["data"]["role"] == "admin" and not r["blocked"]:
                lines.append(ft.ElevatedButton("Bloquear comentario", on_click=lambda e, rid=r["review_id"]: block_and_refresh(rid)))
            if r["blocked"]:
                lines.append(ft.Text("(BLOQUEADO)", color=ft.Colors.RED))
            reviews_col.controls.append(ft.Container(ft.Column(lines), border=ft.border.all(1, ft.Colors.GREY_300), padding=8, border_radius=8))

    def show_details(e=None):
        p = selected_product()
        state["selected"] = p
        if not p:
            return
        details.value = (
            f"ID: {p['product_id']}\n"
            f"Nombre: {p['product_name']}\n"
            f"Categoría(s): {p['category_raw']}\n"
            f"Precio real: {p['actual_price']}\n"
            f"Precio descuento: {p['discounted_price']}\n"
            f"Descuento (%): {p['discount_percentage']}\n"
            f"Rating: {p['rating']}\n"
            f"Cantidad valoraciones: {p['rating_count']}\n"
            f"Descripción: {p['about_product']}\n"
            f"Link: {p['product_link']}"
        )
        product_image.src = p["img_link"] or ""
        edit_name.value = p["product_name"] or ""
        edit_discounted.value = str(p["discounted_price"] or "")
        edit_rating.value = str(p["rating"] or "")
        render_reviews()
        page.update()

    def block_and_refresh(review_id):
        block_review(review_id)
        render_reviews()
        page.update()

    def save_observation(e):
        p = selected_product()
        if not p:
            return toast("Selecciona un producto")
        if not observation.value.strip():
            return toast("Escribe una observación")
        add_observation(p["product_id"], observation.value.strip())
        observation.value = ""
        toast("Observación guardada en DB")

    def employee_save(e):
        p = selected_product()
        if not p:
            return toast("Selecciona un producto")
        updates = {}
        if edit_name.value.strip() and edit_name.value.strip() != (p["product_name"] or ""):
            updates["product_name"] = edit_name.value.strip()
        if edit_discounted.value.strip() and parse_float(edit_discounted.value) != float(p["discounted_price"] or 0):
            updates["discounted_price"] = parse_float(edit_discounted.value)
        if edit_rating.value.strip() and parse_float(edit_rating.value) != float(p["rating"] or 0):
            updates["rating"] = parse_float(edit_rating.value)

        if not updates:
            return toast("No hay cambios")
        update_product(p["product_id"], updates, current_user["data"]["id"])
        refresh_products()
        toast("Producto actualizado y registrado en logs")

    def draw_chart(kind):
        p = selected_product()
        if kind == "rating":
            chart_image.src = chart_rating_by_category()
        elif kind == "discount":
            chart_image.src = chart_discount_by_category()
        elif kind == "price":
            if not p:
                return toast("Selecciona un producto para comparación de precios")
            chart_image.src = chart_price_comparison(p["product_id"])
        elif kind == "count":
            chart_image.src = chart_rating_count_by_category()
        page.update()

    def clear_filters(e):
        category_dd.value = None
        discount_min.value = ""
        discount_max.value = ""
        rating_min.value = ""
        rating_count_min.value = ""
        name_search.value = ""
        refresh_products()

    def clear_screen(e):
        product_dd.value = None
        details.value = ""
        product_image.src = ""
        chart_image.src = ""
        observation.value = ""
        reviews_col.controls.clear()
        state["selected"] = None
        page.update()

    def load_users_ui():
        users_col.controls.clear()
        for u in list_users():
            users_col.controls.append(ft.Text(f"{u['username']} ({u['role']})"))

    def load_logs_ui():
        logs_col.controls.clear()
        for lg in list_logs():
            stamp = lg["changed_at"].strftime("%Y-%m-%d %H:%M") if isinstance(lg["changed_at"], datetime) else str(lg["changed_at"])
            logs_col.controls.append(ft.Text(f"{stamp} | {lg['username']} | {lg['product_id']} | {lg['changed_fields']}"))

    def admin_add_user(e):
        if not (new_username.value.strip() and new_password.value.strip() and new_role.value):
            return toast("Completa usuario, contraseña y rol")
        try:
            add_user(new_username.value.strip(), new_password.value.strip(), new_role.value)
        except Exception as ex:
            return toast(f"Error agregando usuario: {ex}")
        new_username.value = ""
        new_password.value = ""
        load_users_ui()
        toast("Usuario creado")

    def admin_add_product(e):
        payload = {k: v.value.strip() for k, v in add_fields.items()}
        if not payload["product_id"] or not payload["product_name"]:
            return toast("ID y nombre son obligatorios")
        try:
            add_product(payload)
        except Exception as ex:
            return toast(f"Error agregando producto: {ex}")
        refresh_categories()
        refresh_products()
        toast("Producto agregado")

    def build_dashboard():
        refresh_categories()
        refresh_products()
        load_users_ui()
        load_logs_ui()

        for control in [category_dd, discount_min, discount_max, rating_min, rating_count_min, name_search]:
            control.on_change = lambda e: refresh_products()
        product_dd.on_change = show_details

        filters_row = ft.Row(
            [
                category_dd,
                discount_min,
                discount_max,
                rating_min,
                rating_count_min,
                name_search,
                ft.ElevatedButton("Limpiar filtros", on_click=clear_filters),
            ],
            wrap=True,
        )

        charts_row = ft.Row(
            [
                ft.ElevatedButton("Rating por categoría", on_click=lambda e: draw_chart("rating")),
                ft.ElevatedButton("Descuento por categoría", on_click=lambda e: draw_chart("discount")),
                ft.ElevatedButton("Comparación precios", on_click=lambda e: draw_chart("price")),
                ft.ElevatedButton("Valoraciones por categoría", on_click=lambda e: draw_chart("count")),
            ],
            wrap=True,
        )

        general_tab = ft.Tab(
            text="General",
            content=ft.Column(
                [
                    ft.Text("Dashboard Amazon", size=24, weight=ft.FontWeight.BOLD),
                    filters_row,
                    product_dd,
                    ft.Row([details, product_image]),
                    ft.Text("Reseñas"),
                    reviews_col,
                    ft.Row([observation, ft.ElevatedButton("Guardar observación", on_click=save_observation)]),
                    ft.Row([ft.ElevatedButton("Limpiar pantalla", on_click=clear_screen)]),
                    charts_row,
                    chart_image,
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        )

        employee_tab = ft.Tab(
            text="Empleado",
            content=ft.Column(
                [
                    ft.Text("Editar producto (solo empleado)", size=20),
                    edit_name,
                    edit_discounted,
                    edit_rating,
                    ft.ElevatedButton("Guardar cambios", on_click=employee_save),
                    ft.Divider(),
                    ft.Text("Logs de cambios", size=20),
                    logs_col,
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        )

        admin_tab = ft.Tab(
            text="Admin",
            content=ft.Column(
                [
                    ft.Text("Agregar producto", size=20),
                    ft.Row([add_fields["product_id"], add_fields["product_name"]], wrap=True),
                    add_fields["category"],
                    ft.Row([add_fields["discounted_price"], add_fields["actual_price"], add_fields["discount_percentage"]], wrap=True),
                    ft.Row([add_fields["rating"], add_fields["rating_count"]], wrap=True),
                    add_fields["about_product"],
                    add_fields["img_link"],
                    add_fields["product_link"],
                    ft.ElevatedButton("Agregar producto", on_click=admin_add_product),
                    ft.Divider(),
                    ft.Text("Gestionar usuarios", size=20),
                    users_col,
                    ft.Row([new_username, new_password, new_role, ft.ElevatedButton("Agregar usuario", on_click=admin_add_user)], wrap=True),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
        )

        tabs = [general_tab]
        if current_user["data"]["role"] == "employee":
            tabs.append(employee_tab)
        if current_user["data"]["role"] == "admin":
            tabs.append(admin_tab)

        page.controls.clear()
        page.add(ft.Tabs(selected_index=0, tabs=tabs, expand=1))
        page.update()

    def do_login(e):
        conn = db_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username.value.strip(), password.value.strip()),
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if not user:
            login_msg.value = "Credenciales inválidas"
            page.update()
            return
        current_user["data"] = user
        build_dashboard()

    login_view = ft.Column(
        [
            ft.Text("Inicio de sesión", size=30, weight=ft.FontWeight.BOLD),
            username,
            password,
            ft.ElevatedButton("Ingresar", on_click=do_login),
            login_msg,
            ft.Text("Usuarios iniciales: admin/admin y employee/employee", color=ft.Colors.GREY_700),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    page.add(login_view)


ft.app(target=main)
