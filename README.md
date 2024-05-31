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