#!/bin/bash
set -e

echo "Starting Donna AI Backend..."

# Wait for database to be ready (if using Postgres)
if [[ "$DATABASE_URL" == *"postgresql"* ]]; then
    echo "Waiting for PostgreSQL to be ready..."
    until pg_isready -h $(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p') -p $(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p') -U $(echo $DATABASE_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p'); do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 2
    done
    echo "PostgreSQL is up - executing migrations"
fi

# Run Alembic migrations
if [ -f "alembic.ini" ]; then
    echo "Running database migrations..."
    alembic upgrade head
    echo "Migrations completed"
else
    echo "No alembic.ini found, skipping migrations"
fi

# Execute the main command
exec "$@"

