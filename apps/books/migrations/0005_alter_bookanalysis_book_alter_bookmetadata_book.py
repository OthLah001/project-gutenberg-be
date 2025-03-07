# Generated by Django 5.1.6 on 2025-03-02 07:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0004_booksearchhistory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookanalysis',
            name='book',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='analysis', to='books.book'),
        ),
        migrations.AlterField(
            model_name='bookmetadata',
            name='book',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='metadata', to='books.book'),
        ),
    ]
