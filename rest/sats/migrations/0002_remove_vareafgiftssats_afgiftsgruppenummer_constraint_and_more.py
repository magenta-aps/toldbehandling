# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

# Generated by Django 4.2.2 on 2023-08-09 12:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sats', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='vareafgiftssats',
            name='afgiftsgruppenummer_constraint',
        ),
        migrations.AddField(
            model_name='vareafgiftssats',
            name='kræver_indførselstilladelse',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='vareafgiftssats',
            name='minimumsbeløb',
            field=models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='vareafgiftssats',
            name='overordnet',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='underordnede', to='sats.vareafgiftssats'),
        ),
        migrations.AddField(
            model_name='vareafgiftssats',
            name='segment_nedre',
            field=models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=10, null=True, verbose_name='Nedre grænse for mængden der skal beregnes afgift ud fra'),
        ),
        migrations.AddField(
            model_name='vareafgiftssats',
            name='segment_øvre',
            field=models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=10, null=True, verbose_name='Øvre grænse for mængden der skal beregnes afgift ud fra'),
        ),
        migrations.AlterField(
            model_name='vareafgiftssats',
            name='enhed',
            field=models.CharField(choices=[('ant', 'Antal'), ('kg', 'Kilogram'), ('l', 'Liter'), ('pct', 'Procent af fakturabeløb'), ('sam', 'Sammensat')], default='ant', max_length=3),
        ),
    ]
