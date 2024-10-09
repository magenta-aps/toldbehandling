# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from aktør.models import Afsender, Modtager
from anmeldelse.models import Afgiftsanmeldelse
from django.core.management.base import BaseCommand
from django.db.models.functions import Lower
from tabulate import tabulate


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("type", type=str)

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
        while key not in ("j", "n"):
            key = input(msg)
        return key.lower() == "j"

    def option(self, msg: str, options: list) -> int | None:
        print(msg)
        for i, o in enumerate(options):
            print(f"{i}: {o}")
        max = len(options) - 1
        choice = None
        while choice is None or choice > max:
            choice = input()
            if choice == "s":
                return None
            choice = int(choice) if choice.isdigit() else None
        return int(choice)

    def output(self, items):
        print(
            tabulate(
                items,
                headers={
                    "id": "id",
                    "navn": "Navn",
                    "adresse": "Adresse",
                    "postnummer": "Postnummer",
                    "eksplicit_stedkode": "Stedkode",
                    "by": "By",
                    "postbox": "Postbox",
                    "telefon": "Telefon",
                    "cvr": "CVR",
                },
            )
        )

    def handle(self, *args, **kwargs):
        aktørtype = kwargs["type"]
        if aktørtype == "afsender":
            cls = Afsender
        elif aktørtype == "modtager":
            cls = Modtager
        else:
            print(f"Invalid type '{aktørtype}', must be 'afsender' or 'modtager'")
            return
        qs = cls.objects.all()
        qs = (
            qs.annotate(lnavn=Lower("navn"))
            .order_by("lnavn")
            .distinct("lnavn")
            .values_list("lnavn", flat=True)
        )
        fields = (
            "navn",
            "adresse",
            "postnummer",
            "eksplicit_stedkode",
            "by",
            "postbox",
            "telefon",
            "cvr",
        )
        fields_with_id = ["id"] + list(fields)
        for item in qs:
            match_qs = cls.objects.filter(navn__iexact=item)
            new_values = {}
            count = match_qs.count()
            skip = False
            if count > 1:
                values = match_qs.values(*fields_with_id)
                print(f"\n{count} {aktørtype}e med navn {item}")
                self.output(values)
                for field in fields:
                    options = list(set([row[field] for row in values]))
                    if len(options) > 1:
                        choice = self.option(
                            f"Vælg {field}: (s for at overspringe)", options
                        )
                        if choice is None:
                            skip = True
                            break
                        value = options[choice]
                        new_values[field] = value
                    else:
                        new_values[field] = options[0]
                if skip:
                    continue

                self.output([{field: new_values.get(field) for field in fields}])
                if self.confirmation("Korrekt? (j/n) "):
                    master = match_qs.order_by("pk").first()
                    for k, v in new_values.items():
                        setattr(master, k, v)
                    master.save()

                    match_qs = match_qs.exclude(pk=master.pk)
                    tf10s = Afgiftsanmeldelse.objects.filter(
                        **{f"{aktørtype}__in": match_qs}
                    )
                    count = tf10s.count()
                    ids = [str(id) for id in tf10s.values_list("pk", flat=True)]
                    tf10s.update(**{aktørtype: master})
                    print(
                        f"Opdaterede {count} TF10s ({','.join(ids)}) til at pege på {aktørtype} {master.pk}"
                    )
                    ids = [str(id) for id in match_qs.values_list("pk", flat=True)]
                    match_qs.delete()
                    print(f"Slettede {len(ids)} {aktørtype}e ({','.join(ids)})")
