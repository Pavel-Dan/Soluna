-- Couche STREAM : indicateurs temps réel par client
CREATE SCHEMA IF NOT EXISTS stream;

CREATE TABLE IF NOT EXISTS stream.client_features (
  user_id int PRIMARY KEY,
  nb_commandes int NOT NULL DEFAULT 0,
  derniere_order_number int,
  somme_jours numeric NOT NULL DEFAULT 0,
  nb_intervalles int NOT NULL DEFAULT 0,
  derniere_maj timestamptz
);

CREATE TABLE IF NOT EXISTS stream.evenements_invalides (
  id serial PRIMARY KEY,
  recu_le timestamptz DEFAULT now(),
  raison text,
  contenu text
);

CREATE OR REPLACE VIEW stream.client_cadence AS
SELECT user_id, nb_commandes, derniere_order_number,
       round(somme_jours / NULLIF(nb_intervalles, 0), 1) AS cadence_moy_jours,
       derniere_maj
FROM stream.client_features;