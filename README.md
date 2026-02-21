# Notes Manager

## Description

Notes CRUD API.

**Live API:** [https://emmanuelcodinghub.com/notes/api](https://emmanuelcodinghub.com/notes/api) — root links to `notes`, `categories`, and `tags` endpoints.

**API docs (Postman):** [Notes API collection](https://www.postman.com/molero3111/workspace/emmanuel-s-workspace/collection/9720967-e6037335-9f6e-4104-aa8a-82b951fd8e30?action=share&creator=9720967&active-environment=9720967-ebb21adc-4590-4fa2-8e30-9e219cff367f). You may need to create your own env, once created, set the collection variable **url** to `https://emmanuelcodinghub.com/notes/api`, and set **token** after logging in or registering so authenticated requests work.

**Bugs, suggestions, and ideas for improvement:** please open an issue in [GitHub Issues](https://github.com/molero3111/notes_api/issues).

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

4. Build and run docker containers:

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
   - `VPS_SSH_PORT` – SSH port (e.g. `2111` if not using 22)
   - `SSH_PRIVATE_KEY` – paste the full private key (the matching public key must be in the VPS `~/.ssh/authorized_keys`)

2. On the VPS, ensure the app lives at `~/notes_crud/backend` (clone the repo there if needed) and that Docker/Docker Compose are installed. The staging compose file uses the image from Docker Hub; no local build is required.
