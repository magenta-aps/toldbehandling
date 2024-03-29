# Generated by Django 4.2.2 on 2023-11-30 12:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Afgiftstabel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gyldig_fra', models.DateField(blank=True, null=True)),
                ('gyldig_til', models.DateField(blank=True, null=True)),
                ('kladde', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['-gyldig_fra', '-gyldig_til'],
            },
        ),
        migrations.CreateModel(
            name='Vareafgiftssats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vareart_da', models.CharField(max_length=300)),
                ('vareart_kl', models.CharField(blank=True, default='', max_length=300)),
                ('afgiftsgruppenummer', models.PositiveIntegerField()),
                ('enhed', models.CharField(choices=[('ant', 'Antal'), ('kg', 'Kilogram'), ('l', 'Liter'), ('pct', 'Procent af fakturabeløb'), ('sam', 'Sammensat')], default='ant', max_length=3)),
                ('afgiftssats', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('kræver_indførselstilladelse', models.BooleanField(default=False)),
                ('minimumsbeløb', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=10, null=True)),
                ('segment_nedre', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=10, null=True, verbose_name='Nedre grænse for mængden der skal beregnes afgift ud fra')),
                ('segment_øvre', models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=10, null=True, verbose_name='Øvre grænse for mængden der skal beregnes afgift ud fra')),
                ('afgiftstabel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sats.afgiftstabel')),
                ('overordnet', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='underordnede', to='sats.vareafgiftssats')),
            ],
            options={
                'ordering': ['afgiftsgruppenummer'],
            },
        ),
        migrations.AddConstraint(
            model_name='afgiftstabel',
            constraint=models.CheckConstraint(check=models.Q(('kladde', True), ('gyldig_fra__isnull', False), _connector='OR'), name='kladde_or_has_gyldig_fra'),
        ),
        migrations.AddConstraint(
            model_name='vareafgiftssats',
            constraint=models.UniqueConstraint(fields=('afgiftstabel', 'vareart_da'), name='vareart_constraint_da'),
        ),
        migrations.AddConstraint(
            model_name='vareafgiftssats',
            constraint=models.UniqueConstraint(fields=('afgiftstabel', 'vareart_kl'), name='vareart_constraint_kl'),
        ),
    ]
