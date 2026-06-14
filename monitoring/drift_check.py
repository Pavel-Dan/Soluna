"""
Surveillance de derive (data drift) du modele anti-churn Soluna.

Mesure le Population Stability Index (PSI) entre une distribution de REFERENCE
(donnees d'entrainement) et un lot de PRODUCTION recent, variable par variable.

Lecture du PSI :
  PSI < 0.10  -> population stable
  0.10 - 0.25 -> derive moderee (a surveiller)
  PSI > 0.25  -> derive forte (reentrainement conseille)

En production on brancherait un outil dedie (Evidently, Aporia) sur le flux
reel ; ici on calcule le PSI nous-memes pour la transparence. Faute de vrai
flux, le lot "courant" est simule a partir des donnees reelles avec une derive
controlee et DECLAREE (cadence de commande +30%).
"""
import os, json, datetime, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")

ICI = os.path.dirname(os.path.abspath(__file__))
CHEMIN_RAPPORT = os.path.join(ICI, "drift_report.json")
COLONNES = ["nb_commandes", "cadence_moy", "cadence_std", "cadence_max", "cadence_min"]
SEUIL_MODERE, SEUIL_FORT = 0.10, 0.25


def charger_reference():
    try:
        import psycopg2
        conn = psycopg2.connect(host="localhost", port=5432, dbname="soluna",
                                user="soluna", password="soluna", connect_timeout=5)
        df = pd.read_sql(f"SELECT {', '.join(COLONNES)} FROM ml.churn_dataset", conn)
        conn.close()
        print(f"[ref ] {len(df):,} lignes de reference depuis ml.churn_dataset")
        return df.sample(50000, random_state=42) if len(df) > 50000 else df
    except Exception as e:
        print(f"[ref ] Entrepot injoignable ({e.__class__.__name__}), jeu reproductible.")
        rng = np.random.default_rng(42); n = 20000
        return pd.DataFrame({
            "nb_commandes": rng.integers(1, 60, n), "cadence_moy": rng.gamma(2.0, 7.0, n),
            "cadence_std": rng.gamma(1.5, 4.0, n), "cadence_max": rng.gamma(2.0, 10.0, n),
            "cadence_min": rng.gamma(1.0, 3.0, n)})


def simuler_lot_production(reference, facteur=1.30, graine=7):
    """Lot 'courant' = echantillon de la reference avec derive controlee (declaree)
    sur la cadence : clients qui espacent leurs commandes -> signal d'alerte."""
    cur = reference.sample(frac=0.5, random_state=graine).copy()
    cur["cadence_moy"] *= facteur
    cur["cadence_max"] *= facteur
    return cur


def psi(ref, cur, n_bins=10):
    """PSI entre deux series continues, via les deciles de la reference."""
    bornes = np.unique(np.quantile(ref, np.linspace(0, 1, n_bins + 1)))
    if len(bornes) < 3:
        return 0.0
    bornes[0], bornes[-1] = -np.inf, np.inf
    ref_p = np.clip(np.histogram(ref, bins=bornes)[0] / len(ref), 1e-6, None)
    cur_p = np.clip(np.histogram(cur, bins=bornes)[0] / len(cur), 1e-6, None)
    return float(np.sum((cur_p - ref_p) * np.log(cur_p / ref_p)))


def etiqueter(v):
    return "FORTE" if v > SEUIL_FORT else ("moderee" if v > SEUIL_MODERE else "stable")


def main():
    ref = charger_reference()
    cur = simuler_lot_production(ref)
    print(f"[prod] {len(cur):,} lignes (lot de production simule, derive +30% cadence)\n")
    print(f"{'variable':<16}{'PSI':>8}   etat")
    print("-" * 40)

    resultats, global_ = {}, "stable"
    for col in COLONNES:
        v = psi(ref[col].values, cur[col].values)
        etat = etiqueter(v)
        resultats[col] = {"psi": round(v, 4), "etat": etat}
        print(f"{col:<16}{v:>8.4f}   {etat}")
        if etat == "FORTE":
            global_ = "FORTE"
        elif etat == "moderee" and global_ == "stable":
            global_ = "moderee"

    reco = {"stable": "Aucune action.", "moderee": "Surveiller ; planifier un controle.",
            "FORTE": "Reentrainement conseille."}[global_]
    print("-" * 40)
    print(f"[bilan] derive globale : {global_} -> {reco}")

    json.dump({"date": datetime.datetime.now().isoformat(timespec="seconds"),
               "seuils": {"modere": SEUIL_MODERE, "fort": SEUIL_FORT},
               "variables": resultats, "derive_globale": global_, "recommandation": reco},
              open(CHEMIN_RAPPORT, "w"), ensure_ascii=False, indent=2)
    print(f"[save] Rapport ecrit : {CHEMIN_RAPPORT}")


if __name__ == "__main__":
    main()