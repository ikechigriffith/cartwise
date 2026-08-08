# Use GitHub Actions, GHCR, and Docker Compose for CI/CD

We will build Docker images in GitHub Actions, push them to GitHub Container Registry, and deploy them to the Hetzner VPS with Docker Compose. This separates building from running, reduces load on the VPS, supports image rollback, and keeps the deployment pipeline cheap and production-like for the MVP.
