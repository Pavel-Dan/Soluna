-- Couche RAW : copie fidèle des fichiers sources Instacart
CREATE SCHEMA IF NOT EXISTS raw;

DROP TABLE IF EXISTS raw.aisles, raw.departments, raw.products,
  raw.orders, raw.order_products_prior, raw.order_products_train CASCADE;

CREATE TABLE raw.aisles      (aisle_id int, aisle text);
CREATE TABLE raw.departments (department_id int, department text);
CREATE TABLE raw.products    (product_id int, product_name text, aisle_id int, department_id int);
CREATE TABLE raw.orders (
  order_id int, user_id int, eval_set text, order_number int,
  order_dow int, order_hour_of_day int, days_since_prior_order numeric
);
CREATE TABLE raw.order_products_prior (order_id int, product_id int, add_to_cart_order int, reordered int);
CREATE TABLE raw.order_products_train (order_id int, product_id int, add_to_cart_order int, reordered int);

COPY raw.aisles               FROM '/data/aisles.csv'                CSV HEADER;
COPY raw.departments          FROM '/data/departments.csv'           CSV HEADER;
COPY raw.products             FROM '/data/products.csv'              CSV HEADER;
COPY raw.orders               FROM '/data/orders.csv'                CSV HEADER;
COPY raw.order_products_prior FROM '/data/order_products__prior.csv' CSV HEADER;
COPY raw.order_products_train FROM '/data/order_products__train.csv' CSV HEADER;