# Run the web app on the MVP VPS

We will run the Next.js web app on the same Hetzner VPS as the API, workers, Redis, PostgreSQL, and Caddy for the MVP. This keeps infrastructure simple, low-cost, Docker-based, and portable, with Caddy routing web and API traffic by hostname or path.
