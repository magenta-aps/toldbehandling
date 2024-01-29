from django.db import migrations

def set_afgiftsanmeldelse(apps, schema_editor):
    afgiftsanmeldelse = apps.get_model('anmeldelse', 'Afgiftsanmeldelse')
    for model in afgiftsanmeldelse.objects.all():
        model.betales_af = 'modtager' if model.modtager_betaler else 'afsender'
        model.save()

    history_afgiftsanmeldelse = apps.get_model('anmeldelse', 'HistoricalAfgiftsanmeldelse')
    for model in history_afgiftsanmeldelse.objects.all():
        model.betales_af = 'modtager' if model.modtager_betaler else 'afsender'
        model.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('anmeldelse', '0009_afgiftsanmeldelse_betales_af_and_more'),
    ]

    operations = [
        migrations.RunPython(set_afgiftsanmeldelse, noop),
        migrations.RemoveField(
            model_name='afgiftsanmeldelse',
            name='modtager_betaler',
        ),
        migrations.RemoveField(
            model_name='historicalafgiftsanmeldelse',
            name='modtager_betaler',
        ),
    ]