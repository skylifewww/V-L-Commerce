#!/usr/bin/env bash
set -o errexit

echo "Installing dependencies..."

# Pre-install compatible versions to avoid heif compilation
pip install "Pillow==10.4.0" "pillow-heif==0.17.0" || echo "pillow-heif optional"

# Install requirements one by one, skipping problematic ones
pip install Django==4.2.7
pip install wagtail==5.2 || pip install wagtail==5.2 --no-deps
pip install psycopg2-binary celery==5.3.4 redis
pip install django-debug-toolbar django-extensions django-simple-history
pip install openpyxl requests gunicorn whitenoise dj-database-url

# Install wagtail dependencies separately if needed
pip install django-modelcluster django-taggit django-treebeard djangorestframework django-filter beautifulsoup4 html5lib l18n anyascii telepath draftjs-exporter || true

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate

echo "Build complete!"
