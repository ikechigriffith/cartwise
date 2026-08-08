# Use Celery and Redis for background jobs

We will use Celery workers with Redis as the job broker for background work such as scraping, price refreshes, stock checks, product mapping candidates, and future notifications. This keeps user-facing FastAPI requests fast while allowing retries, schedules, and worker scaling; the MVP will control cost by starting with minimal worker capacity and conservative scraping schedules.
