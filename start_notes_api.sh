#!/bin/bash
set -e

# Parse command line arguments
environment="production"  # Default to production
for arg in "$@"
do
    case $arg in
        --environment=*)
            environment="${arg#*=}"
            shift
            ;;
        *)
            # Unknown argument
            ;;
    esac
done

# Run Django migrations
python manage.py makemigrations
python manage.py migrate

# Load fixture data (optional; ignore errors if no fixtures or invalid)
python manage.py loaddata fixtures/* 2>/dev/null || true

# Collect static files
python manage.py collectstatic --no-input

# Run different commands based on environment parameter
if [ "$environment" = "local" ]; then
    # Run Django dev server for local development
    python manage.py runserver 0.0.0.0:8000
else
    # Run Gunicorn server for other environments (staging, production)
    gunicorn notes_manager.wsgi:application -b 0.0.0.0:8000
fi
