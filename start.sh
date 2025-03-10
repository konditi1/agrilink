#!/bin/bash

# Run database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Start the Django server
echo "Starting Django server..."
gunicorn agrilink.wsgi:application --bind 0.0.0.0:8000
