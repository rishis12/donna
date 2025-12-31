#!/bin/bash
set -e

echo "Starting Donna AI Backend..."

# Wait for database to be ready (if using Postgres in docker-compose only)
# Skip check for cloud deployments (Render, Railway, Fly.io) - they manage PostgreSQL separately
if [[ "$DATABASE_URL" == *"postgresql"* ]] && [[ "$DATABASE_URL" == *"@postgres"* ]]; then
    echo "Checking PostgreSQL connection (docker-compose)..."
    DB_HOST="postgres"
    DB_PORT="5432"
    DB_USER="${POSTGRES_USER:-donna}"
    
    MAX_ATTEMPTS=30
    ATTEMPT=0
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; then
            echo "PostgreSQL is ready"
            break
        fi
        ATTEMPT=$((ATTEMPT + 1))
        if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
            echo "Warning: PostgreSQL check timeout. Proceeding with migrations..."
            break
        fi
        echo "PostgreSQL unavailable - retrying ($ATTEMPT/$MAX_ATTEMPTS)..."
        sleep 2
    done
elif [[ "$DATABASE_URL" == *"postgresql"* ]]; then
    echo "Using external/cloud PostgreSQL - skipping readiness check (managed by platform)"
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

