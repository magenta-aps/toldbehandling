# Generated by Django 4.2.1 on 2023-06-22 07:52

from django.db import migrations, models
import forsendelse.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Fragtforsendelse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('forsendelsestype', models.CharField(choices=[('S', 'Skib'), ('F', 'Fly')], default='S', max_length=1)),
                ('fragtbrevsnummer', models.CharField(db_index=True, max_length=20)),
                ('fragtbrev', models.FileField(blank=True, null=True, upload_to=forsendelse.models.fragtbrev_upload_to)),
                ('forbindelsesnr', models.CharField(db_index=True, max_length=100)),
            ],
            options={
                'ordering': ['fragtbrevsnummer'],
            },
        ),
        migrations.CreateModel(
            name='Postforsendelse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('forsendelsestype', models.CharField(choices=[('S', 'Skib'), ('F', 'Fly')], default='S', max_length=1)),
                ('postforsendelsesnummer', models.CharField(db_index=True, max_length=20)),
                ('afsenderbykode', models.CharField(db_index=True, max_length=4)),
            ],
            options={
                'ordering': ['postforsendelsesnummer'],
            },
        ),
    ]
