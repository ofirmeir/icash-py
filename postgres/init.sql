CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- products must exist before purchase_items
CREATE TABLE IF NOT EXISTS products (
  id SERIAL PRIMARY KEY,
  product_name TEXT UNIQUE NOT NULL,
  unit_price NUMERIC NOT NULL
);

-- users table: sequential PK for indexing, and a DB-generated uuid value
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  uuid UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS purchases (
  id SERIAL PRIMARY KEY,
  supermarket_id TEXT NOT NULL REFERENCES stores(supermarket_id),
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  user_id INTEGER NOT NULL REFERENCES users(id),
  total_amount NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS purchase_items (
  id SERIAL PRIMARY KEY,
  purchase_id INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
  product_id INTEGER NOT NULL REFERENCES products(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  total_purchases INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS stores (
  id SERIAL PRIMARY KEY,
  supermarket_id TEXT UNIQUE NOT NULL
);