# Generated by Django 5.1.1 on 2024-10-14 10:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_alter_restaurant_images_alter_restaurant_owner"),
    ]

    operations = [
        migrations.CreateModel(
            name="RestaurantImage",
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
                ("image", models.ImageField(upload_to="restaurant_additional_images/")),
                (
                    "restaurant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="additional_images",
                        to="core.restaurant",
                    ),
                ),
            ],
        ),
    ]