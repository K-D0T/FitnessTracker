# Generated by Django 5.0.3 on 2024-05-09 18:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_remove_workout_duration_workout_end_time_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workout',
            name='date',
            field=models.DateField(auto_now_add=True),
        ),
    ]
