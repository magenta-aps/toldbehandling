# Generated by Django 4.2.11 on 2025-05-06 12:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0008_update_postnumbers'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='indberetterprofile',
            unique_together={('cpr', 'cvr')},
        ),
    ]
