# Déploiement Kubernetes — API anti-churn Soluna

Manifests pour déployer l'API conteneurisée sur un cluster Kubernetes (en local
avec **minikube** ou **kind**, ou sur un cluster managé).

## Contenu
- `deployment.yaml` — 2 réplicas de l'API, avec *readiness* et *liveness probes* sur `/health`.
- `service.yaml` — expose l'API via un `NodePort` (port 30080).

## Démarrage rapide (kind / minikube en local)

```bash
# 1. Construire l'image (depuis la racine du dépôt)
docker build -t soluna-api:latest .

# 2a. Avec kind : charger l'image dans le cluster
kind create cluster
kind load docker-image soluna-api:latest

# 2b. Avec minikube : pointer Docker vers le démon du cluster avant le build
#     eval $(minikube docker-env) && docker build -t soluna-api:latest .

# 3. Déployer
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 4. Vérifier
kubectl get pods
kubectl get service soluna-api

# 5. Accéder à l'API
#    kind     : kubectl port-forward service/soluna-api 8000:80  -> http://localhost:8000/docs
#    minikube : minikube service soluna-api --url
```

## Pourquoi Kubernetes
- **Disponibilité** : plusieurs réplicas, redémarrage automatique si un pod tombe (liveness).
- **Mises à jour sans coupure** : rolling update natif lors d'un nouveau build de l'image.
- **Sondes de santé** : le trafic n'est routé que vers les pods dont `/health` répond.

> En production, l'image serait poussée sur un registre (au lieu d'`IfNotPresent`)
> et le `NodePort` remplacé par un `Ingress` + TLS.
