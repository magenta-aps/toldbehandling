# Generated by Django 4.2.2 on 2023-12-14 14:41

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0002_alter_eboksbesked_cpr_alter_indberetterprofile_cpr'),
    ]

    operations = [
        migrations.AddField(
            model_name='indberetterprofile',
            name='api_key',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
