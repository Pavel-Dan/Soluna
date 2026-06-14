terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

# Image de l'entrepot
resource "docker_image" "postgres" {
  name = "postgres:16"
}

# Volume persistant pour les donnees
resource "docker_volume" "warehouse_data" {
  name = "soluna_warehouse_data"
}

# Conteneur de l'entrepot (equivalent du service `warehouse` du docker-compose)
resource "docker_container" "warehouse" {
  name  = "soluna-warehouse"
  image = docker_image.postgres.image_id

  env = [
    "POSTGRES_USER=soluna",
    "POSTGRES_PASSWORD=soluna",
    "POSTGRES_DB=soluna",
  ]

  ports {
    internal = 5432
    external = 5432
  }

  volumes {
    volume_name    = docker_volume.warehouse_data.name
    container_path = "/var/lib/postgresql/data"
  }
}
