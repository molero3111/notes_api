# Notes Manager

## Description

Notes CRUD API

##  Runtimes, engines, tools and requirements

- **Python**: 3.8.0
- **Django**: 4.2.11
- **Django REST Framework (DRF)**: 3.15.1
- **Django CORS headers**: 4.3.1
- **Database**: PostgreSQL 13-3.1

## Run Project locally

1. Clone the repository:

```bash
git clone https://github.com/molero3111/notes_api.git
```

2. cd into notes api repository:

```bash
cd notes_api/
```

3. Create .env and .env.secrets:

```bash
cp .env.example .env 
cp .env.secrets.example .env.secrets
```

4. Create notes_api_network:

```bash
docker network create notes_api_network
```

5. Build and run docker containers:

```bash
docker compose -p local-notes-api up --build
```

## Staging deployment (GitHub Actions)

Merges (or pushes) to the `staging` branch trigger an automated deploy:

1. The workflow builds the Docker image and pushes it to Docker Hub (`molero3111/notes-api:latest`), so the VPS does no build and uses fewer resources.
2. It then SSHs into the VPS and runs `git pull`, `docker compose pull`, and `docker compose up -d` in `~/notes_crud/backend`.

**One-time setup**

1. In the repo: **Settings → Secrets and variables → Actions**, add:
   - `DOCKERHUB_USERNAME` – your Docker Hub username
   - `DOCKERHUB_TOKEN` – a Docker Hub [access token](https://hub.docker.com/settings/security)
   - `VPS_HOST` – VPS IP or hostname
   - `VPS_USER` – SSH user (e.g. `ubuntu`)
   - `SSH_PRIVATE_KEY` – paste the full private key (the matching public key must be in the VPS `~/.ssh/authorized_keys`)

2. On the VPS, ensure the app lives at `~/notes_crud/backend` (clone the repo there if needed) and that Docker/Docker Compose are installed. The staging compose file uses the image from Docker Hub; no local build is required.