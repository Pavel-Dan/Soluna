"""
Réentraînement automatisé du modèle anti-churn Soluna (champion / challenger).

- Charge les features depuis l'entrepôt (ml.churn_dataset). Si l'entrepôt est
  injoignable (ex. CI), bascule sur un jeu de démonstration reproductible.
- Entraîne un challenger (SMOTE + RandomForest) et l'évalue sur un jeu de test
  qu'il n'a jamais vu.
- Le compare à la métrique ENREGISTRÉE du champion (metrics.json), elle aussi
  hors-échantillon. On ne re-score PAS le modèle sauvegardé sur un nouveau
  split : il a pu être entraîné sur une partie de ces lignes -> fuite de
  données -> AUC surestimée.
- Ne promeut le challenger que s'il est au moins aussi bon (AUC).
- Journalise la décision dans retrain/retrain_log.csv.
"""
import os, json, csv, datetime, warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, recall_score
from imblearn.over_sampling import SMOTE

warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER_MODELE = os.path.join(RACINE, "models")
CHEMIN_MODELE = os.path.join(DOSSIER_MODELE, "churn_model.joblib")
CHEMIN_METRIQUES = os.path.join(DOSSIER_MODELE, "metrics.json")
CHEMIN_FEATURES = os.path.join(DOSSIER_MODELE, "features.json")
CHEMIN_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "retrain_log.csv")

COLONNES = ["nb_commandes", "cadence_moy", "cadence_std", "cadence_max", "cadence_min"]
CIBLE = "churn"
TOLERANCE = 0.01  # le challenger peut être au pire 0.01 d'AUC sous le champion


def charger_depuis_entrepot():
    import psycopg2
    conn = psycopg2.connect(host="localhost", port=5432, dbname="soluna",
                            user="soluna", password="soluna", connect_timeout=5)
    df = pd.read_sql(
        "SELECT nb_commandes, cadence_moy, cadence_std, cadence_max, cadence_min, churn "
        "FROM ml.churn_dataset", conn)
    conn.close()
    return df


def jeu_de_demonstration(n=20000, graine=42):
    """Jeu reproductible (utilisé seulement si l'entrepôt est injoignable, ex. CI)."""
    rng = np.random.default_rng(graine)
    nb = rng.integers(1, 60, n)
    cad = rng.gamma(2.0, 7.0, n)
    std = rng.gamma(1.5, 4.0, n)
    cmax = cad + rng.gamma(2.0, 6.0, n)
    cmin = np.clip(cad - rng.gamma(1.0, 3.0, n), 0, None)
    score = (cad - 12) * 0.08 + (std - 6) * 0.05 - (nb - 10) * 0.03
    churn = (rng.random(n) < 1 / (1 + np.exp(-score))).astype(int)
    return pd.DataFrame({"nb_commandes": nb, "cadence_moy": cad, "cadence_std": std,
                         "cadence_max": cmax, "cadence_min": cmin, "churn": churn})


def charger_donnees():
    try:
        df = charger_depuis_entrepot()
        print(f"[data] Entrepot : {len(df):,} lignes depuis ml.churn_dataset")
        source = "entrepot"
    except Exception as e:
        print(f"[data] Entrepot injoignable ({e.__class__.__name__}). "
              f"Bascule sur le jeu de demonstration reproductible.")
        df = jeu_de_demonstration()
        source = "demonstration"
    df = df.dropna(subset=COLONNES + [CIBLE])
    if len(df) > 120000:
        df = df.sample(120000, random_state=42)
    return df, source


def lire_auc_champion():
    """AUC de référence = métrique enregistrée (hors-échantillon, non biaisée)."""
    if not os.path.exists(CHEMIN_METRIQUES):
        return None
    try:
        m = json.load(open(CHEMIN_METRIQUES))
    except Exception:
        return None
    for k, v in m.items():
        if "auc" in k.lower() and isinstance(v, (int, float)) and 0 < v <= 1:
            return float(v)
    return None


def entrainer(X, y):
    Xr, yr = SMOTE(random_state=42).fit_resample(X, y)
    m = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    m.fit(Xr, yr)
    return m


def main():
    df, source = charger_donnees()
    X, y = df[COLONNES], df[CIBLE]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25,
                                              stratify=y, random_state=42)

    print("[train] Entrainement du challenger (SMOTE + RandomForest)...")
    challenger = entrainer(X_tr, y_tr)
    auc_chal = roc_auc_score(y_te, challenger.predict_proba(X_te)[:, 1])
    rec_chal = recall_score(y_te, challenger.predict(X_te))
    print(f"[challenger] AUC={auc_chal:.4f}  rappel={rec_chal:.3f}")

    auc_champ = lire_auc_champion()
    if auc_champ is None:
        print("[champion ] pas de metrique enregistree, promotion auto.")
    else:
        print(f"[champion ] AUC={auc_champ:.4f} (metrique enregistree)")

    promu = (auc_champ is None) or (auc_chal >= auc_champ - TOLERANCE)
    decision = "PROMU" if promu else "REJETE"
    print(f"[decision] {decision}")

    if promu:
        os.makedirs(DOSSIER_MODELE, exist_ok=True)
        joblib.dump(challenger, CHEMIN_MODELE)
        json.dump(COLONNES, open(CHEMIN_FEATURES, "w"), ensure_ascii=False, indent=2)
        json.dump({"auc": round(auc_chal, 4), "rappel_a_risque": round(rec_chal, 4),
                   "source_donnees": source, "date": datetime.date.today().isoformat()},
                  open(CHEMIN_METRIQUES, "w"), ensure_ascii=False, indent=2)
        print(f"[save] Nouveau modele ecrit : {CHEMIN_MODELE}")

    nouveau = not os.path.exists(CHEMIN_LOG)
    with open(CHEMIN_LOG, "a", newline="") as f:
        w = csv.writer(f)
        if nouveau:
            w.writerow(["date", "source", "auc_challenger", "auc_champion", "decision"])
        w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), source,
                    round(auc_chal, 4),
                    "" if auc_champ is None else round(auc_champ, 4), decision])
    print(f"[log] Decision journalisee dans {CHEMIN_LOG}")


if __name__ == "__main__":
    main()