# Use a separate API app

We will use a separate API app in the monorepo instead of putting backend logic primarily in Next.js API routes. The product needs shared access from web and mobile plus backend-heavy capabilities like scraping, product mapping, route planning, stock checks, price history, and background work, so separating the API keeps the backend boundary explicit and easier to evolve.
