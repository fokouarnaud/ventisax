"""Serveur de démonstration isolé : aucun contenu ajouté à la base du projet."""
import argparse
import os
import sys
import tempfile
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_DEBUG"] = "1"
# Les variables du processus priment sur .env : un .env de production (hôte PythonAnywhere)
# ne doit pas faire refuser 127.0.0.1 par l'aperçu local.
os.environ["DJANGO_ALLOWED_HOSTS"] = "localhost,127.0.0.1"


def seed():
    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image, ImageDraw
    from hub.models import ConfigurationGenerale, Secteur, Nouvelle, LienNouvelle

    ConfigurationGenerale.objects.create(
        identite_fr="Un projet de groupe qui se construit.", identite_en="A group project taking shape.",
        resume_fr="Ventisax est un projet en formation autour de la climatisation, du froid et du matériel électronique. Suivez les étapes de sa préparation.",
        resume_en="Ventisax is a project in training, focused on air conditioning, refrigeration and electronic equipment. Follow its preparation, step by step.",
        presentation_fr="Exemple de présentation pour l’aperçu local. Ventisax est un projet informel de futur groupe. Cette interface ne présente aucune prestation ni vente actuellement disponible.",
        presentation_en="Sample presentation for the local preview. Ventisax is an informal project for a future group. This interface presents no currently available services or sales.",
        parcours_fr="Cet aperçu utilise des textes de démonstration. La formation, les apprentissages et les prochaines étapes permettront de raconter la progression réelle du projet.",
        parcours_en="This preview uses demonstration text. Training, learning and next steps will tell the story of the project’s actual progress.",
        implantation_fr="Yaoundé et ses environs · Cameroun", implantation_en="Yaoundé and surrounding areas · Cameroon",
        email="demo@example.com", whatsapp="+237699000000",
        tiktok_url="https://www.tiktok.com/@ventisax-demo", facebook_url="https://www.facebook.com/ventisax-demo",
        academie_url="https://acadventisax.pythonanywhere.com/",
    )
    cooling = Secteur.objects.create(nom_fr="Climatisation & froid", nom_en="Air conditioning & refrigeration",
        slug_fr="climatisation-froid", slug_en="air-conditioning-refrigeration",
        description_fr="Découvrir les systèmes de climatisation et de réfrigération, puis construire progressivement les connaissances du métier.",
        description_en="Explore air conditioning and refrigeration systems, then gradually build technical knowledge.",
        apprentissages_fr="Texte de démonstration : principes du froid, fonctionnement des équipements et sécurité.",
        apprentissages_en="Sample text: refrigeration principles, equipment operation and safety.",
        prochaine_etape_fr="Exemple de prochaine étape : documenter un premier jalon de formation réel.",
        prochaine_etape_en="Sample next step: document a first actual training milestone.", publie=True, ordre=0)
    electronics = Secteur.objects.create(nom_fr="Matériel électronique", nom_en="Electronic equipment",
        slug_fr="materiel-electronique", slug_en="electronic-equipment",
        description_fr="Explorer les équipements électroniques, leurs usages et les connaissances nécessaires pour un futur secteur dédié.",
        description_en="Explore electronic equipment, its uses and the knowledge needed for a future dedicated sector.",
        apprentissages_fr="Exemple de contenu : composants, lecture des caractéristiques et usages des équipements.",
        apprentissages_en="Sample content: components, specifications and equipment uses.",
        prochaine_etape_fr="Renseigner les premiers apprentissages réels avant le lancement.",
        prochaine_etape_en="Record the first actual learning milestones before launch.", publie=True, ordre=1)
    titles = [("Un aperçu du parcours de formation", "A preview of the training journey"),
              ("Préparer les premiers apprentissages techniques", "Preparing the first technical learning steps"),
              ("Structurer la préparation du projet", "Structuring the project preparation")]
    for index in range(12):
        title_fr, title_en = titles[index % len(titles)]
        n = Nouvelle.objects.create(titre_fr=title_fr if index < 3 else f"Exemple de jalon {index + 1}",
            titre_en=title_en if index < 3 else f"Sample milestone {index + 1}",
            corps_fr="Donnée fictive utilisée uniquement pour vérifier cette interface locale. Ce texte ne décrit aucune réalisation de Ventisax.\n\nLes véritables nouvelles seront rédigées et traduites par le porteur du projet avant publication.",
            corps_en="Sample data used only to check this local interface. This text describes no Ventisax achievement.\n\nActual news will be written and translated by the project founder before publication.",
            date_jalon=date(2026, 10, 10) - timedelta(days=index), slug_fr=f"exemple-{index + 1}",
            slug_en=f"sample-{index + 1}")
        n.secteurs.add(cooling)
        if index % 2:
            n.secteurs.add(electronics)
        if index == 0:
            canvas = Image.new("RGB", (900, 450), "#e6f1f1")
            draw = ImageDraw.Draw(canvas)
            for x in range(0, 900, 50):
                draw.line((x, 0, x, 450), fill="#ccdddd")
            for y in range(0, 450, 50):
                draw.line((0, y, 900, y), fill="#ccdddd")
            draw.rounded_rectangle((310, 90, 590, 360), radius=30, fill="#0b2d46")
            draw.line([(370, 170), (450, 300), (530, 170)], fill="#68ddce", width=15)
            draw.text((24, 24), "DEMONSTRATION / SAMPLE IMAGE", fill="#0b2d46")
            data = BytesIO()
            canvas.save(data, "PNG")
            n.image = SimpleUploadedFile("demo.png", data.getvalue())
            n.alt_fr = "Illustration de démonstration : un V sur une grille."
            n.alt_en = "Sample illustration: a V on a grid."
            n.video_youtube = "https://www.youtube.com/watch?v=M7lc1UVf-VE"  # vidéo publique de démonstration de Google
            n.instagram_url = "https://www.instagram.com/"
            n.facebook_url = "https://www.facebook.com/"
            n.save()
            LienNouvelle.objects.create(nouvelle=n, url="https://example.com", libelle_fr="Lien de démonstration", libelle_en="Sample link")
        n.publish()
    Secteur.objects.create(nom_fr="Secteur sans nouvelle (démonstration)", nom_en="Sector without news (sample)",
        slug_fr="sans-nouvelle", slug_en="without-news", description_fr="État vide de démonstration.",
        description_en="Sample empty state.", apprentissages_fr="Texte d’essai.", apprentissages_en="Sample text.",
        prochaine_etape_fr="Texte d’essai.", prochaine_etape_en="Sample text.", publie=True, ordre=2)


