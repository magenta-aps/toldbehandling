import base64
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import CheckConstraint, Q
from lxml import etree


class IndberetterProfile(models.Model):
    class Meta:
        unique_together = (("cpr", "cvr"),)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=False, related_name="indberetter_data"
    )
    cpr = models.BigIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(101000000),
            MaxValueValidator(3112999999),
        ],
        db_index=True,
    )
    cvr = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(10000000), MaxValueValidator(99999999)],
        db_index=True,
    )

    @staticmethod
    def create_api_key():
        return uuid.uuid4()

    api_key = models.CharField(max_length=128, editable=False, unique=True)

    def __str__(self):
        return f"IndberetterProfile(user={self.user})"


class Postnummer(models.Model):
    postnummer = models.PositiveSmallIntegerField(
        db_index=True,
        validators=(
            MinValueValidator(1000),
            MaxValueValidator(9999),
        ),
        null=False,
    )
    navn = models.CharField(
        max_length=100,
        null=False,
    )
    dage = models.PositiveSmallIntegerField(
        null=False,
        default=0,
    )
    stedkode = models.PositiveSmallIntegerField(
        db_index=True,
        validators=(MinValueValidator(1), MaxValueValidator(500)),
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Postnummer(nr={self.postnummer}, navn={self.navn})"


class EboksBesked(models.Model):
    titel = models.CharField(max_length=500)
    cpr = models.BigIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(101000000),
            MaxValueValidator(3112999999),
        ],
        db_index=True,
    )
    cvr = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(10000000), MaxValueValidator(99999999)],
        db_index=True,
    )
    pdf = models.BinaryField()

    sendt = models.BooleanField(default=False)
    oprettet = models.DateTimeField(auto_now_add=True)
    opdateret = models.DateTimeField(auto_now=True)
    forsøg = models.PositiveSmallIntegerField(default=0)
    afgiftsanmeldelse = models.ForeignKey(
        "anmeldelse.Afgiftsanmeldelse", null=True, on_delete=models.SET_NULL
    )
    privat_afgiftsanmeldelse = models.ForeignKey(
        "anmeldelse.PrivatAfgiftsanmeldelse", null=True, on_delete=models.SET_NULL
    )

    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(cpr__isnull=False) | Q(cvr__isnull=False),
                name="has_cpr_or_cvr",
            )
        ]

    @property
    def content(self):
        root = etree.Element("Dispatch", xmlns="urn:eboks:en:3.0.0")

        recipient = etree.Element("DispatchRecipient")
        recipient_id = etree.Element("Id")
        if self.cvr is not None:
            recipient_id.text = str(self.cvr).zfill(8)
            recipient_type = "V"
        elif self.cpr is not None:
            recipient_id.text = str(self.cpr).zfill(10)
            recipient_type = "P"
        else:
            return None
        recipient.append(recipient_id)
        r_type = etree.Element("Type")
        r_type.text = recipient_type
        recipient.append(r_type)
        nationality = etree.Element("Nationality")
        nationality.text = "DK"
        recipient.append(nationality)
        root.append(recipient)

        content_type = etree.Element("ContentTypeId")
        content_type.text = str(settings.EBOKS["content_type_id"])
        root.append(content_type)

        title_element = etree.Element("Title")
        title_element.text = self.titel
        root.append(title_element)

        content = etree.Element("Content")
        data = etree.Element("Data")
        data.text = base64.b64encode(bytes(self.pdf))
        content.append(data)
        file_extension = etree.Element("FileExtension")
        file_extension.text = "pdf"
        content.append(file_extension)
        root.append(content)

        return etree.tostring(root, xml_declaration=True, encoding="UTF-8")

    def __str__(self):
        anmeldelse = self.afgiftsanmeldelse or self.privat_afgiftsanmeldelse
        return (
            f"EboksBesked(id={self.id}, "
            f"anmeldelse={anmeldelse.id if anmeldelse else None}, "
            f"oprettet={self.oprettet})"
        )


class EboksDispatch(models.Model):
    oprettet = models.DateTimeField(auto_now_add=True)
    opdateret = models.DateTimeField(auto_now=True)
    besked = models.ForeignKey(EboksBesked, null=False, on_delete=models.CASCADE)
    message_id = models.CharField(
        max_length=40,
        null=False,
    )
    status_code = models.PositiveSmallIntegerField(
        null=True,
    )
    status_message = models.CharField(max_length=500, null=True)

    def __str__(self):
        return f"EboksDispatch(besked={self.besked.id})"
