# Generated by Django 4.2.2 on 2023-12-19 08:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('anmeldelse', '0003_privatafgiftsanmeldelse_oprettet_på_vegne_af_and_more'),
        ('common', '0003_indberetterprofile_api_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='eboksbesked',
            name='privat_afgiftsanmeldelse',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='anmeldelse.privatafgiftsanmeldelse'),
        ),
    ]
