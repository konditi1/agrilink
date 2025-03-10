#!/bin/bash

# Extract database credentials from DATABASE_URL
DB_URL="postgresql://fena:QHx2YQdzLunOcV0M4H4zvGUg8lj7QEev@dpg-cv7hp1tds78s7395vp30-a/agrilink"

DB_USER=$(echo $DB_URL | sed -E 's|postgresql://([^:]+):.*|\1|')
DB_PASSWORD=$(echo $DB_URL | sed -E 's|postgresql://[^:]+:([^@]+)@.*|\1|')
DB_HOST=$(echo $DB_URL | sed -E 's|postgresql://[^@]+@([^/:]+).*|\1|')
DB_NAME=$(echo $DB_URL | sed -E 's|.*/([^/]+)$|\1|')

# Enable pg_trgm extension
echo "Enabling pg_trgm extension..."
PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -h $DB_HOST -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# Run database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Start the Django server
echo "Starting Django server..."
gunicorn agrilink.wsgi:application --bind 0.0.0.0:8000
