release: python manage.py migrate
web: gunicorn config.wsgi --log-file -
celery: celery -A config worker --loglevel=info