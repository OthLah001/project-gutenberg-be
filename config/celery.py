import os

from celery import Celery

from observability.setup import bootstrap_observability

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

bootstrap_observability()

app = Celery(
    "config",
)
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
