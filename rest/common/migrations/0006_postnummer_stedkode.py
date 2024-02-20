# Generated by Django 4.2.2 on 2024-02-19 07:31

from django.db import migrations


def set_postcode_ref(apps, schema_editor):
    Postnummer = apps.get_model("common", "Postnummer")
    postnumre = {item.postnummer: item for item in Postnummer.objects.all()}

    for model_navn in ("Modtager", "Afsender"):
        Aktør = apps.get_model('aktør', model_navn)
        for item in Aktør.objects.all():
            kode = item.postnummer
            if kode in postnumre:
                item.postnummer_ref = postnumre[kode]
                item.save(update_fields=["postnummer_ref"])

class Migration(migrations.Migration):

    dependencies = [
        ('common', '0005_postnummer_stedkode'),
    ]

    operations = [
        migrations.RunPython(set_postcode_ref),
    ]