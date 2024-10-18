# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import re

from aktør.models import Afsender, Modtager
from anmeldelse.models import Afgiftsanmeldelse
from django.core.management.base import BaseCommand
from django.db.models.functions import Lower
from tabulate import tabulate


class Command(BaseCommand):

    omit_cvrs = {
        17516345,  # Tusass
        40516611,  # Blue water
    }

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

    def confirmation(self, msg, allow_skip=False):
        while True:
            key = input(msg).lower()
            if key == "j":
                return True
            if key == "n":
                return False
            if allow_skip and key == "s":
                return None

    def option(self, msg: str, options: list) -> int | None:
        print(msg)
        for i, o in enumerate(options):
            print(f"{i}: {o}")
        max = len(options) - 1
        while True:
            choice = input("Valg: ")
            if choice == "s":
                return None
            elif choice is None or not choice.isdigit() or int(choice) > max:
                print("Ikke en valgmulighed")
            else:
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
                    "kreditordning": "Kreditordning",
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
        qs = (
            cls.objects.all()
            .annotate(lnavn=Lower("navn"))
            .order_by("lnavn")
            .distinct("lnavn")
            .values_list("lnavn", flat=True)
        )

        for item in qs:
            match_qs = cls.objects.filter(navn__iexact=item)
            match_qs = match_qs.exclude(cvr__in=self.omit_cvrs)
            count = match_qs.count()
            if count > 1:
                print(f"\n{count} {aktørtype}e med navn {item}")
                self.handle_group(match_qs, aktørtype)

    def handle_group(self, match_qs, aktørtype):
        fields = [
            "navn",
            "adresse",
            "postnummer",
            "eksplicit_stedkode",
            "by",
            "postbox",
            "telefon",
            "cvr",
        ]
        if aktørtype == "modtager":
            fields.append("kreditordning")
        fields_with_id = ["id"] + list(fields)
        while True:  # loop indtil skip eller update
            new_values = {}
            filtered_match_qs = match_qs  # Hvis vi looper mere end en gang,
            # tag udgangspunkt i originalen
            values = list(filtered_match_qs.values(*fields_with_id))

            self.output(values)
            omit_pks = set()
            while do_omit := self.confirmation(
                "Udelad nogle? (j/n) (s for at overspringe) ", allow_skip=True
            ):
                omit_str = input("Skriv id på dem der ikke skal merges: ")
                omit = re.split(r"[\s,]", omit_str)
                for o in omit:
                    if o.isdigit():
                        omit_pks.add(int(o))
                filtered_match_qs = filtered_match_qs.exclude(id__in=omit_pks)
                values = list(filtered_match_qs.values(*fields_with_id))
                self.output(values)
                if filtered_match_qs.count() <= 1:
                    print(
                        f"Kun {filtered_match_qs.count()} tilbage i gruppen. "
                        f"Overspringer"
                    )
                    return  # Der er udeladt så mange at vi kun har 0 eller 1 tilbage
            if do_omit is None:
                return  # Skip til næste gruppe

            for field in fields:
                options = list(set([row[field] for row in values]))
                options.sort(key=lambda x: "" if x is None else str(x))
                if len(options) > 1:
                    choice = self.option(
                        f"Vælg {field}: (s for at overspringe)", options
                    )
                    if choice is None:  # overspring denne gruppe
                        return
                    value = options[choice]
                    new_values[field] = value
                else:
                    new_values[field] = options[0]

            self.output([{field: new_values.get(field) for field in fields}])
            if self.confirmation("Korrekt? (j/n) "):
                master = filtered_match_qs.order_by("pk").first()
                for k, v in new_values.items():
                    setattr(master, k, v)
                master.save()
                print(f"Opdaterede {aktørtype} {master.pk} med ovenstående data")

                filtered_match_qs = filtered_match_qs.exclude(pk=master.pk)
                tf10s = Afgiftsanmeldelse.objects.filter(
                    **{f"{aktørtype}__in": filtered_match_qs}
                )
                count = tf10s.count()
                ids = [str(id) for id in tf10s.values_list("pk", flat=True)]
                tf10s.update(**{aktørtype: master})
                Afgiftsanmeldelse.history.filter(
                    **{f"{aktørtype}__in": filtered_match_qs}
                ).update(**{aktørtype: master})
                print(
                    f"Opdaterede {count} anmeldelse{'r' if len(ids) > 1 else ''} "
                    f"({','.join(ids)}) til at pege på {aktørtype} {master.pk}"
                )

                ids = [str(id) for id in filtered_match_qs.values_list("pk", flat=True)]
                filtered_match_qs.delete()
                print(
                    f"Slettede {len(ids)} {aktørtype}{'e' if len(ids) > 1 else ''} "
                    f"({','.join(ids)})"
                )
                return
