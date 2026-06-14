-- Couche MART : schéma en étoile pour l'analyse
CREATE SCHEMA IF NOT EXISTS mart;
DROP TABLE IF EXISTS mart.fait_commande_produit, mart.dim_produit,
  mart.dim_client, mart.dim_temps CASCADE;

-- Dimension Produit (dénormalisée : produit + rayon + département)
CREATE TABLE mart.dim_produit AS
SELECT p.product_id, p.product_name AS nom_produit,
       a.aisle AS rayon, d.department AS departement
FROM raw.products p
LEFT JOIN raw.aisles a       ON a.aisle_id = p.aisle_id
LEFT JOIN raw.departments d  ON d.department_id = p.department_id;
ALTER TABLE mart.dim_produit ADD PRIMARY KEY (product_id);

-- Dimension Client (abonné) avec attributs dérivés
CREATE TABLE mart.dim_client AS
SELECT o.user_id,
       count(*) AS nb_commandes,
       round(avg(o.days_since_prior_order)::numeric, 1) AS cadence_moy_jours
FROM raw.orders o
GROUP BY o.user_id;
ALTER TABLE mart.dim_client ADD PRIMARY KEY (user_id);

-- Dimension Temps
CREATE TABLE mart.dim_temps AS
SELECT DISTINCT
  (order_dow*100 + order_hour_of_day) AS id_temps,
  order_dow AS jour_semaine,
  order_hour_of_day AS heure,
  CASE WHEN order_hour_of_day BETWEEN 5 AND 11  THEN 'Matin'
       WHEN order_hour_of_day BETWEEN 12 AND 17 THEN 'Après-midi'
       WHEN order_hour_of_day BETWEEN 18 AND 22 THEN 'Soir'
       ELSE 'Nuit' END AS moment_journee
FROM raw.orders;
ALTER TABLE mart.dim_temps ADD PRIMARY KEY (id_temps);

-- Table de faits : 1 ligne = 1 produit acheté dans une commande
CREATE TABLE mart.fait_commande_produit AS
SELECT op.order_id, o.user_id, op.product_id,
       (o.order_dow*100 + o.order_hour_of_day) AS id_temps,
       o.order_number, o.days_since_prior_order,
       op.add_to_cart_order, op.reordered
FROM (
  SELECT order_id, product_id, add_to_cart_order, reordered FROM raw.order_products_prior
  UNION ALL
  SELECT order_id, product_id, add_to_cart_order, reordered FROM raw.order_products_train
) op
JOIN raw.orders o ON o.order_id = op.order_id;

-- Vérifications
SELECT count(*) AS lignes_table_de_faits FROM mart.fait_commande_produit;

SELECT p.nom_produit, p.rayon, count(*) AS nb_achats,
       round(avg(f.reordered)*100, 1) AS taux_reachat_pct
FROM mart.fait_commande_produit f
JOIN mart.dim_produit p ON p.product_id = f.product_id
GROUP BY p.nom_produit, p.rayon
ORDER BY nb_achats DESC
LIMIT 10;