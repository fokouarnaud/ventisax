"""Rubrique « Projets » du hub (PRD du 18 novembre 2026, US-42 à US-45, règles RP-09 à RP-11)."""
import html
from datetime import date

import pytest
from django.core.exceptions import ValidationError

from hub import models
from tests.test_admin import admin_user, verified_client  # noqa: F401 (fixtures)


pytestmark = pytest.mark.django_db


def projet(slug="chambre-froide", **overrides):
    values = {f"{field}_{lang}": f"{field} {lang}" for field in ("titre", "resume", "problematique", "objectifs")
              for lang in ("fr", "en")}
    values.update(slug_fr=slug, slug_en=f"{slug}-en", statut="conception", date_debut=date(2026, 11, 18))
    values.update(overrides)
    return models.Projet.objects.create(**values)


def etape(p, ordre=0, **overrides):
    values = dict(projet=p, libelle_fr="Validation du dossier", libelle_en="File approval", date=date(2026, 12, 1),
                  etat="a_venir", ordre=ordre)
    values.update(overrides)
    return models.EtapeProjet.objects.create(**values)


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def pages(monkeypatch, tmp_path):
    folder = tmp_path / "projets"
    folder.mkdir()
    (folder / "cycle.html").write_text("<!doctype html>", encoding="utf-8")
    monkeypatch.setattr(models, "FIGURES_INTERACTIVES_DIR", folder)
    return folder


def image_file(size=(2000, 1000)):
    from io import BytesIO
    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile
    stream = BytesIO()
    Image.new("RGB", size, "blue").save(stream, "PNG")
    return SimpleUploadedFile("figure.png", stream.getvalue(), content_type="image/png")


def figure(p, **overrides):
    values = dict(projet=p, image=image_file(), alt_fr="Vue éclatée", alt_en="Exploded view",
                  legende_fr="Vue éclatée", legende_en="Exploded view")
    values.update(overrides)
    return models.FigureProjet.objects.create(**values)


def page(client, path, status=200):
    response = client.get(path)
    assert response.status_code == status, path
    return html.unescape(response.content.decode())


def publie(**overrides):
    from tests.factories import configuration
    if not models.ConfigurationGenerale.objects.exists():
        configuration()
    p = projet(**overrides)
    p.publish()
    return p


# --- Modèle de données : Projet (US-45) ---------------------------------------------------------------------

def test_projet_complet_se_publie_dans_les_deux_langues():
    p = projet()
    p.publish()
    p.refresh_from_db()
    assert p.publie and p.premiere_publication is not None


def test_projet_incomplet_ne_se_publie_pas():
    p = projet(problematique_en="   ")
    with pytest.raises(ValidationError) as exc:
        p.publish()
    assert "problematique_en" in exc.value.message_dict


def test_resultats_facultatifs_mais_traduits_a_la_publication():
    p = projet()
    p.publish()  # sans résultats : publiable (RP-09, aucun résultat avant mesure)
    p.resultats_fr = "Descente à +4 °C en 1 h 40."
    with pytest.raises(ValidationError) as exc:
        p.save()
    assert "resultats_en" in exc.value.message_dict


def test_date_de_fin_anterieure_au_debut_refusee():
    with pytest.raises(ValidationError) as exc:
        projet(date_fin=date(2026, 11, 1))
    assert "date_fin" in exc.value.message_dict


def test_secteur_associe_a_un_projet_non_supprimable():
    from django.db.models import ProtectedError
    from tests.factories import secteur
    s = secteur()
    p = projet()
    models.ProjetSecteur.objects.create(projet=p, secteur=s)
    assert list(p.secteurs.all()) == [s]
    with pytest.raises(ProtectedError):
        s.delete()


def test_binome_et_ordre_ont_des_valeurs_par_defaut():
    p = projet()
    assert p.binome == "" and p.accord_binome is False and p.ordre == 0


# --- Modèle de données : étapes, figures, nouvelles liées (US-43 à US-45) ------------------------------------

