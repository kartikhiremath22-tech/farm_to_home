-- Run this file in MySQL to set up the database
-- Command: mysql -u root -p < database.sql

CREATE DATABASE IF NOT EXISTS farm_to_home;
USE farm_to_home;

-- Users table (both farmers and buyers)
CREATE TABLE IF NOT EXISTS users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100)  NOT NULL,
    email      VARCHAR(100)  NOT NULL UNIQUE,
    password   VARCHAR(100)  NOT NULL,
    role       ENUM('farmer','buyer') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table (listed by farmers)
CREATE TABLE IF NOT EXISTS products (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    farmer_id  INT NOT NULL,
    name       VARCHAR(100) NOT NULL,
    price      DECIMAL(10,2) NOT NULL,
    quantity   INT NOT NULL,
    location   VARCHAR(150),
    category   VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (farmer_id) REFERENCES users(id)
);

-- Orders table (placed by buyers)
CREATE TABLE IF NOT EXISTS orders (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    buyer_id    INT NOT NULL,
    product_id  INT NOT NULL,
    quantity    INT NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    status      ENUM('pending','confirmed','delivered') DEFAULT 'pending',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (buyer_id)   REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Sample data to test with
INSERT INTO users (name, email, password, role) VALUES
('Raju Kumar',   'raju@farm.com',  'raju123',  'farmer'),
('Priya Devi',   'priya@farm.com', 'priya123', 'farmer'),
('Ankit Sharma', 'ankit@buy.com',  'ankit123', 'buyer');

INSERT INTO products (farmer_id, name, price, quantity, location, category) VALUES
(1, 'Tomatoes',   45.00, 800,  'Hassan, Karnataka',    'Vegetables'),
(1, 'Potatoes',   22.00, 1200, 'Hassan, Karnataka',    'Vegetables'),
(2, 'Broccoli',   80.00, 200,  'Coimbatore, Tamil Nadu','Vegetables'),
(2, 'Mangoes',   120.00, 300,  'Coimbatore, Tamil Nadu','Fruits');
