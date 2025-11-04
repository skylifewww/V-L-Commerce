# TikFlow Commerce – Local Run Book

## Prereqs
- macOS, Python 3.13 (virtualenv)
- Docker + Docker Compose

## Setup (one-time)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create .env (or update your existing one):
```bash
cat > .env <<'EOF'
DJANGO_DEBUG=1
POSTGRES_DB=tikflow
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
WAGTAILADMIN_BASE_URL=http://127.0.0.1:8000
EOF
```

Start infrastructure:
```bash
make docker-up   # Postgres + Redis
# wait 5–10s for DB to be ready
```

Initialize DB (first run or after reset):
```bash
python3 manage.py migrate
DJANGO_SUPERUSER_USERNAME=skylife_www \
DJANGO_SUPERUSER_EMAIL=skylife@ukr.net \
DJANGO_SUPERUSER_PASSWORD=SkyWlifE123 \
python3 manage.py createsuperuser --noinput
```

Run server:
```bash
python3 manage.py runserver
```
- Admin: http://127.0.0.1:8000/admin/
- Wagtail: http://127.0.0.1:8000/cms/
- Shop: http://127.0.0.1:8000/eshop/products/

## Wagtail home page (if root shows default screen)
Create and bind a Home page:
```bash
python3 manage.py shell -c "
from wagtail.models import Page, Site
from landing.pages import LandingPage
root = Page.get_first_root_node()
home = LandingPage(title='Home', slug='home')
root.add_child(instance=home)
home.save_revision().publish()
Site.objects.update_or_create(
    hostname='127.0.0.1', port=8000,
    defaults={'site_name':'TikFlow Commerce','root_page':home,'is_default_site':True}
)
print('Home created and Site bound.')
"
```

## Useful make targets
- `make docker-up` – start DB/Redis
- `make migrate` – makemigrations + migrate with .env
- `make down` – stop containers

## Troubleshooting
- FATAL: role does not exist
  - Ensure `.env` has `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`, host `127.0.0.1`, port `5432`.
  - Re-run: `python3 manage.py migrate`

- database "tikflow" does not exist
  - Create it inside the container:
    ```bash
    docker exec -it tikflow_commerce-db-1 psql -U postgres -c "CREATE DATABASE tikflow OWNER postgres;"
    ```
  - Then: `python3 manage.py migrate`

- Verify DB connectivity from Python:
```bash
python3 - <<'PY'
import psycopg2
conn = psycopg2.connect("host=127.0.0.1 port=5432 dbname=tikflow user=postgres password=postgres")
cur=conn.cursor(); cur.execute("SELECT current_database(), current_user;"); print(cur.fetchone()); conn.close()
PY
```

## Daily flow
```bash
source .venv/bin/activate
make docker-up
python3 manage.py runserver
# Ctrl+C to stop
git status
make down
```
