# Soluna — Plateforme Data & IA

Projet fil rouge d'une marque **fictive**, *Soluna* (compléments alimentaires personnalisés par abonnement).
Objectif transverse : **transformer l'achat d'impulsion en abonnement durable** — c'est-à-dire piloter la rétention (anti-churn).

> **Données.** L'historique de commandes s'appuie sur le jeu **Instacart Market Basket Analysis** (Kaggle),
> utilisé comme **proxy réel** de la cadence de réachat. Le quiz de bien-être est **simulé**. Soluna est une entité fictive.

## Architecture du dépôt

| Dossier | Contenu | Bloc |
|---|---|---|
| `sql/` | `init.sql` (couche raw), `02_star.sql` (schéma en étoile), `03_stream.sql`, `04_ml_features.sql` | 2-4 |
| `python/` | `producer.py` / `consumer.py` — pipeline temps réel Kafka | 3 |
| `dags/` | `soluna_pipeline.py` — orchestration Airflow (qualité + segmentation) | 3 |
| `src/` | `train.py` — entraînement du modèle anti-churn | 4 |
| `api/` | `main.py` (FastAPI) + `logic.py` — serving des prédictions | 4 |
| `retrain/` | `retrain.py` — réentraînement champion/challenger + journal | 4 |
| `monitoring/` | `drift_check.py` — surveillance de dérive (PSI) | 4 |
| `tests/` | tests unitaires (logique métier + cohérence du modèle) | 4 |
| `models/` | `metrics.json`, `features.json` (le modèle `.joblib` se régénère) | 4 |
| `.github/workflows/` | `ci.yml` (tests) + `retrain.yml` (réentraînement planifié) | 4 |
| `docker-compose.yml`, `Dockerfile`, `requirements.txt` | infrastructure & dépendances | 2-4 |

## Démarrage rapide

```bash
# 1. Entrepôt + outils (PostgreSQL, Adminer, Kafka, Airflow)
docker compose up -d

# 2. Charger les données (raw -> mart -> stream -> ml)
docker compose exec -T warehouse psql -U soluna -d soluna < sql/init.sql
docker compose exec -T warehouse psql -U soluna -d soluna < sql/02_star.sql
docker compose exec -T warehouse psql -U soluna -d soluna < sql/03_stream.sql
docker compose exec -T warehouse psql -U soluna -d soluna < sql/04_ml_features.sql

# 3. Pipeline temps réel (deux terminaux)
python python/producer.py
python python/consumer.py

# 4. Modèle anti-churn
python src/train.py

# 5. API de serving
uvicorn api.main:app --port 8000      # ou : docker build -t soluna-api . && docker run -p 8000:8000 soluna-api
# -> http://localhost:8000/docs

# 6. Tests, réentraînement, monitoring
python -m pytest -v
python retrain/retrain.py
python monitoring/drift_check.py
```

## Modèle anti-churn (Bloc 4)
- **Cible** : `churn = 1` si l'écart depuis la dernière commande ≥ 30 jours.
- **Modèle** : RandomForest + SMOTE (classe minoritaire ~30 %).
- **Performance** : AUC ≈ 0,70 ; rappel sur « à risque » ≈ 0,53 (modèle volontairement simple et explicable).
- **Industrialisation** : API FastAPI + Docker, CI/CD GitHub Actions, réentraînement champion/challenger planifié, monitoring de dérive (PSI).

## Stack
PostgreSQL · Docker / docker-compose · Apache Kafka · Apache Airflow · Python (scikit-learn, imbalanced-learn, FastAPI) · GitHub Actions.
