# Generated by Django 4.2.2 on 2024-02-19 07:31

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0005_postnummer_stedkode'),
        ('aktør', '0005_alter_afsender_postnummer_alter_modtager_postnummer'),
    ]

    operations = [
        migrations.AddField(
            model_name='afsender',
            name='eksplicit_stedkode',
            field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(999)]),
        ),
        migrations.AddField(
            model_name='afsender',
            name='postnummer_ref',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='common.postnummer'),
        ),
        migrations.AddField(
            model_name='modtager',
            name='eksplicit_stedkode',
            field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(999)]),
        ),
        migrations.AddField(
            model_name='modtager',
            name='postnummer_ref',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='common.postnummer'),
        ),
    ]
