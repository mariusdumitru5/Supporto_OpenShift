from prometheus_client import start_http_server, Counter
import time
import random

REQUEST_COUNTER = Counter('mie_richieste_totali', 'Numero di richieste ricevute dall app Python', ['endpoint'])

if __name__ == '__main__':
    # FORZA l'ascolto su 0.0.0.0 per accettare connessioni da Prometheus
    start_http_server(8000, addr='0.0.0.0')
    print("Server metriche Python avviato sulla porta 8000 (0.0.0.0)...")

    while True:
        REQUEST_COUNTER.labels(endpoint='/api').inc()
        time.sleep(random.uniform(0.5, 2.0))