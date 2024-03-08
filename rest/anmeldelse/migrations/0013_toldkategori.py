# Generated by Django 4.2.2 on 2024-03-08 11:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anmeldelse', '0012_alter_historicalvarelinje_mængde_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Toldkategori',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kategori', models.CharField(max_length=3)),
                ('navn', models.CharField(max_length=300)),
                ('kræver_cvr', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['kategori'],
            },
        ),
    ]