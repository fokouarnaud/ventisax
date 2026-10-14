from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, RegexValidator
from django.utils import timezone
from urllib.parse import parse_qs, quote, urlsplit
import re
import uuid
from .images import optimize


HTTP_URL = URLValidator(schemes=["http", "https"])


def missing_text(obj, fields, message):
    """Erreurs de validation pour les champs texte vides ou faits d'espaces."""
    return {field: message for field in fields if not getattr(obj, field).strip()}


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
            errors.update(missing_text(self, [f"{field}_{lang}" for field in (*self.translated_fields, "slug")
                                              for lang in ("fr", "en")], "Traduction obligatoire pour publier."))
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
    site_url = models.URLField(blank=True, validators=[HTTP_URL])
    translated_fields = ("nom", "description", "apprentissages", "prochaine_etape")

    class Meta(Publication.Meta):
        ordering = ["ordre", "pk"]
        verbose_name = "secteur"

    def __str__(self):
        return self.nom_fr or f"Secteur {self.pk} (brouillon)"


YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}
YOUTUBE_ID = re.compile(r"[A-Za-z0-9_-]{11}")
SOCIAL_HOSTS = {"instagram_url": {"instagram.com", "www.instagram.com"},
                "facebook_url": {"facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch"}}


def youtube_video_id(url):
    """ID d'une vidéo YouTube (11 caractères) ou chaîne vide si l'URL n'en désigne pas une seule."""
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    if parts.scheme not in ("http", "https") or "list" in query:
        return ""
    host, segments = parts.hostname or "", [s for s in parts.path.split("/") if s]
    if host == "youtu.be" and len(segments) == 1:
        candidate = segments[0]
    elif host in YOUTUBE_HOSTS and segments == ["watch"]:
        candidate = query.get("v", [""])[0]
    elif host in YOUTUBE_HOSTS and len(segments) == 2 and segments[0] in ("shorts", "embed"):
        candidate = segments[1]
    else:
        return ""
    return candidate if YOUTUBE_ID.fullmatch(candidate) else ""


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
    video_youtube = models.URLField("vidéo YouTube", blank=True,
                                    validators=[HTTP_URL],
                                    help_text="Vidéo non répertoriée ou publique (une vidéo privée ne se lit pas).")
    instagram_url = models.URLField("lien Instagram", blank=True, validators=[HTTP_URL])
    facebook_url = models.URLField("lien Facebook", blank=True, validators=[HTTP_URL])
    translated_fields = ("titre", "corps")

    class Meta(Publication.Meta):
        ordering = ["-date_jalon", "-pk"]
        verbose_name = "nouvelle"

    def __str__(self):
        return self.titre_fr or f"Nouvelle {self.pk} (brouillon)"

    @property
    def youtube_id(self):
        return youtube_video_id(self.video_youtube) if self.video_youtube else ""

    def clean(self):
        super().clean()
        errors = {}
        if self.video_youtube and not self.youtube_id:
            errors["video_youtube"] = "Lien d'une vidéo YouTube unique attendu (watch, shorts, embed ou youtu.be)."
        for field, hosts in SOCIAL_HOSTS.items():
            value = getattr(self, field)
            if value and urlsplit(value).hostname not in hosts:
                errors[field] = "Lien attendu vers " + ("Instagram." if field == "instagram_url" else "Facebook.")
        if errors:
            raise ValidationError(errors)
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
                errors = missing_text(self, ("alt_fr", "alt_en"), "Alternative traduite obligatoire.")
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
    url = models.URLField(validators=[HTTP_URL])
    libelle_fr = models.CharField(max_length=200, blank=True)
    libelle_en = models.CharField(max_length=200, blank=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "pk"]
        verbose_name = "lien de nouvelle"

    def validate_publication(self):
        errors = missing_text(self, ("libelle_fr", "libelle_en"), "Libellé traduit obligatoire.")
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
        errors = missing_text(self, [f.name for f in self._meta.fields if f.name.endswith(("_fr", "_en"))],
                              "Texte obligatoire dans les deux langues.")
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
