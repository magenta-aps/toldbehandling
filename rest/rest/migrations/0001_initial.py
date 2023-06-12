# Generated by Django 4.2.1 on 2023-06-12 13:22

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import rest.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Afgiftsanmeldelse',
            fields=[
                ('anmeldelsesnummer', models.PositiveBigIntegerField(primary_key=True, serialize=False)),
                ('leverandørfaktura_nummer', models.CharField(db_index=True, max_length=20)),
                ('leverandørfaktura', models.FileField(upload_to=rest.models.afgiftsanmeldelse_upload_to)),
                ('modtager_betaler', models.BooleanField(default=False)),
                ('indførselstilladelse', models.CharField(db_index=True, max_length=20)),
                ('afgift_total', models.DecimalField(decimal_places=2, max_digits=16)),
                ('betalt', models.BooleanField(default=False)),
                ('dato', models.DateField(auto_now_add=True, db_index=True)),
            ],
            options={
                'ordering': ['dato'],
            },
        ),
        migrations.CreateModel(
            name='Afgiftstabel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gyldig_fra', models.DateField(auto_now_add=True)),
                ('gyldig_til', models.DateField(null=True)),
                ('kladde', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['-gyldig_fra', '-gyldig_til'],
            },
        ),
        migrations.CreateModel(
            name='Afsender',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('navn', models.CharField(db_index=True, max_length=100)),
                ('adresse', models.CharField(max_length=100)),
                ('postnummer', models.PositiveSmallIntegerField(db_index=True)),
                ('by', models.CharField(db_index=True, max_length=20)),
                ('postbox', models.CharField(blank=True, max_length=10, null=True)),
                ('telefon', models.CharField(max_length=12)),
                ('cvr', models.IntegerField(blank=True, db_index=True, null=True, unique=True, validators=[django.core.validators.MinValueValidator(10000000), django.core.validators.MaxValueValidator(99999999)])),
            ],
            options={
                'ordering': ['navn'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Fragt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('forsendelsestype', models.CharField(choices=[('S', 'Skib'), ('F', 'Fly')], default='S', max_length=1)),
                ('fragtbrevsnummer', models.CharField(db_index=True, max_length=20)),
                ('fragtbrev', models.FileField(upload_to=rest.models.fragtbrev_upload_to)),
            ],
            options={
                'ordering': ['fragtbrevsnummer'],
            },
        ),
        migrations.CreateModel(
            name='Modtager',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('navn', models.CharField(db_index=True, max_length=100)),
                ('adresse', models.CharField(max_length=100)),
                ('postnummer', models.PositiveSmallIntegerField(db_index=True)),
                ('by', models.CharField(db_index=True, max_length=20)),
                ('postbox', models.CharField(blank=True, max_length=10, null=True)),
                ('telefon', models.CharField(max_length=12)),
                ('cvr', models.IntegerField(blank=True, db_index=True, null=True, unique=True, validators=[django.core.validators.MinValueValidator(10000000), django.core.validators.MaxValueValidator(99999999)])),
                ('kreditordning', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['navn'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('forsendelsestype', models.CharField(choices=[('S', 'Skib'), ('F', 'Fly')], default='S', max_length=1)),
                ('postforsendelsesnummer', models.CharField(db_index=True, max_length=20)),
            ],
            options={
                'ordering': ['postforsendelsesnummer'],
            },
        ),
        migrations.CreateModel(
            name='Vareafgiftssats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vareart', models.CharField(max_length=300)),
                ('afgiftsgruppenummer', models.PositiveIntegerField()),
                ('enhed', models.CharField(choices=[('ant', 'Antal'), ('kg', 'Kilogram'), ('l', 'Liter'), ('pct', 'Procent af fakturabeløb')], default='ant', max_length=3)),
                ('afgiftssats', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('afgiftstabel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rest.afgiftstabel')),
            ],
            options={
                'ordering': ['afgiftsgruppenummer'],
            },
        ),
        migrations.CreateModel(
            name='Varelinje',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kvantum', models.PositiveIntegerField()),
                ('fakturabeløb', models.DecimalField(decimal_places=2, max_digits=16)),
                ('afgiftsbeløb', models.DecimalField(decimal_places=2, max_digits=16)),
                ('afgiftsanmeldelse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rest.afgiftsanmeldelse')),
                ('afgiftssats', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rest.vareafgiftssats')),
            ],
            options={
                'ordering': ['afgiftssats'],
            },
        ),
        migrations.AddField(
            model_name='afgiftsanmeldelse',
            name='afsender',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='afgiftsanmeldelser', to='rest.afsender'),
        ),
        migrations.AddField(
            model_name='afgiftsanmeldelse',
            name='fragtforsendelse',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='afgiftsanmeldelse', to='rest.fragt'),
        ),
        migrations.AddField(
            model_name='afgiftsanmeldelse',
            name='modtager',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='afgiftsanmeldelser', to='rest.modtager'),
        ),
        migrations.AddField(
            model_name='afgiftsanmeldelse',
            name='postforsendelse',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='afgiftsanmeldelse', to='rest.post'),
        ),
        migrations.AddConstraint(
            model_name='vareafgiftssats',
            constraint=models.UniqueConstraint(fields=('afgiftstabel', 'vareart'), name='vareart_constraint'),
        ),
        migrations.AddConstraint(
            model_name='vareafgiftssats',
            constraint=models.UniqueConstraint(fields=('afgiftstabel', 'afgiftsgruppenummer'), name='afgiftsgruppenummer_constraint'),
        ),
    ]
