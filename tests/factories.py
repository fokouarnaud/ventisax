from datetime import date
from hub import models


def secteur(slug="froid", **overrides):
    values = {f"{field}_{lang}": f"{field} {lang}" for field in
              ("nom", "description", "apprentissages", "prochaine_etape") for lang in ("fr", "en")}
    values.update(slug_fr=slug, slug_en=f"{slug}-en")
    values.update(overrides)
    return models.Secteur.objects.create(**values)


def nouvelle(slug="formation", **overrides):
    values = dict(titre_fr="Formation réelle", titre_en="Actual training", corps_fr="Étape de formation",
                  corps_en="Training milestone", slug_fr=slug, slug_en=f"{slug}-en", date_jalon=date(2026, 10, 1))
    values.update(overrides)
    return models.Nouvelle.objects.create(**values)


def configuration(**overrides):
    values = {f"{field}_{lang}": f"Texte réel {lang}" for field in
              ("identite", "resume", "presentation", "parcours", "implantation") for lang in ("fr", "en")}
    values.update(email="contact@example.com", whatsapp="+237699123456")
    values.update(overrides)
    return models.ConfigurationGenerale.objects.create(**values)
