import os
import sys
import subprocess

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

def run(cmd):
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

# создаём venv и ставим зависимости
run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
if os.path.exists("requirements.txt"):
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
if os.path.exists("requirements.deploy.txt"):
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.deploy.txt"])

# собираем статику и миграции
run([sys.executable, "manage.py", "collectstatic", "--noinput"])
run([sys.executable, "manage.py", "migrate", "--noinput"])

# порт задаётся платформой
port = os.environ.get("SERVER_PORT") or os.environ.get("PORT") or "24587"
run(["gunicorn", "config.wsgi:application", "--bind", f"0.0.0.0:{port}"])
