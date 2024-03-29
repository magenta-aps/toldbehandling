# Generated by Django 4.2.2 on 2023-11-30 12:57

import anmeldelse.models
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sats', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('forsendelse', '0001_initial'),
        ('aktør', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Afgiftsanmeldelse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('leverandørfaktura_nummer', models.CharField(db_index=True, max_length=20)),
                ('leverandørfaktura', models.FileField(blank=True, null=True, upload_to=anmeldelse.models.afgiftsanmeldelse_upload_to)),
                ('modtager_betaler', models.BooleanField(default=False)),
                ('indførselstilladelse', models.CharField(blank=True, db_index=True, max_length=20, null=True)),
                ('afgift_total', models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ('betalt', models.BooleanField(default=False)),
                ('dato', models.DateField(auto_now_add=True, db_index=True)),
                ('status', models.CharField(choices=[('ny', 'ny'), ('afvist', 'afvist'), ('godkendt', 'godkendt'), ('afsluttet', 'afsluttet')], default='ny')),
                ('afsender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='afgiftsanmeldelser', to='aktør.afsender')),
                ('fragtforsendelse', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='afgiftsanmeldelse', to='forsendelse.fragtforsendelse')),
                ('modtager', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='afgiftsanmeldelser', to='aktør.modtager')),
                ('oprettet_af', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='afgiftsanmeldelser', to=settings.AUTH_USER_MODEL)),
                ('postforsendelse', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='afgiftsanmeldelse', to='forsendelse.postforsendelse')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Varelinje',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mængde', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('antal', models.PositiveIntegerField(blank=True, null=True)),
                ('fakturabeløb', models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('afgiftsbeløb', models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('afgiftsanmeldelse', simple_history.models.HistoricForeignKey(on_delete=django.db.models.deletion.CASCADE, to='anmeldelse.afgiftsanmeldelse')),
                ('vareafgiftssats', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sats.vareafgiftssats')),
            ],
            options={
                'ordering': ['vareafgiftssats'],
            },
        ),
        migrations.CreateModel(
            name='PrismeResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rec_id', models.BigIntegerField()),
                ('tax_notification_number', models.BigIntegerField()),
                ('invoice_date', models.DateTimeField()),
                ('afgiftsanmeldelse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='anmeldelse.afgiftsanmeldelse')),
            ],
        ),
        migrations.CreateModel(
            name='Notat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tekst', models.TextField()),
                ('oprettet', models.DateTimeField(auto_now_add=True)),
                ('index', models.PositiveSmallIntegerField(default=0)),
                ('afgiftsanmeldelse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='anmeldelse.afgiftsanmeldelse')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='HistoricalVarelinje',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('mængde', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('antal', models.PositiveIntegerField(blank=True, null=True)),
                ('fakturabeløb', models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('afgiftsbeløb', models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('afgiftsanmeldelse', simple_history.models.HistoricForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='anmeldelse.afgiftsanmeldelse')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('vareafgiftssats', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='sats.vareafgiftssats')),
            ],
            options={
                'verbose_name': 'historical varelinje',
                'verbose_name_plural': 'historical varelinjes',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalAfgiftsanmeldelse',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('leverandørfaktura_nummer', models.CharField(db_index=True, max_length=20)),
                ('leverandørfaktura', models.TextField(blank=True, max_length=100, null=True)),
                ('modtager_betaler', models.BooleanField(default=False)),
                ('indførselstilladelse', models.CharField(blank=True, db_index=True, max_length=20, null=True)),
                ('afgift_total', models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ('betalt', models.BooleanField(default=False)),
                ('dato', models.DateField(blank=True, db_index=True, editable=False)),
                ('status', models.CharField(choices=[('ny', 'ny'), ('afvist', 'afvist'), ('godkendt', 'godkendt'), ('afsluttet', 'afsluttet')], default='ny')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('afsender', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='aktør.afsender')),
                ('fragtforsendelse', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='forsendelse.fragtforsendelse')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('modtager', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='aktør.modtager')),
                ('oprettet_af', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('postforsendelse', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='forsendelse.postforsendelse')),
            ],
            options={
                'verbose_name': 'historical afgiftsanmeldelse',
                'verbose_name_plural': 'historical afgiftsanmeldelses',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
