from typing import Dict, Optional

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from told_common.data import Vareafgiftssats
from told_common.forms import TF10Form, TF10VareForm


class TF10FormTest(TestCase):
    maxDiff = False

    def test_klasse_fjern_required(self):
        form = TF10Form(data={"kladde": True, "some_field": "abc"})
        form.is_valid()  # bind form and populate field data
        form.klasse_fjern_required()

        for _, field in form.fields.items():
            self.assertFalse(field.required)

    def test_clean_errors(self):
        # Make a form instanse which will fail in validation
        form = TF10Form(
            fragtbrev_required=True,
            # NOTE: We add these default data, since our clean methods fails with
            #       KeyError, if these are not supplied
            data={
                "fragttype": "skibsfragt",
                "forbindelsesnr": "abc",
                "fragtbrevnr": "def",
            },
        )
        self.assertFalse(form.is_valid())

        # Aseert required field errors
        for required_field in [
            "afsender_navn",
            "afsender_adresse",
            "afsender_postnummer",
            "afsender_by",
            "modtager_navn",
            "modtager_adresse",
            "modtager_postnummer",
            "modtager_by",
            "leverand\u00f8rfaktura_nummer",
            "leverand\u00f8rfaktura",
            "afgangsdato",
        ]:
            self.assertIn(required_field, form.errors)
            self.assertEqual(
                form.errors[required_field].as_text(),
                "* Dette felt er p\u00e5kr\u00e6vet.",
            )

        # Aseert other fields
        self.assertIn("fragtbrev", form.errors)
        self.assertEqual(form.errors["fragtbrev"].as_text(), "* Mangler fragtbrev")

        self.assertIn("forbindelsesnr", form.errors)
        self.assertEqual(
            form.errors["forbindelsesnr"].as_text(),
            (
                "* Ved skibsfragt skal forbindelsesnummer best\u00e5 af "
                "tre bogstaver, mellemrum og tre cifre"
            ),
        )

        self.assertIn("fragtbrevnr", form.errors)
        self.assertEqual(
            form.errors["fragtbrevnr"].as_text(),
            (
                "* Ved skibsfragt skal fragtbrevnr best\u00e5 af "
                "fem bogstaver efterfulgt af syv cifre"
            ),
        )

        # check again, but using "luftfragt"
        form = TF10Form(
            fragtbrev_required=True,
            data={
                "fragttype": "luftfragt",
                "forbindelsesnr": "abc",
                "fragtbrevnr": "def",
            },
        )

        self.assertFalse(form.is_valid())

        self.assertIn("forbindelsesnr", form.errors)
        self.assertEqual(
            form.errors["forbindelsesnr"].as_text(),
            "* Ved luftfragt skal forbindelsesnummer bestå af tre cifre",
        )

        self.assertIn("fragtbrevnr", form.errors)
        self.assertEqual(
            form.errors["fragtbrevnr"].as_text(),
            "* Ved luftfragt skal fragtbrevnummer bestå af otte cifre",
        )

    def test_clean_with_formset(self):
        form = TF10FormTest.create_TF10Form(
            varesatser={
                1: Vareafgiftssats(
                    id=1,
                    afgiftstabel=1,
                    vareart_da="Båthorn Snaps",
                    vareart_kl="Båthorn Snaps",
                    afgiftsgruppenummer=12345678,
                    enhed=Vareafgiftssats.Enhed.KILOGRAM,
                    afgiftssats="1.00",
                    kræver_indførselstilladelse_alkohol=True,
                    kræver_indførselstilladelse_tobak=False,
                ),
            }
        )
        self.assertTrue(form.is_valid())

        subform = TF10VareForm(
            varesatser=form.varesatser,
            data={"vareafgiftssats": 1, "mængde": 2},
        )
        subform.is_valid()

        form.clean_with_formset(formset=[subform])
        self.assertIn("indførselstilladelse_alkohol", form.errors)

    @staticmethod
    def create_TF10Form(
        varesatser: Optional[Dict] = None, kladde: Optional[bool] = None
    ):
        return TF10Form(
            varesatser=(
                varesatser
                if varesatser
                else {
                    1: Vareafgiftssats(
                        id=1,
                        afgiftstabel=1,
                        vareart_da="Båthorn",
                        vareart_kl="Båthorn",
                        afgiftsgruppenummer=12345678,
                        enhed=Vareafgiftssats.Enhed.KILOGRAM,
                        afgiftssats="1.00",
                        kræver_indførselstilladelse_alkohol=False,
                        kræver_indførselstilladelse_tobak=False,
                        har_privat_tillægsafgift_alkohol=False,
                    ),
                    2: Vareafgiftssats(
                        id=2,
                        afgiftstabel=1,
                        vareart_da="Klovnesko",
                        vareart_kl="Klovnesko",
                        afgiftsgruppenummer=87654321,
                        enhed=Vareafgiftssats.Enhed.ANTAL,
                        afgiftssats="1.00",
                        kræver_indførselstilladelse_alkohol=False,
                        kræver_indførselstilladelse_tobak=False,
                        har_privat_tillægsafgift_alkohol=False,
                    ),
                    3: Vareafgiftssats(
                        id=3,
                        afgiftstabel=1,
                        vareart_da="Ethjulede cykler",
                        vareart_kl="Ethjulede cykler",
                        afgiftsgruppenummer=22446688,
                        enhed=Vareafgiftssats.Enhed.PROCENT,
                        afgiftssats="0.50",
                        kræver_indførselstilladelse_alkohol=False,
                        kræver_indførselstilladelse_tobak=False,
                        har_privat_tillægsafgift_alkohol=False,
                    ),
                }
            ),
            data={
                "afsender_cvr": "12345678",
                "afsender_navn": "TestFirma1",
                "afsender_adresse": "Testvej 42",
                "afsender_postnummer": "1234",
                "afsender_by": "TestBy",
                "afsender_postbox": "123",
                "afsender_telefon": "123456",
                "modtager_cvr": "12345679",
                "modtager_navn": "TestFirma2",
                "modtager_adresse": "Testvej 43",
                "modtager_postnummer": "1234",
                "modtager_by": "TestBy",
                "modtager_postbox": "124",
                "modtager_telefon": "123123",
                # To verify clean_with_formset later
                "indførselstilladelse_alkohol": None,
                "indførselstilladelse_tobak": None,
                "leverandørfaktura_nummer": "123",
                "fragttype": "skibsfragt",
                "fragtbrevnr": "ABCDE1234567",
                "afgangsdato": "2023-11-03",
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "1",
                "form-0-vareafgiftssats": "1",
                "form-0-mængde": "3",
                "form-0-antal": "6",
                "form-0-fakturabeløb": "100.00",
                "forbindelsesnr": "ABC 337",
                "betales_af": "afsender",
                "leverandørfaktura": None,
                "fragtbrev": None,
                "kladde": kladde if kladde else False,
            },
            files={
                "fragtbrev": SimpleUploadedFile(
                    "fragtbrev.txt", b"\x00" * (5 * 1024 * 1024)  # 5MB
                ),
                "leverandørfaktura": SimpleUploadedFile(
                    "leverandørfaktura.txt", b"\x00" * (5 * 1024 * 1024)  # 5MB
                ),
            },
        )


class TF10VareFormTest(TestCase):
    def test_kladde_parent_from_parent(self):
        tf10_form = TF10FormTest.create_TF10Form(kladde=True)
        self.assertTrue(tf10_form.is_valid())

        form = TF10VareForm(
            varesatser=tf10_form.varesatser,
            data={"vareafgiftssats": 1, "mængde": 2},
        )
        self.assertTrue(form.is_valid())

        form.set_parent_form(tf10_form)
        self.assertTrue(form.kladde)
