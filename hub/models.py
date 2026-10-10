from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, RegexValidator
from django.utils import timezone
from urllib.parse import quote
import uuid
from .images import optimize


class ValidatedModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Publication(ValidatedModel):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    publie = models.BooleanField(default=False)
    slug_fr = models.SlugField(max_length=200, blank=True, default="")
    slug_en = models.SlugField(max_length=200, blank=True, default="")
    premiere_publication = models.DateTimeField(null=True, blank=True, editable=False)
    cree_le = models.DateTimeField(default=timezone.now, editable=False)
    modifie_le = models.DateTimeField(auto_now=True)
    translated_fields = ()

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(fields=["slug_fr"], condition=~models.Q(slug_fr=""), name="%(class)s_slug_fr_unique"),
            models.UniqueConstraint(fields=["slug_en"], condition=~models.Q(slug_en=""), name="%(class)s_slug_en_unique"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.publie:
            for field in (*self.translated_fields, "slug"):
                for lang in ("fr", "en"):
                    name = f"{field}_{lang}"
                    if not getattr(self, name).strip():
                        errors[name] = "Traduction obligatoire pour publier."
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            if old and old.premiere_publication:
                for field in ("slug_fr", "slug_en", "premiere_publication"):
                    if getattr(old, field) != getattr(self, field):
                        errors[field] = "Valeur verrouillée après première publication."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.publie and not self.premiere_publication:
            self.premiere_publication = timezone.now()
        return models.Model.save(self, *args, **kwargs)

    def publish(self):
        self.publie = True
        self.save()

    def unpublish(self):
        self.publie = False
        self.save()


class Secteur(Publication):
    nom_fr = models.CharField(max_length=200, blank=True)
    nom_en = models.CharField(max_length=200, blank=True)
    description_fr = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    apprentissages_fr = models.TextField(blank=True)
    apprentissages_en = models.TextField(blank=True)
    prochaine_etape_fr = models.TextField(blank=True)
    prochaine_etape_en = models.TextField(blank=True)
    etat = models.CharField(max_length=20, default="preparation", choices=[("preparation", "En préparation"), ("actif", "Actif")])
    ordre = models.PositiveIntegerField(default=0)
    site_url = models.URLField(blank=True, validators=[URLValidator(schemes=["http", "https"])])
    translated_fields = ("nom", "description", "apprentissages", "prochaine_etape")

    class Meta(Publication.Meta):
        ordering = ["ordre", "pk"]
        verbose_name = "secteur"

    def __str__(self):
        return self.nom_fr or f"Secteur {self.pk} (brouillon)"


class Nouvelle(Publication):
    titre_fr = models.CharField(max_length=200, blank=True)
    titre_en = models.CharField(max_length=200, blank=True)
    corps_fr = models.TextField(blank=True)
    corps_en = models.TextField(blank=True)
    date_jalon = models.DateField(null=True, blank=True)
    image = models.ImageField(upload_to="nouvelles/", blank=True)
    alt_fr = models.CharField(max_length=250, blank=True)
    alt_en = models.CharField(max_length=250, blank=True)
    secteurs = models.ManyToManyField(Secteur, through="NouvelleSecteur", related_name="nouvelles", blank=True)
    translated_fields = ("titre", "corps")

    class Meta(Publication.Meta):
        ordering = ["-date_jalon", "-pk"]
        verbose_name = "nouvelle"

    def __str__(self):
        return self.titre_fr or f"Nouvelle {self.pk} (brouillon)"

    def clean(self):
        super().clean()
        if self.image and not self.image._committed:
            optimize(self.image.file)
        if self.publie:
            if not self.date_jalon:
                raise ValidationError({"date_jalon": "Date du jalon obligatoire."})
            if self.pk:
                for link in self.liens.all():
                    try:
                        link.validate_publication()
                    except ValidationError as exc:
                        raise ValidationError({"__all__": exc.messages}) from exc
            if self.image:
                errors = {field: "Alternative traduite obligatoire." for field in ("alt_fr", "alt_en")
                          if not getattr(self, field).strip()}
                if errors:
                    raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        old = type(self).objects.filter(pk=self.pk).values_list("image", flat=True).first() if self.pk else None
        uploaded = bool(self.image and not self.image._committed)
        if uploaded:
            self.image = optimize(self.image.file)
        try:
            result = super().save(*args, **kwargs)
        except Exception:
            if uploaded and self.image._committed:
                self.image.storage.delete(self.image.name)
            raise
        if old and old != self.image.name:
            schedule_image_cleanup(old, self.image.storage)
        return result


class NouvelleSecteur(models.Model):
    nouvelle = models.ForeignKey(Nouvelle, on_delete=models.CASCADE)
    secteur = models.ForeignKey(Secteur, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["nouvelle", "secteur"], name="nouvelle_secteur_unique")]


def schedule_image_cleanup(name, storage):
    def cleanup():
        from .database_versions import backup_image_referenced
        if not Nouvelle.objects.filter(image=name).exists() and not backup_image_referenced(name):
            storage.delete(name)
    transaction.on_commit(cleanup)


@receiver(post_delete, sender=Nouvelle)
def cleanup_deleted_image(sender, instance, **kwargs):
    if instance.image:
        schedule_image_cleanup(instance.image.name, instance.image.storage)


class LienNouvelle(ValidatedModel):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nouvelle = models.ForeignKey(Nouvelle, on_delete=models.CASCADE, related_name="liens")
    url = models.URLField(validators=[URLValidator(schemes=["http", "https"])])
    libelle_fr = models.CharField(max_length=200, blank=True)
    libelle_en = models.CharField(max_length=200, blank=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "pk"]
        verbose_name = "lien de nouvelle"

    def validate_publication(self):
        errors = {field: "Libellé traduit obligatoire." for field in ("libelle_fr", "libelle_en")
                  if not getattr(self, field).strip()}
        if errors:
            raise ValidationError(errors)

    def clean(self):
        super().clean()
        if self.nouvelle_id and Nouvelle.objects.filter(pk=self.nouvelle_id, publie=True).exists():
            self.validate_publication()


class ConfigurationGenerale(ValidatedModel):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    identite_fr = models.CharField(max_length=250)
    identite_en = models.CharField(max_length=250)
    resume_fr = models.TextField()
    resume_en = models.TextField()
    presentation_fr = models.TextField()
    presentation_en = models.TextField()
    parcours_fr = models.TextField()
    parcours_en = models.TextField()
    implantation_fr = models.CharField(max_length=250)
    implantation_en = models.CharField(max_length=250)
    email = models.EmailField()
    whatsapp = models.CharField(max_length=16, blank=True, default="", validators=[RegexValidator(r"^\+[1-9][0-9]{7,14}$", "Numéro international requis (+…).")])
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "configuration générale"
        verbose_name_plural = "configuration générale"
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="configuration_unique")]

    def clean(self):
        super().clean()
        errors = {}
        for field in self._meta.fields:
            if field.name.endswith(("_fr", "_en")) and not getattr(self, field.name).strip():
                errors[field.name] = "Texte obligatoire dans les deux langues."
        if self.pk != 1:
            errors["id"] = "Une seule configuration est autorisée."
        if self._state.adding and type(self).objects.exists():
            errors["__all__"] = "La configuration existe déjà."
        if errors:
            raise ValidationError(errors)

    @property
    def whatsapp_url(self):
        return "https://wa.me/" + self.whatsapp[1:] if self.whatsapp else ""

    @property
    def email_url(self):
        return "mailto:" + quote(self.email, safe="@.")


class DatabaseVersion(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="database_version_singleton")]
