-- Crear base de datos
CREATE DATABASE IF NOT EXISTS amazon_dashboard;

USE amazon_dashboard;

-- Tabla productos
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
);

-- Tabla reviews
CREATE TABLE IF NOT EXISTS reviews (
    review_id VARCHAR(255) PRIMARY KEY,
    product_id VARCHAR(255),
    user_id VARCHAR(255),
    user_name TEXT,
    review_title TEXT,
    review_content TEXT,
    FOREIGN KEY (product_id) REFERENCES productos(product_id)
);

-- Tabla system_users
CREATE TABLE IF NOT EXISTS system_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE,
    password VARCHAR(255),
    role ENUM('admin', 'employee')
);

-- Insertar usuarios por defecto
INSERT IGNORE INTO system_users (username, password, role) VALUES ('admin', 'admin', 'admin');
INSERT IGNORE INTO system_users (username, password, role) VALUES ('employee', 'employee', 'employee');

-- Tabla logs
CREATE TABLE IF NOT EXISTS logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT,
    product_id VARCHAR(255),
    change_description TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES system_users(id),
    FOREIGN KEY (product_id) REFERENCES productos(product_id)
);

-- Tabla blocked_reviews
CREATE TABLE IF NOT EXISTS blocked_reviews (
    review_id VARCHAR(255) PRIMARY KEY,
    FOREIGN KEY (review_id) REFERENCES reviews(review_id)
);