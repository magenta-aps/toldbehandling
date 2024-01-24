# Generated by Django 4.2.2 on 2024-01-23 12:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sats', '0004_alter_afgiftstabel_options'),
        ('aktør', '0002_alter_afsender_options_alter_modtager_options_and_more'),
        ('anmeldelse', '0005_alter_afgiftsanmeldelse_dato_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalvarelinje',
            name='kladde',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='varelinje',
            name='kladde',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='afgiftsanmeldelse',
            name='afsender',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='afgiftsanmeldelser', to='aktør.afsender'),
        ),
        migrations.AlterField(
            model_name='afgiftsanmeldelse',
            name='leverandørfaktura_nummer',
            field=models.CharField(blank=True, db_index=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='afgiftsanmeldelse',
            name='modtager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='afgiftsanmeldelser', to='aktør.modtager'),
        ),
        migrations.AlterField(
            model_name='afgiftsanmeldelse',
            name='status',
            field=models.CharField(choices=[('kladde', 'kladde'), ('ny', 'ny'), ('afvist', 'afvist'), ('godkendt', 'godkendt'), ('afsluttet', 'afsluttet')], default='ny'),
        ),
        migrations.AlterField(
            model_name='historicalafgiftsanmeldelse',
            name='leverandørfaktura_nummer',
            field=models.CharField(blank=True, db_index=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='historicalafgiftsanmeldelse',
            name='status',
            field=models.CharField(choices=[('kladde', 'kladde'), ('ny', 'ny'), ('afvist', 'afvist'), ('godkendt', 'godkendt'), ('afsluttet', 'afsluttet')], default='ny'),
        ),
        migrations.AlterField(
            model_name='varelinje',
            name='vareafgiftssats',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='sats.vareafgiftssats'),
        ),
        migrations.AddConstraint(
            model_name='afgiftsanmeldelse',
            constraint=models.CheckConstraint(check=models.Q(('afsender__isnull', False), ('status', 'kladde'), _connector='OR'), name='aktuel_har_afsender'),
        ),
        migrations.AddConstraint(
            model_name='afgiftsanmeldelse',
            constraint=models.CheckConstraint(check=models.Q(('modtager__isnull', False), ('status', 'kladde'), _connector='OR'), name='aktuel_har_modtager'),
        ),
        migrations.AddConstraint(
            model_name='afgiftsanmeldelse',
            constraint=models.CheckConstraint(check=models.Q(('leverandørfaktura_nummer__isnull', False), ('status', 'kladde'), _connector='OR'), name='aktuel_har_leverandørfaktura_nummer'),
        ),
        migrations.AddConstraint(
            model_name='varelinje',
            constraint=models.CheckConstraint(check=models.Q(('vareafgiftssats__isnull', False), ('kladde', True), _connector='OR'), name='aktuel_har_vareafgiftssats'),
        ),
    ]