def test_etapes_ordonnees_par_ordre_puis_creation():
    p = projet()
    deux = etape(p, ordre=2, libelle_fr="Essais")
    un = etape(p, ordre=1, libelle_fr="Achat T1")
    autre = etape(p, ordre=1, libelle_fr="Achat T0")
    assert list(p.etapes.all()) == [un, autre, deux]


def test_etape_non_traduite_bloque_la_publication_du_projet():
    p = projet()
    etape(p, libelle_en="")
    with pytest.raises(ValidationError):
        p.publish()


def test_etape_d_un_projet_publie_doit_rester_traduite():
    p = projet()
    p.publish()
    with pytest.raises(ValidationError):
        etape(p, libelle_en="  ")


def test_montant_d_etape_facultatif_et_positif():
    p = projet()
    assert etape(p).montant_fcfa is None
    with pytest.raises(ValidationError):
        etape(p, montant_fcfa=-1)


def test_figure_optimisee_comme_les_images_de_nouvelles(media):
    from PIL import Image
    f = figure(projet())
    with Image.open(f.image.path) as img:
        assert img.size == (1600, 800) and img.format == "JPEG"


def test_figure_sans_alternative_refusee(media):
    with pytest.raises(ValidationError) as exc:
        figure(projet(), alt_en="")
    assert "alt_en" in exc.value.message_dict


def test_version_interactive_limitee_aux_pages_versionnees(media, pages):
    p = projet()
    assert figure(p, interactive="cycle.html").interactive == "cycle.html"
    for interdit in ("../../settings.py", "https://exemple.com/x.html", "absente.html"):
        with pytest.raises(ValidationError) as exc:
            figure(p, interactive=interdit)
        assert "interactive" in exc.value.message_dict


def test_nouvelle_liee_a_un_projet_une_seule_fois():
    from django.db import IntegrityError, transaction
    from tests.factories import nouvelle
    p, n = projet(), nouvelle()
    models.NouvelleProjet.objects.create(projet=p, nouvelle=n)
    assert list(p.nouvelles.all()) == [n]
    with pytest.raises((IntegrityError, ValidationError)), transaction.atomic():
        models.NouvelleProjet.objects.create(projet=p, nouvelle=n)
    p.delete()
    assert models.Nouvelle.objects.filter(pk=n.pk).exists()


@pytest.mark.django_db(transaction=True)
def test_image_de_figure_remplacee_ou_supprimee_nettoyee(media):
    from pathlib import Path
    f = figure(projet())
    ancienne = Path(f.image.path)
    f.image = image_file((800, 400))
    f.save()
    assert not ancienne.exists() and Path(f.image.path).exists()
    actuelle = Path(f.image.path)
    f.delete()
    assert not actuelle.exists()


# --- Pages publiques : liste (US-42) --------------------------------------------------------------------------

def test_liste_des_projets_publies_dans_les_deux_langues(client):
    from tests.factories import configuration
    configuration()
    second = projet(slug="second", titre_fr="Second projet", titre_en="Second project", ordre=2)
    premier = projet(titre_fr="Chambre froide solaire", titre_en="Solar cold room", ordre=1, statut="validation")
    projet(slug="brouillon", titre_fr="Brouillon caché", titre_en="Hidden draft")
    second.publish(), premier.publish()
    fr = page(client, "/fr/projets/")
    assert fr.index("Chambre froide solaire") < fr.index("Second projet")
    assert "Brouillon caché" not in fr and "En validation" in fr and "resume fr" in fr
    assert 'href="/fr/projets/chambre-froide/"' in fr and 'href="/en/projects/"' in fr
    en = page(client, "/en/projects/")
    assert "Solar cold room" in en and "In validation" in en and "Hidden draft" not in en
    assert 'href="/en/projects/chambre-froide-en/"' in en


def test_liste_vide_explicite(client):
    from tests.factories import configuration
    configuration()
    assert "Aucun projet publié pour le moment." in page(client, "/fr/projets/")
    assert "No published project yet." in page(client, "/en/projects/")


