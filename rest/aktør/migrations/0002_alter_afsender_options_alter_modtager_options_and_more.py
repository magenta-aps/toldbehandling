# Generated by Django 4.2.2 on 2024-01-23 12:24

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aktør', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='afsender',
            options={},
        ),
        migrations.AlterModelOptions(
            name='modtager',
            options={},
        ),
        migrations.AddField(
            model_name='afsender',
            name='kladde',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='modtager',
            name='kladde',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='afsender',
            name='adresse',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='afsender',
            name='by',
            field=models.CharField(blank=True, db_index=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='afsender',
            name='navn',
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='afsender',
            name='postnummer',
            field=models.PositiveSmallIntegerField(blank=True, db_index=True, null=True, validators=[django.core.validators.MinValueValidator(1000), django.core.validators.MaxValueValidator(9999)]),
        ),
        migrations.AlterField(
            model_name='afsender',
            name='telefon',
            field=models.CharField(blank=True, max_length=12, null=True),
        ),
        migrations.AlterField(
            model_name='modtager',
            name='adresse',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='modtager',
            name='by',
            field=models.CharField(blank=True, db_index=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='modtager',
            name='navn',
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='modtager',
            name='postnummer',
            field=models.PositiveSmallIntegerField(blank=True, db_index=True, null=True, validators=[django.core.validators.MinValueValidator(1000), django.core.validators.MaxValueValidator(9999)]),
        ),
        migrations.AlterField(
            model_name='modtager',
            name='telefon',
            field=models.CharField(blank=True, max_length=12, null=True),
        ),
        migrations.AddConstraint(
            model_name='afsender',
            constraint=models.CheckConstraint(check=models.Q(('navn__isnull', False), ('kladde', True), _connector='OR'), name='aktuel_afsender_har_navn'),
        ),
        migrations.AddConstraint(
            model_name='afsender',
            constraint=models.CheckConstraint(check=models.Q(('adresse__isnull', False), ('kladde', True), _connector='OR'), name='aktuel_afsender_har_adresse'),
        ),
        migrations.AddConstraint(
            model_name='afsender',
            constraint=models.CheckConstraint(check=models.Q(('postnummer__isnull', False), ('kladde', True), _connector='OR'), name='aktuel_afsender_har_postnummer'),
        ),
        migrations.AddConstraint(
            model_name='afsender',
            constraint=models.CheckConstraint(check=models.Q(('by__isnull', False), ('kladde', True), _connector='OR'), name='aktuel_afsender_har_by'),
        ),
        migrations.AddConstraint(
            model_name='afsender',
            constraint=models.CheckConstraint(check=models.Q(('telefon__isnull', False), ('kladde', True), _connector='OR'), name='aktuel_afsender_har_telefon'),
        ),
        migrations.AddConstraint(
            model_name='modtager',
            constraint=models.CheckConstraint(check=models.Q(('navn__isnull', False), ('kladde', True), _connector='OR'), name='aktuel_modtager_har_navn'),
        ),
        migrations.AddConstraint(
            model_name='modtager',
            constraint=models.CheckConstraint(check=models.Q(('adresse__isnull', False), ('kladde', True), _connector='OR'), name='aktuel_modtager_har_adresse'),
        ),
        migrations.AddConstraint(
            model_name='modtager',
            constraint=models.CheckConstraint(check=models.Q(('postnummer__isnull', False), ('kladde', True), _connector='OR'), name='aktuel_modtager_har_postnummer'),
        ),
        migrations.AddConstraint(
            model_name='modtager',
            constraint=models.CheckConstraint(check=models.Q(('by__isnull', False), ('kladde', True), _connector='OR'), name='aktuel_modtager_har_by'),
        ),
        migrations.AddConstraint(
            model_name='modtager',
            constraint=models.CheckConstraint(check=models.Q(('telefon__isnull', False), ('kladde', True), _connector='OR'), name='aktuel_modtager_har_telefon'),
        ),
    ]
