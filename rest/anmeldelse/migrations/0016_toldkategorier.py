from django.db import migrations


def opdater_toldkategorier(apps, schema_editor):
    Toldkategori = apps.get_model("anmeldelse", "Toldkategori")
    Toldkategori.objects.filter(kategori__in=("72", "79", "90")).delete()
    Toldkategori.objects.filter(kategori="76").update(kræver_cvr=False)


class Migration(migrations.Migration):

    dependencies = [
        ('anmeldelse', '0015_afgiftsanmeldelse_tf3_and_more'),
    ]

    operations = [
        migrations.RunPython(opdater_toldkategorier)
    ]
