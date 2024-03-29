# Generated by Django 4.2.2 on 2023-12-05 07:42

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eboksbesked',
            name='cpr',
            field=models.BigIntegerField(blank=True, db_index=True, null=True, validators=[django.core.validators.MinValueValidator(101000000), django.core.validators.MaxValueValidator(3112999999)]),
        ),
        migrations.AlterField(
            model_name='indberetterprofile',
            name='cpr',
            field=models.BigIntegerField(blank=True, db_index=True, null=True, validators=[django.core.validators.MinValueValidator(101000000), django.core.validators.MaxValueValidator(3112999999)]),
        ),
    ]
