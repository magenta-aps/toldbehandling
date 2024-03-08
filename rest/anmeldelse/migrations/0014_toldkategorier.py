# Generated by Django 4.2.2 on 2024-02-01 14:29

from django.db import migrations, models

kategorier = [
    {"kategori": "70", "navn": "RAL Royal Arctic Line A/S", "kræver_cvr": False},
    {
        "kategori": "71",
        "navn": "Forudbetalt indførselsafgift",
        "kræver_cvr": True,
    },
    {
        "kategori": "73A",
        "navn": "Kreditkunder Nan,Qaq,Nar,Kali,Qas,Nuu,Man,Sis,Nars",
        "kræver_cvr": True,
    },
    {
        "kategori": "73B",
        "navn": "Kreditkunder Kangaa,Aas,Qas,Ilu,Qeq",
        "kræver_cvr": True,
    },
    {
        "kategori": "73C",
        "navn": "Kreditkunder Uum,Uper",
        "kræver_cvr": True,
    },
    {
        "kategori": "73D",
        "navn": "Kreditkunder Tasiilaq,Kangerlussuaq",
        "kræver_cvr": True,
    },
    {
        "kategori": "73E",
        "navn": "Kreditkunder Ittoqqortoormiit,Qaanaq",
        "kræver_cvr": True,
    },
    {"kategori": "76", "navn": "Fra Tusass A/S"},
    {
        "kategori": "77",
        "navn": "Fra Skattestyrelsen",
        "kræver_cvr": True,
    },
    {
        "kategori": "79",
        "navn": "Refusion",
        "kræver_cvr": True,
    }
]

def opret_toldkategorier(apps, schema_editor):
    Toldkategori = apps.get_model("anmeldelse", "Toldkategori")
    for kategori in kategorier:
        Toldkategori.objects.create(**kategori)


class Migration(migrations.Migration):

    dependencies = [
        ('anmeldelse', '0013_toldkategori'),
    ]

    operations = [
        migrations.RunPython(opret_toldkategorier)
    ]