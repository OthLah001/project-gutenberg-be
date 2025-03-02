# Generated by Django 5.1.6 on 2025-03-01 14:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("books", "0002_alter_bookmetadata_authors_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="content",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="bookanalysis",
            name="book",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="analysis",
                to="books.book",
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="bookmetadata",
            name="book",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="metadata",
                to="books.book",
                unique=True,
            ),
        ),
    ]
