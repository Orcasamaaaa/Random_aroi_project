# Generated by Django 5.1.1 on 2024-10-14 09:40

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_restaurant_owner"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="restaurant",
            name="images",
            field=models.ImageField(
                blank=True, null=True, upload_to="restaurant_images/"
            ),
        ),
        migrations.AlterField(
            model_name="restaurant",
            name="owner",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
