def recommander_action(proba: float):
    a_risque = proba >= 0.5
    action = ("Proposer une pause d'abonnement pour preserver la valeur client"
              if a_risque else "Aucune action - abonne fidele")
    return a_risque, action