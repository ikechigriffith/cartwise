# Architecture

## MVP Stack

- Web: Next.js
- Mobile: Expo / React Native
- API: FastAPI
- Database: PostgreSQL
- Database access: SQLAlchemy 2.0 + Alembic
- Background jobs: Celery + Redis
- Reverse proxy / HTTPS: Caddy
- Hosting target: Hetzner VPS
- Deployment: GitHub Actions + GitHub Container Registry + Docker Compose

## Runtime Topology

```txt
Internet
  ↓
Caddy
  ├── web → Next.js
  └── api → FastAPI
            ├── PostgreSQL
            └── Redis → Celery worker → PostgreSQL
```

## Deployment Flow

```txt
Push to main
  ↓
GitHub Actions builds Docker images
  ↓
Images pushed to GitHub Container Registry
  ↓
GitHub Actions SSHes into Hetzner VPS
  ↓
Docker Compose pulls images and restarts services
```

## Notes

- Local development can use `docker-compose.yml` with build contexts.
- Production deployment uses `docker-compose.prod.yml` to pull GHCR images.
- PostgreSQL is self-hosted on the VPS for the real MVP, with automated backups to be added before real users.
