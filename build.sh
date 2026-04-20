#!/usr/bin/env bash
set -o errexit

echo "Installing dependencies..."
# Install without heif extras to avoid compilation issues
pip install "Willow==1.6.3" "Pillow==10.4.0" --no-deps
pip install -r requirements.txt --no-deps 2>/dev/null || pip install -r requirements.txt

# Ensure critical dependencies are installed
pip install Django wagtail psycopg2-binary gunicorn whitenoise dj-database-url

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate

echo "Build complete!"
