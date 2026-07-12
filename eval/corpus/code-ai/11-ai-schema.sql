-- ============================================
-- Database Schema for E-Commerce Application
-- ============================================
-- This script creates the core tables for the application.
-- You can customize the column types as needed for your database engine.

-- Step 1: Create the users table
-- This table stores the customer account information
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    -- The user's email address (must be unique)
    email VARCHAR(255) UNIQUE NOT NULL,
    -- The hashed password (never store plain text passwords!)
    password_hash VARCHAR(255) NOT NULL,
    -- The timestamp when the account was created
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 2: Create the products table
-- This table stores the product catalog
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    -- The name of the product
    name VARCHAR(255) NOT NULL,
    -- A detailed description of the product
    description TEXT,
    -- The price in cents to avoid floating point issues
    price_cents INTEGER NOT NULL,
    -- The current stock quantity
    stock_quantity INTEGER DEFAULT 0
);

-- Step 3: Create the orders table
-- This table stores the order records
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    -- Reference to the user who placed the order
    user_id INTEGER REFERENCES users(id),
    -- The current status of the order
    status VARCHAR(50) DEFAULT 'pending',
    -- The timestamp when the order was placed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 4: Create the order items table
-- This is a junction table linking orders to products
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    -- Reference to the parent order
    order_id INTEGER REFERENCES orders(id),
    -- Reference to the ordered product
    product_id INTEGER REFERENCES products(id),
    -- The quantity of this product in the order
    quantity INTEGER NOT NULL,
    -- The price at the time of purchase
    unit_price_cents INTEGER NOT NULL
);

-- Finally, we create indexes to improve query performance
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
