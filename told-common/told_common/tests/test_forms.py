from django.test import TestCase
from told_common.forms import TF10Form


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
