# Generated by Django 5.0.3 on 2024-05-20 17:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0012_alter_lift_sets_rating'),
    ]

    operations = [
        migrations.AddField(
            model_name='workout',
            name='rating',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.DeleteModel(
            name='Rating',
        ),
    ]