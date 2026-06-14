from __future__ import annotations
import pendulum
from airflow.decorators import dag, task

@dag(
    schedule="@hourly",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["soluna"],
)
def soluna_pipeline():

    @task
    def controle_qualite():
        import psycopg2
        conn = psycopg2.connect(host="warehouse", port=5432, dbname="soluna",
                                user="soluna", password="soluna")
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM stream.client_features")
        n = cur.fetchone()[0]
        assert n > 0, "Aucun client suivi dans la couche stream"
        cur.execute("SELECT count(*) FROM stream.client_features WHERE somme_jours < 0")
        assert cur.fetchone()[0] == 0, "Valeurs negatives detectees"
        cur.execute("SELECT count(*) FROM stream.evenements_invalides")
        invalides = cur.fetchone()[0]
        conn.close()
        print(f"Controle qualite OK : {n} clients, {invalides} evenements invalides.")
        return n

    @task
    def rafraichir_agregat(n: int):
        import psycopg2
        conn = psycopg2.connect(host="warehouse", port=5432, dbname="soluna",
                                user="soluna", password="soluna")
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS stream.cadence_resume (
                         calcule_le timestamptz, segment text, nb_clients int)""")
        cur.execute("DELETE FROM stream.cadence_resume")
        cur.execute("""
            INSERT INTO stream.cadence_resume (calcule_le, segment, nb_clients)
            SELECT now(),
                   CASE WHEN somme_jours / NULLIF(nb_intervalles, 0) <= 10 THEN 'frequent'
                        WHEN somme_jours / NULLIF(nb_intervalles, 0) <= 25 THEN 'regulier'
                        ELSE 'a risque' END,
                   count(*)
            FROM stream.client_features
            WHERE nb_intervalles > 0
            GROUP BY 1, 2
        """)
        conn.close()
        print(f"Agregat rafraichi pour {n} clients.")

    rafraichir_agregat(controle_qualite())

soluna_pipeline()