def test_projets_dans_le_menu_entre_journal_et_contact(client):
    from tests.factories import configuration
    configuration()
    for lang, label, url in (("fr", "Projets", "/fr/projets/"), ("en", "Projects", "/en/projects/")):
        content = page(client, f"/{lang}/")
        nav = content[content.index('id="main-navigation"'):content.index("</nav>")]
        assert f'href="{url}"' in nav and nav.index(f'href="{url}"') < nav.index(f'href="/{lang}/contact/"')
        assert f">{label}<" in nav
        assert 'aria-current="page"' in page(client, url).split(f'href="{url}"')[1].split(">")[0]


# --- Pages publiques : fiche (US-43, US-44) -------------------------------------------------------------------

def test_brouillon_introuvable_dans_les_deux_langues(client):
    from tests.factories import configuration
    configuration()
    projet()
    page(client, "/fr/projets/chambre-froide/", 404)
    page(client, "/en/projects/chambre-froide-en/", 404)


def test_fiche_affiche_les_textes_de_sa_langue_et_mene_a_sa_traduction(client):
    publie()
    fr = page(client, "/fr/projets/chambre-froide/")
    for text in ("titre fr", "resume fr", "problematique fr", "objectifs fr", "En conception"):
        assert text in fr, text
    assert 'href="/en/projects/chambre-froide-en/"' in fr and "titre en" not in fr
    en = page(client, "/en/projects/chambre-froide-en/")
    assert "objectifs en" in en and "In design" in en and 'href="/fr/projets/chambre-froide/"' in en
    assert "titre fr" not in en


def test_etapes_ordonnees_avec_date_etat_et_montant(client):
    p = publie()
    etape(p, ordre=2, libelle_fr="Essais d'autonomie", etat="a_venir")
    etape(p, ordre=1, libelle_fr="Tranche T0", montant_fcfa=45000, etat="fait")
    content = page(client, "/fr/projets/chambre-froide/")
    assert content.index("Tranche T0") < content.index("Essais d'autonomie")
    assert "45 000 FCFA" in content and "Fait" in content and "À venir" in content
    assert "45,000 FCFA" in page(client, "/en/projects/chambre-froide-en/")


def test_binome_affiche_seulement_avec_son_accord(client):
    p = publie(binome="Prénom Binôme")
    assert "Prénom Binôme" not in page(client, "/fr/projets/chambre-froide/")
    p.accord_binome = True
    p.save()
    assert "Prénom Binôme" in page(client, "/fr/projets/chambre-froide/")


def test_resultats_affiches_seulement_une_fois_renseignes(client):
    p = publie()
    assert "Résultats" not in page(client, "/fr/projets/chambre-froide/")
    p.resultats_fr, p.resultats_en = "Descente à +4 °C en 1 h 40.", "Pull-down to +4 °C in 1 h 40."
    p.save()
    assert "Descente à +4 °C en 1 h 40." in page(client, "/fr/projets/chambre-froide/")


def test_secteurs_et_nouvelles_publies_seuls_affiches(client):
    from tests.factories import nouvelle, secteur
    p = publie()
    visible, cache = secteur(publie=True), secteur(slug="electronique", nom_fr="Secteur caché")
    models.ProjetSecteur.objects.create(projet=p, secteur=visible)
    models.ProjetSecteur.objects.create(projet=p, secteur=cache)
    entree = nouvelle(publie=True, titre_fr="Entrée liée")
    brouillon = nouvelle(slug="brouillon", titre_fr="Entrée brouillon")
    for n in (entree, brouillon):
        models.NouvelleProjet.objects.create(projet=p, nouvelle=n)
    content = page(client, "/fr/projets/chambre-froide/")
    assert 'href="/fr/secteurs/froid/"' in content and "Secteur caché" not in content
    assert 'href="/fr/nouvelles/formation/"' in content and "Entrée brouillon" not in content


def test_figure_avec_alternative_legende_et_version_interactive(client, media, pages):
    p = publie()
    figure(p, interactive="cycle.html")
    fr = page(client, "/fr/projets/chambre-froide/")
    assert 'alt="Vue éclatée"' in fr and "<figcaption>Vue éclatée" in fr
    assert 'href="/static/hub/projets/cycle.html"' in fr and "Version interactive" in fr
    en = page(client, "/en/projects/chambre-froide-en/")
    assert 'alt="Exploded view"' in en and "Interactive version" in en


