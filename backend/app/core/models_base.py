"""Base class for SQLAlchemy models - safe for Alembic imports."""
from sqlalchemy.orm import declarative_base

# Create Base without any engine dependencies
# This can be safely imported by Alembic
Base = declarative_base()

