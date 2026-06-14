#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Soluna - chargement de l'entrepot et construction des couches de donnees.
# Prerequis : Docker Desktop lance + `docker compose up -d` (service warehouse).
# Usage     : depuis la racine du depot ->  bash scripts/load_data.sh
# ---------------------------------------------------------------------------
set -euo pipefail

PSQL="docker compose exec -T warehouse psql -U soluna -d soluna"

echo "==> 1/4  Couche raw (init.sql) : tables sources + chargement des CSV"
$PSQL < sql/init.sql

echo "==> 2/4  Couche mart (02_star.sql) : schema en etoile"
$PSQL < sql/02_star.sql

echo "==> 3/4  Couche stream (03_stream.sql) : agregats temps reel"
$PSQL < sql/03_stream.sql

echo "==> 4/4  Features ML (04_ml_features.sql) : jeu d'apprentissage churn"
$PSQL < sql/04_ml_features.sql

echo "==> Termine. Entrepot pret (raw -> mart -> stream -> ml)."
