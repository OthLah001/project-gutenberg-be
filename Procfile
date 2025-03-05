release: python manage.py migrate
web: gunicorn config.wsgi --timeout 120 --log-file -