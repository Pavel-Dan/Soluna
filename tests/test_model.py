import numpy as np
from sklearn.ensemble import RandomForestClassifier

def test_modele_predit_des_probabilites():
    rng = np.random.RandomState(0)
    X = rng.rand(400, 5)
    y = (X[:, 0] + X[:, 1] > 1).astype(int)
    m = RandomForestClassifier(n_estimators=20, random_state=0).fit(X, y)
    proba = m.predict_proba(X[:5])[:, 1]
    assert proba.min() >= 0 and proba.max() <= 1
    assert proba.shape == (5,)