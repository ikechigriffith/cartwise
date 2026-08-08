# Self-host PostgreSQL for the real MVP

We will use local Docker PostgreSQL for development and self-host PostgreSQL in Docker on the MVP VPS rather than relying on Supabase-specific platform features. A free managed Postgres provider such as Neon may be used for prototypes or demos, but the real MVP target is portable PostgreSQL with standard tooling, automated backups, and minimal vendor lock-in.
