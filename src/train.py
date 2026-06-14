import os, json, joblib
import pandas as pd
import psycopg2
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix, recall_score
from imblearn.over_sampling import SMOTE

FEATURES = ["nb_commandes", "cadence_moy", "cadence_std", "cadence_max", "cadence_min"]

# 1. Charger les donnees
conn = psycopg2.connect(host="localhost", port=5432, dbname="soluna",
                        user="soluna", password="soluna")
df = pd.read_sql("SELECT nb_commandes, cadence_moy, cadence_std, cadence_max, "
                 "cadence_min, churn FROM ml.churn_dataset", conn)
conn.close()
print(f"Donnees : {len(df)} clients, taux de churn = {df.churn.mean():.3f}")

if len(df) > 100000:
    df = df.sample(100000, random_state=42)

X, y = df[FEATURES], df["churn"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, stratify=y, random_state=42)

# 2. Modele de reference (sans reequilibrage)
base = RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=42).fit(X_train, y_train)
rappel_base = recall_score(y_test, base.predict(X_test))

# 3. Reequilibrage SMOTE sur l'entrainement, puis modele final
X_res, y_res = SMOTE(random_state=42).fit_resample(X_train, y_train)
model = RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=42).fit(X_res, y_res)

# 4. Evaluation sur le test (jamais reequilibre)
pred = model.predict(X_test)
proba = model.predict_proba(X_test)[:, 1]
print("\n=== Modele anti-churn (avec SMOTE) ===")
print(classification_report(y_test, pred, target_names=["fidele", "a risque"]))
print(f"AUC ROC            : {roc_auc_score(y_test, proba):.3f}")
print(f"Rappel 'a risque'  : {recall_score(y_test, pred):.3f}  (vs {rappel_base:.3f} sans SMOTE)")
print("Matrice de confusion :\n", confusion_matrix(y_test, pred))

# 5. Sauvegarde
os.makedirs("models", exist_ok=True)
joblib.dump(model, "models/churn_model.joblib")
json.dump(FEATURES, open("models/features.json", "w"))
json.dump({
    "auc": round(float(roc_auc_score(y_test, proba)), 3),
    "rappel_a_risque": round(float(recall_score(y_test, pred)), 3),
    "rappel_baseline": round(float(rappel_base), 3),
    "n_train": int(len(X_train)),
}, open("models/metrics.json", "w"), indent=2)
print("\nModele sauvegarde dans models/churn_model.joblib")