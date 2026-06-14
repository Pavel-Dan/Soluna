# Infrastructure as Code — choix et alternatives

L'infrastructure de Soluna est décrite **en code**, versionnée et déployable en
une commande. Deux implémentations sont fournies :

## 1. Docker Compose — chemin principal (`docker-compose.yml`, racine)
Retenu pour le projet : il décrit l'ensemble de la stack (PostgreSQL, Adminer,
Kafka, Airflow) dans un seul fichier lisible, idéal pour un environnement de
développement et de démonstration reproductible.

```bash
docker compose up -d
```

## 2. Terraform — alternative outillée (`terraform/main.tf`)
Fourni pour démontrer la même approche avec un outil d'IaC standard du marché,
via le *provider* Docker. Il provisionne l'entrepôt PostgreSQL (image, volume,
conteneur, ports).

```bash
cd terraform
terraform init
terraform apply
```

## 3. Kubernetes — déploiement applicatif (`k8s/`)
Pour servir l'API du modèle (Bloc 4) en production : réplicas, sondes de santé,
exposition réseau. Voir `k8s/README.md`.

## Pourquoi ce choix
Docker Compose couvre tout le périmètre du mémoire avec un minimum de
complexité. Terraform et Kubernetes sont ajoutés pour montrer la **maîtrise des
outils d'IaC et d'orchestration** attendus en production, sans surdimensionner
l'environnement de développement.
