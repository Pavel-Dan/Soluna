import json, psycopg2
from confluent_kafka import Consumer

conn = psycopg2.connect(host="localhost", port=5432, dbname="soluna",
                        user="soluna", password="soluna")
conn.autocommit = True
cur = conn.cursor()

UPSERT = """
INSERT INTO stream.client_features
  (user_id, nb_commandes, derniere_order_number, somme_jours, nb_intervalles, derniere_maj)
VALUES (%s, 1, %s, %s, %s, now())
ON CONFLICT (user_id) DO UPDATE SET
  nb_commandes          = stream.client_features.nb_commandes + 1,
  derniere_order_number = GREATEST(stream.client_features.derniere_order_number, EXCLUDED.derniere_order_number),
  somme_jours           = stream.client_features.somme_jours + EXCLUDED.somme_jours,
  nb_intervalles        = stream.client_features.nb_intervalles + EXCLUDED.nb_intervalles,
  derniere_maj          = now();
"""

def valide(e):
    if not isinstance(e.get("user_id"), int): return "user_id invalide"
    if not isinstance(e.get("order_number"), int) or e["order_number"] < 1: return "order_number invalide"
    d = e.get("days_since_prior_order")
    if d is not None and (not isinstance(d, (int, float)) or d < 0 or d > 365): return "ecart en jours hors bornes"
    return None

consumer = Consumer({"bootstrap.servers": "localhost:9092",
                     "group.id": "soluna-features", "auto.offset.reset": "earliest"})
consumer.subscribe(["orders"])
print("Consommation du flux (Ctrl+C pour arreter)...")
n_ok = n_ko = 0
try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print("Erreur Kafka:", msg.error()); continue
        try:
            e = json.loads(msg.value())
        except Exception:
            cur.execute("INSERT INTO stream.evenements_invalides (raison, contenu) VALUES (%s,%s)",
                        ("JSON illisible", msg.value().decode("utf-8", "replace")))
            n_ko += 1; continue
        raison = valide(e)
        if raison:
            cur.execute("INSERT INTO stream.evenements_invalides (raison, contenu) VALUES (%s,%s)",
                        (raison, json.dumps(e)))
            n_ko += 1; continue
        d = e["days_since_prior_order"]
        somme = d if d is not None else 0
        nb_int = 1 if d is not None else 0
        cur.execute(UPSERT, (e["user_id"], e["order_number"], somme, nb_int))
        n_ok += 1
        if (n_ok + n_ko) % 100 == 0:
            print(f"  traites : {n_ok} valides, {n_ko} invalides")
except KeyboardInterrupt:
    print(f"\nArret. Total : {n_ok} valides, {n_ko} invalides.")
finally:
    consumer.close(); cur.close(); conn.close()