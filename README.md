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

## Homelab storage guard

On the homelab, Postgres data lives on a fixed 300 MB volume (a loop-mounted ext4 image at `/srv/volumes/notes-api-db`). If that volume fills completely, Postgres stops and **can't restart** until space is freed. To keep the volume from filling, the api mounts it read-only and refuses writes once less than `DB_WRITE_GUARD_MIN_FREE_MB` (64) is free. Those settings go in the homelab `.env`:

```
DB_WRITE_GUARD_PATH=/var/lib/notes-db-volume
DB_WRITE_GUARD_MIN_FREE_MB=64
```

**What happens when it trips:** note creates and updates, and sign-ups, return `507 Storage is full...`. Reading, deleting and login keep working. The api logs `Write refused (...): N MB free on the database volume`.

**Recovery.** Postgres doesn't shrink its files when rows are deleted (it reuses the space internally), so deleting notes alone won't clear the guard. Run these from `/srv/apps/notes-api`:

1. Find what filled it:
   ```
   docker compose -p notes-api exec db psql -U postgres -d notes_db -c \
     "SELECT u.username, count(n.id) notes, pg_size_pretty(sum(pg_column_size(n.content))::bigint) content
        FROM auth_user u JOIN notes_note n ON n.user_id = u.id GROUP BY u.username ORDER BY sum(pg_column_size(n.content)) DESC LIMIT 10;"
   ```
2. Delete the abusive accounts in Django admin (`/admin/` → Users); their notes are deleted with them.
3. Reclaim the space. `VACUUM FULL` rewrites each table with only its live rows, so it needs free space about the size of the **remaining** data, not of the bloated table. Check the live size first:
   ```
   docker compose -p notes-api exec db psql -U postgres -d notes_db -c \
     "SELECT pg_size_pretty(sum(pg_column_size(n.*))::bigint) live FROM notes_note n;"
   docker compose -p notes-api exec db psql -U postgres -d notes_db -c \
     "VACUUM FULL notes_note; VACUUM FULL notes_note_tags; VACUUM FULL notes_note_categories; VACUUM FULL authtoken_token; VACUUM FULL auth_user;"
   ```
   If the live data is close to the free space, grow the image instead (with the db stopped: `truncate -s +200M` on the image, then `losetup -c` and `resize2fs` on its loop device).
4. Check `df -h /srv/volumes/notes-api-db`. Writes resume on their own once more than 64 MB is free.

**If Postgres is already down from a full disk:** the image keeps 10% of its blocks reserved for root. `tune2fs -m 0 <loop device>` releases them so Postgres can start, then follow the steps above and restore the reserve with `tune2fs -m 10 <loop device>`.
