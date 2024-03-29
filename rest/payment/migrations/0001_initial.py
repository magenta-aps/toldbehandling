# Generated by Django 4.2.2 on 2023-12-20 12:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('anmeldelse', '0003_privatafgiftsanmeldelse_oprettet_på_vegne_af_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.IntegerField()),
                ('currency', models.CharField(max_length=3)),
                ('reference', models.CharField(max_length=128, null=True)),
                ('provider_host', models.CharField(max_length=128, null=True)),
                ('provider_payment_id', models.CharField(max_length=128, null=True)),
                ('status', models.CharField(max_length=128, null=True)),
                ('declaration', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='payments', to='anmeldelse.privatafgiftsanmeldelse')),
            ],
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(max_length=128)),
                ('name', models.CharField()),
                ('quantity', models.IntegerField()),
                ('unit', models.CharField(max_length=128)),
                ('unit_price', models.IntegerField()),
                ('tax_rate', models.IntegerField(default=0)),
                ('tax_amount', models.IntegerField(default=0)),
                ('gross_total_amount', models.IntegerField()),
                ('net_total_amount', models.IntegerField()),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='payment.payment')),
            ],
        ),
    ]
