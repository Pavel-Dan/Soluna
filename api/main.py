import os, json, joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from api.logic import recommander_action

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model = joblib.load(os.path.join(ROOT, "models", "churn_model.joblib"))
FEATURES = json.load(open(os.path.join(ROOT, "models", "features.json")))

app = FastAPI(title="Soluna - API anti-churn")

class Client(BaseModel):
    nb_commandes: int
    cadence_moy: float
    cadence_std: float
    cadence_max: float
    cadence_min: float

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
def predict(c: Client):
    X = pd.DataFrame([[getattr(c, f) for f in FEATURES]], columns=FEATURES)
    proba = float(model.predict_proba(X)[0, 1])
    a_risque, action = recommander_action(proba)
    return {
        "probabilite_churn": round(proba, 3),
        "a_risque": a_risque,
        "action_recommandee": action,
    }