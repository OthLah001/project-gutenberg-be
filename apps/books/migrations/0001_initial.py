# Generated by Django 5.1.6 on 2025-03-01 11:54

import django.contrib.postgres.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Book",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("gutenberg_id", models.IntegerField(db_index=True, unique=True)),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("modified_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="BookAnalysis",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("summary", models.TextField()),
                ("key_characters", models.JSONField()),
                (
                    "themes",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=255), size=None
                    ),
                ),
                (
                    "topics",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=255), size=None
                    ),
                ),
                ("sentiment_and_emotion", models.TextField()),
                (
                    "notable_quotes",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=255), size=None
                    ),
                ),
                (
                    "character_relationships",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=255), size=None
                    ),
                ),
                (
                    "book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="analysis",
                        to="books.book",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BookMetadata",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(db_index=True, max_length=500)),
                ("issued_date", models.DateField()),
                ("language", models.CharField(db_index=True, max_length=100)),
                (
                    "authors",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=255), size=None
                    ),
                ),
                (
                    "subjects",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=255), size=None
                    ),
                ),
                ("locc", models.CharField(max_length=255)),
                (
                    "bookshelves",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=255), size=None
                    ),
                ),
                ("filled_by_script", models.BooleanField(default=False)),
                (
                    "book",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="metadata",
                        to="books.book",
                    ),
                ),
            ],
        ),
    ]
