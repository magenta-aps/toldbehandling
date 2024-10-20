# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from aktør.models import Afsender, Modtager
from anmeldelse.models import Afgiftsanmeldelse
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("type", type=str)
        parser.add_argument("id1", type=int)
        parser.add_argument("id2", type=int)

    def show_aktør(self, label, item):
        print(label)
        for field in (
            "navn",
            "adresse",
            "postnummer",
            "eksplicit_stedkode",
            "by",
            "postbox",
            "telefon",
            "cvr",
        ):
            print(f"    {field}: {getattr(item, field)}")

    def confirmation(self, msg):
        key = None
        while key not in ("y", "n"):
            key = input(msg)
        return key.lower() == "y"

    def handle(self, *args, **kwargs):
        aktørtype = kwargs["type"]
        id1 = kwargs["id1"]
        id2 = kwargs["id2"]
        if id1 == id2:
            print("The two ids may not be equal")
            return
        try:
            if aktørtype == "afsender":
                item1 = Afsender.objects.get(id=id1)
                item2 = Afsender.objects.get(id=id2)
            elif aktørtype == "modtager":
                item1 = Modtager.objects.get(id=id1)
                item2 = Modtager.objects.get(id=id2)
            else:
                print(f"Invalid type '{aktørtype}', must be 'afsender' or 'modtager'")
                return
        except (Afsender.DoesNotExist, Modtager.DoesNotExist) as e:
            print(e)
            return
        self.show_aktør("Kept item:", item1)
        self.show_aktør("Joined item:", item2)
        print(
            "Joined item will be deleted, "
            "and all its TF10s will be assigned to Kept item"
        )
        if self.confirmation("Continue? (y/n) "):
            qs = Afgiftsanmeldelse.objects.filter(**{aktørtype: item2})
            ids = list(qs.values_list("id", flat=True))
            qs.update(**{aktørtype: item1})
            item2.delete()
            print(f"Updated TF10 ids: {ids}")
            print(f"Deleted {aktørtype}: {id2}")
