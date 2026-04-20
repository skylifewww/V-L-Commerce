#!/usr/bin/env bash
set -o errexit

echo "Installing dependencies..."
# Install Willow without heif first to avoid compilation issues
pip install Willow==1.6.3 Pillow==10.4.0
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate

echo "Build complete!"
