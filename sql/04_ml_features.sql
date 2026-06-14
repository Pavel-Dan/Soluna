-- Couche ML : jeu de données pour le modèle anti-churn
CREATE SCHEMA IF NOT EXISTS ml;
DROP TABLE IF EXISTS ml.churn_dataset;

CREATE TABLE ml.churn_dataset AS
WITH o AS (
  SELECT user_id, order_number, days_since_prior_order,
         max(order_number) OVER (PARTITION BY user_id) AS last_no
  FROM raw.orders
),
hist AS (   -- on exclut la toute dernière commande (elle sert de cible)
  SELECT user_id,
         count(*)                                        AS nb_commandes,
         avg(days_since_prior_order)                     AS cadence_moy,
         coalesce(stddev_pop(days_since_prior_order), 0) AS cadence_std,
         max(days_since_prior_order)                     AS cadence_max,
         min(days_since_prior_order)                     AS cadence_min
  FROM o
  WHERE order_number < last_no
    AND days_since_prior_order IS NOT NULL
  GROUP BY user_id
),
cible AS (   -- l'écart avant la dernière commande = signal de décrochage
  SELECT user_id, days_since_prior_order AS dernier_ecart
  FROM o
  WHERE order_number = last_no
)
SELECT h.user_id,
       h.nb_commandes,
       round(h.cadence_moy::numeric, 2) AS cadence_moy,
       round(h.cadence_std::numeric, 2) AS cadence_std,
       h.cadence_max,
       h.cadence_min,
       CASE WHEN c.dernier_ecart >= 30 THEN 1 ELSE 0 END AS churn
FROM hist h
JOIN cible c USING (user_id)
WHERE h.nb_commandes >= 2;