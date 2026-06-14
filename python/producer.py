import json, time, psycopg2
from confluent_kafka import Producer

producer = Producer({"bootstrap.servers": "localhost:9092"})

conn = psycopg2.connect(host="localhost", port=5432, dbname="soluna",
                        user="soluna", password="soluna")
cur = conn.cursor()
cur.execute("""
    SELECT order_id, user_id, order_number, order_dow, order_hour_of_day, days_since_prior_order
    FROM raw.orders
    WHERE user_id <= 200
    ORDER BY user_id, order_number
""")

print("Diffusion des commandes dans Kafka (Ctrl+C pour arrêter)...")
n = 0
try:
    for order_id, user_id, order_number, dow, hour, dsp in cur:
        event = {
            "order_id": order_id, "user_id": user_id, "order_number": order_number,
            "order_dow": dow, "order_hour_of_day": hour,
            "days_since_prior_order": float(dsp) if dsp is not None else None,
        }
        producer.produce("orders", key=str(user_id), value=json.dumps(event))
        producer.poll(0)
        n += 1
        if n % 50 == 0:
            print(f"  {n} commandes envoyees...")
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nArret demande.")
finally:
    producer.flush()
    print(f"Total envoye : {n} commandes.")
    cur.close(); conn.close()