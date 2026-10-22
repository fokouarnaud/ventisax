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


def save_with_image(instance, field, save, *args, **kwargs):
    """Optimise une image nouvellement envoyée, puis planifie le nettoyage de celle qu'elle remplace."""
    old = type(instance).objects.filter(pk=instance.pk).values_list(field, flat=True).first() if instance.pk else None
    image = getattr(instance, field)
    uploaded = bool(image and not image._committed)
    if uploaded:
        setattr(instance, field, optimize(image.file))
        image = getattr(instance, field)
    try:
        result = save(*args, **kwargs)
    except Exception:
        if uploaded and image._committed:
            image.storage.delete(image.name)
        raise
    if old and old != image.name:
        schedule_image_cleanup(old, image.storage)
    return result


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
                "facebook_url": {"facebook.com", "www.facebook.com", "m.facebook.com", "fb.watch"},
                "youtube_channel_url": YOUTUBE_HOSTS,
                "tiktok_url": {"tiktok.com", "www.tiktok.com"}}
SOCIAL_NAMES = {"instagram_url": "Instagram", "facebook_url": "Facebook",
                "youtube_channel_url": "YouTube", "tiktok_url": "TikTok"}


def social_host_errors(obj, fields):
    """Erreurs pour les liens de réseaux renseignés hors du domaine attendu."""
    return {field: f"Lien attendu vers {SOCIAL_NAMES[field]}." for field in fields
            if getattr(obj, field) and urlsplit(getattr(obj, field)).hostname not in SOCIAL_HOSTS[field]}


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
    compte_rendu_fr = models.TextField("compte rendu de manipulation (fr)", blank=True,
                                       help_text="Une ligne par rubrique, « Rubrique : valeur » (Objet, Matériel, Déroulement, Durée).")
    compte_rendu_en = models.TextField("compte rendu de manipulation (en)", blank=True,
                                       help_text="One line per item, “Item: value” (Purpose, Equipment, Procedure, Duration).")
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

    def link_errors(self):
        """Vidéo YouTube unique et réseaux à domaine vérifié ; partagé avec la validation des bases importées."""
        errors = {}
        if self.video_youtube and not self.youtube_id:
            errors["video_youtube"] = "Lien d'une vidéo YouTube unique attendu (watch, shorts, embed ou youtu.be)."
        errors.update(social_host_errors(self, ("instagram_url", "facebook_url")))
        return errors

    def clean(self):
        super().clean()
        errors = self.link_errors()
        if errors:
            raise ValidationError(errors)
        if self.image and not self.image._committed:
            optimize(self.image.file)
        if self.publie:
            if not self.date_jalon:
                raise ValidationError({"date_jalon": "Date du jalon obligatoire."})
            if self.compte_rendu_fr.strip() or self.compte_rendu_en.strip():
                errors = missing_text(self, ("compte_rendu_fr", "compte_rendu_en"), "Compte rendu traduit obligatoire.")
                if errors:
                    raise ValidationError(errors)
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
        return save_with_image(self, "image", super().save, *args, **kwargs)


class NouvelleSecteur(models.Model):
    nouvelle = models.ForeignKey(Nouvelle, on_delete=models.CASCADE)
    secteur = models.ForeignKey(Secteur, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["nouvelle", "secteur"], name="nouvelle_secteur_unique")]


def schedule_image_cleanup(name, storage):
    def cleanup():
        from .database_versions import backup_image_referenced
        in_use = (Nouvelle.objects.filter(image=name).exists()
                  or ConfigurationGenerale.objects.filter(image_accueil=name).exists())
        if not in_use and not backup_image_referenced(name):
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
    youtube_channel_url = models.URLField("chaîne YouTube", blank=True, validators=[HTTP_URL])
    instagram_url = models.URLField("profil Instagram", blank=True, validators=[HTTP_URL])
    facebook_url = models.URLField("page Facebook", blank=True, validators=[HTTP_URL])
    tiktok_url = models.URLField("profil TikTok", blank=True, validators=[HTTP_URL])
    academie_url = models.URLField("adresse de l'Académie", blank=True, validators=[HTTP_URL],
                                   help_text="Espace de révision (cours, quiz) ; vide, aucun renvoi n'est affiché.")
    profile_fields = ("youtube_channel_url", "facebook_url", "tiktok_url", "instagram_url")
    image_accueil = models.ImageField("image d'accueil", upload_to="accueil/", blank=True,
                                      help_text="Photo réelle et publiable (2 Mio max). La remplacer supprime la précédente ; "
                                                "sans image, le logo s'affiche.")
    alt_accueil_fr = models.CharField("alternative (fr)", max_length=250, blank=True)
    alt_accueil_en = models.CharField("alternative (en)", max_length=250, blank=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "configuration générale"
        verbose_name_plural = "configuration générale"
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="configuration_unique")]

    def clean(self):
        super().clean()
        errors = missing_text(self, self.required_texts(), "Texte obligatoire dans les deux langues.")
        errors.update(social_host_errors(self, self.profile_fields))
        if self.image_accueil:
            errors.update(missing_text(self, ("alt_accueil_fr", "alt_accueil_en"), "Alternative traduite obligatoire."))
            if not self.image_accueil._committed:
                try:
                    optimize(self.image_accueil.file)
                except ValidationError as exc:
                    errors["image_accueil"] = exc.message_dict["image"]
        if self.pk != 1:
            errors["id"] = "Une seule configuration est autorisée."
        if self._state.adding and type(self).objects.exists():
            errors["__all__"] = "La configuration existe déjà."
        if errors:
            raise ValidationError(errors)

    @classmethod
    def required_texts(cls):
        """Textes bilingues toujours obligatoires ; les alternatives de l'image ne le sont qu'avec une image."""
        return [f.name for f in cls._meta.fields if f.name.endswith(("_fr", "_en")) and not f.name.startswith("alt_accueil")]

    def save(self, *args, **kwargs):
        self.full_clean()
        return save_with_image(self, "image_accueil", super().save, *args, **kwargs)

    @property
    def whatsapp_url(self):
        return "https://wa.me/" + self.whatsapp[1:] if self.whatsapp else ""

    @property
    def email_url(self):
        return "mailto:" + quote(self.email, safe="@.")

    def whatsapp_text_url(self, message):
        return f"{self.whatsapp_url}?text={quote(message, safe='')}" if self.whatsapp else ""

    def email_text_url(self, subject, message):
        return f"{self.email_url}?subject={quote(subject, safe='')}&body={quote(message, safe='')}"

    def notify_url(self, message, subject):
        """Lien « Me prévenir » : WhatsApp pré-rempli, sinon e-mail pré-rempli."""
        return self.whatsapp_text_url(message) or self.email_text_url(subject, message)


class DatabaseVersion(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="database_version_singleton")]