def seed_journal(directory):
    """Configuration et secteur réels minimaux, puis les fichiers sources du journal publiés tels quels."""
    from django.utils.text import slugify
    from hub import journal
    from hub.models import ConfigurationGenerale, Secteur
    ConfigurationGenerale.objects.create(
        identite_fr="Ventisax", identite_en="Ventisax",
        resume_fr="Aperçu local du Journal de formation.", resume_en="Local preview of the training log.",
        presentation_fr="Aperçu local.", presentation_en="Local preview.", parcours_fr="Aperçu local.",
        parcours_en="Local preview.", implantation_fr="Yaoundé et ses environs, Cameroun",
        implantation_en="Yaoundé and surrounding areas, Cameroon", email="demo@example.com")
    sources = [journal.parse_source(path.read_text(encoding="utf-8")) for path in sorted(Path(directory).rglob("*.md"))]
    for name in sorted({name for source in sources for name in source.secteurs}):
        Secteur.objects.create(nom_fr=name, nom_en=name, slug_fr=slugify(name), slug_en=f"{slugify(name)}-en",
                               description_fr="Aperçu.", description_en="Preview.", apprentissages_fr="Aperçu.",
                               apprentissages_en="Preview.", prochaine_etape_fr="Aperçu.", prochaine_etape_en="Preview.",
                               publie=True)
    for source in sources:
        journal.publier(source)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001, help="8000 est souvent pris par OpenShorts.")
    parser.add_argument("--empty", action="store_true", help="Prévisualiser le site sans configuration (503).")
    parser.add_argument("--journal", help="Dossier de fichiers sources du journal à prévisualiser, sans données fictives.")
    args = parser.parse_args()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connections
    import django
    with tempfile.TemporaryDirectory(prefix="ventisax-preview-") as directory:
        settings.DATABASES["default"]["NAME"] = Path(directory) / "db.sqlite3"
        settings.MEDIA_ROOT = Path(directory) / "media"
        settings.VENTISAX_PREVIEW = True
        settings.DEBUG = False
        django.setup()
        call_command("migrate", verbosity=0)
        if args.journal:
            seed_journal(args.journal)
        elif not args.empty:
            seed()
        from django.urls import re_path
        from django.views.static import serve
        from config import urls
        urls.urlpatterns.append(re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}))
        print(f"Aperçu isolé : http://127.0.0.1:{args.port}/fr/ (aucune donnée dans la base du projet)", flush=True)
        try:
            call_command("runserver", f"127.0.0.1:{args.port}", use_reloader=False, insecure=True)
        finally:
            connections.close_all()


if __name__ == "__main__":
    main()
