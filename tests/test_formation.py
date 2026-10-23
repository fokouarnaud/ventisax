import html

import pytest
from django.core.exceptions import ValidationError

from hub import models
from tests.factories import configuration, nouvelle, secteur
from tests.test_admin import admin_user, verified_client  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db

ELECTRO = "https://electroacadventisax.pythonanywhere.com/fr/catalogue/"


def page(client, path):
    response = client.get(path)
    assert response.status_code == 200, path
    return html.unescape(response.content.decode())


def test_adresse_de_plateforme_facultative_et_limitee_a_http():
    assert secteur().formation_url == ""
    for slug, url in (("a", "javascript:alert(1)"), ("b", "data:text/html,x"), ("c", "ftp://cours.example/")):
        with pytest.raises(ValidationError) as error:
            secteur(slug=slug, formation_url=url)
        assert "formation_url" in error.value.message_dict
    assert secteur(slug="d", formation_url=ELECTRO).formation_url == ELECTRO


def test_sans_adresse_aucun_bloc_sur_la_fiche(client):
    configuration()
    secteur(publie=True, site_url="https://clim.example.org/")
    for path in ("/fr/secteurs/froid/", "/en/secteurs/froid-en/"):
        content = page(client, path)
        assert "data-formation" not in content
        assert 'href="https://clim.example.org/"' in content


@pytest.mark.parametrize("lang, slug, titre, texte, lien, onglet", [
    ("fr", "froid", "Approfondir en ligne",
     "Les cours, quiz et examens que nous suivons pour ce secteur sont en ligne, en français et en anglais.",
     "Voir le programme", "(nouvel onglet)"),
    ("en", "froid-en", "Go further online",
     "The lessons, quizzes and exams we follow for this sector are online, in French and in English.",
     "See the programme", "(new tab)"),
])
def test_bloc_sur_la_fiche_dans_la_langue_avec_lien_externe(client, lang, slug, titre, texte, lien, onglet):
    configuration()
    secteur(publie=True, formation_url=ELECTRO)
    content = page(client, f"/{lang}/secteurs/{slug}/")
    assert content.count("data-formation") == 1
    assert titre in content and texte in content and lien in content and onglet in content
    assert f'href="{ELECTRO}" target="_blank" rel="noopener noreferrer"' in content
    for interdit in ("centre de formation", "training centre", "gratuit", "free", "certificat", "certificate"):
        assert interdit not in content.lower(), interdit


def test_bloc_absent_des_autres_pages_et_secteurs(client):
    configuration(academie_url="https://acadventisax.pythonanywhere.com/")
    secteur(publie=True, formation_url=ELECTRO)
    secteur(slug="electronique", publie=True)
    nouvelle(publie=True)
    for lang, suffix in (("fr", ""), ("en", "-en")):
        for path in ("", "presentation/", "nouvelles/", f"nouvelles/formation{suffix}/", "contact/",
                     f"secteurs/electronique{suffix}/"):
            assert "data-formation" not in page(client, f"/{lang}/{path}"), path


def test_secteur_depublie_introuvable_malgre_l_adresse(client):
    configuration()
    secteur(formation_url=ELECTRO)
    assert client.get("/fr/secteurs/froid/").status_code == 404


def test_adresse_modifiable_dans_unfold_et_refus_sans_perte(verified_client):
    s = secteur(publie=True, formation_url=ELECTRO)
    url = f"/admin/hub/secteur/{s.pk}/change/"
    assert 'name="formation_url"' in verified_client.get(url).content.decode()
    payload = {field.name: getattr(s, field.name) for field in s._meta.fields
               if field.editable and field.name not in ("uuid", "publie", "premiere_publication")}
    payload.update(formation_url="javascript:alert(1)", _save="Enregistrer")
    assert verified_client.post(url, payload).status_code == 200
    s.refresh_from_db()
    assert s.formation_url == ELECTRO
    payload.update(formation_url="")
    assert verified_client.post(url, payload).status_code == 302
    s.refresh_from_db()
    assert s.formation_url == "" and s.publie


ACADEMIE = "https://acadventisax.pythonanywhere.com/"


def test_fiche_secteur_sans_pastille_du_secteur_courant(client):
    configuration()
    froid = secteur(publie=True)
    autre = secteur(slug="electronique", publie=True, nom_fr="Électronique publique")
    n = nouvelle(publie=True)
    n.secteurs.add(froid, autre)
    fiche = page(client, "/fr/secteurs/froid/")
    assert 'class="tag" href="/fr/secteurs/froid/"' not in fiche
    assert 'class="tag" href="/fr/secteurs/electronique/"' in fiche
    journal = page(client, "/fr/nouvelles/")
    assert 'class="tag" href="/fr/secteurs/froid/"' in journal


def test_renvoi_apres_l_etat_du_secteur(client):
    configuration()
    secteur(publie=True, formation_url=ELECTRO)
    content = page(client, "/fr/secteurs/froid/")
    assert content.index("Prochaine étape") < content.index("data-formation")


def test_secteur_renvoye_vers_l_academie_affiche_la_demande_d_acces(client):
    configuration(academie_url=ACADEMIE)
    secteur(publie=True, formation_url=ACADEMIE)
    for path, titre, etape in (("/fr/secteurs/froid/", "Réviser les cours", "Prochaine étape"),
                               ("/en/secteurs/froid-en/", "Review the lessons", "Next step")):
        content = page(client, path)
        assert content.count("data-academy") == 1 and titre in content
        assert "data-formation" not in content
        assert "https://wa.me/237699123456?text=" in content
        assert content.index(etape) < content.index("data-academy")
