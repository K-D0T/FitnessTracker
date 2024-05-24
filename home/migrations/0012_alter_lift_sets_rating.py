# Generated by Django 5.0.3 on 2024-05-20 17:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0011_alter_lift_lift_delete_liftname'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lift',
            name='sets',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField()),
                ('workout', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.workout')),
            ],
        ),
    ]
