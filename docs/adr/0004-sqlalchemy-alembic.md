# Use SQLAlchemy 2.0 and Alembic

We will use SQLAlchemy 2.0 as the Python database access layer and Alembic for schema migrations. The application has a complex relational domain and will likely use PostgreSQL-specific capabilities such as PostGIS and pgvector, so a mature and flexible ORM plus migration tool is preferred over lighter abstractions.
