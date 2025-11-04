# Load .env if present
ENV_LOAD = set -a; [ -f .env ] && . ./.env; set +a;

.PHONY: install migrate run docker-up env

install:
	pip install -r requirements.txt

migrate:
	$(ENV_LOAD) python manage.py makemigrations
	$(ENV_LOAD) python manage.py migrate

run:
	$(ENV_LOAD) python manage.py runserver 0.0.0.0:8000

# Bring up services defined in docker-compose.yml (if Docker is installed)
docker-up:
	docker compose up -d

# Create .env from template if missing
env:
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env created"; else echo ".env already exists"; fi