def test_textes_echappes_et_aucune_promesse_commerciale(client):
    publie(resume_fr="<script>alert(1)</script>")
    raw = client.get("/fr/projets/chambre-froide/").content.decode()
    assert "<script>alert(1)</script>" not in raw and "&lt;script&gt;" in raw
    for path in ("/fr/projets/", "/fr/projets/chambre-froide/", "/en/projects/", "/en/projects/chambre-froide-en/"):
        content = html.unescape(client.get(path).content.decode()).lower()
        for interdit in ("devis", "prestation", "quote", "offre", "our offer"):
            assert interdit not in content, (path, interdit)


# --- Bloc « Projet en cours » (US-42) -------------------------------------------------------------------------

def test_bloc_projet_en_cours_sur_accueil_et_secteur_associe(client):
    from tests.factories import secteur
    froid, _autre = secteur(publie=True), secteur(slug="electronique", publie=True)
    p = publie(statut="realisation", titre_fr="Chambre froide solaire", titre_en="Solar cold room")
    models.ProjetSecteur.objects.create(projet=p, secteur=froid)
    for path in ("/fr/", "/fr/secteurs/froid/"):
        content = page(client, path)
        assert "Projet en cours" in content and 'href="/fr/projets/chambre-froide/"' in content, path
    assert "Current project" in page(client, "/en/") and "Solar cold room" in page(client, "/en/")
    assert "data-current-project" not in page(client, "/fr/secteurs/electronique/")


def test_aucun_bloc_pour_un_projet_termine_ou_brouillon(client):
    from tests.factories import secteur
    froid = secteur(publie=True)
    p = publie(statut="termine")
    models.ProjetSecteur.objects.create(projet=p, secteur=froid)
    brouillon = projet(slug="brouillon", statut="conception")
    models.ProjetSecteur.objects.create(projet=brouillon, secteur=froid)
    for path in ("/fr/", "/fr/secteurs/froid/", "/en/"):
        assert "data-current-project" not in page(client, path), path


# --- Administration Unfold (US-45) ----------------------------------------------------------------------------

def test_projet_publie_et_depublie_depuis_unfold(verified_client):
    p = projet()
    verified_client.post("/admin/hub/projet/", {"action": "publish_selected", "_selected_action": [p.pk]})
    p.refresh_from_db()
    assert p.publie
    verified_client.post("/admin/hub/projet/", {"action": "unpublish_selected", "_selected_action": [p.pk]})
    p.refresh_from_db()
    assert not p.publie and models.Projet.objects.filter(pk=p.pk).exists()


def test_publication_incomplete_refusee_avec_le_champ_nomme(verified_client):
    p = projet(objectifs_en="")
    response = verified_client.post("/admin/hub/projet/", {"action": "publish_selected", "_selected_action": [p.pk]},
                                    follow=True)
    p.refresh_from_db()
    assert not p.publie and "objectifs_en" in response.content.decode()


def test_formulaire_projet_avec_etapes_figures_secteurs_et_slugs_verrouilles(verified_client):
    p = projet()
    content = verified_client.get(f"/admin/hub/projet/{p.pk}/change/").content.decode()
    for marker in ('name="etapes-TOTAL_FORMS"', 'name="figures-TOTAL_FORMS"', 'name="projetsecteur_set-TOTAL_FORMS"',
                   'name="slug_fr"', 'name="accord_binome"'):
        assert marker in content, marker
    p.publish()
    content = verified_client.get(f"/admin/hub/projet/{p.pk}/change/").content.decode()
    assert 'name="slug_fr"' not in content


def test_version_interactive_proposee_en_liste_fermee(verified_client, pages):
    content = verified_client.get(f"/admin/hub/projet/{projet().pk}/change/").content.decode()
    assert '<select name="figures-__prefix__-interactive"' in content and 'value="cycle.html"' in content


def test_nouvelle_liee_a_un_projet_depuis_sa_fiche(verified_client):
    from tests.factories import nouvelle
    content = verified_client.get(f"/admin/hub/nouvelle/{nouvelle().pk}/change/").content.decode()
    assert 'name="nouvelleprojet_set-TOTAL_FORMS"' in content
