import re
import pytest
from tests.factories import secteur, nouvelle, configuration

pytestmark = pytest.mark.django_db


def test_entree_francaise_et_pages_bilingues(client):
    configuration(identite_fr="Ventisax — projet en développement", identite_en="Ventisax — developing project")
    s = secteur(publie=True)
    n = nouvelle(publie=True)
    n.secteurs.add(s)
    assert client.get("/").url == "/fr/"
    for lang in ("fr", "en"):
        for page in ("", "presentation/", "contact/", "nouvelles/"):
            response = client.get(f"/{lang}/{page}")
            assert response.status_code == 200
            assert f'<html lang="{lang}">'.encode() in response.content
        response = client.get(f"/{lang}/")
        assert getattr(s, f"nom_{lang}").encode() in response.content
        assert getattr(n, f"titre_{lang}").encode() in response.content


def test_details_traduits_associations_publiques_et_echappement(client):
    configuration()
    s = secteur(publie=True)
    hidden = secteur("retire")
    n = nouvelle(publie=True, corps_fr="<script>alert(1)</script>")
    n.secteurs.add(s, hidden)
    response = client.get("/fr/nouvelles/formation/")
    assert response.status_code == 200
    assert b"&lt;script&gt;" in response.content and b"<script>" not in response.content
    assert b'/en/nouvelles/formation-en/' in response.content
    assert b'/fr/secteurs/froid/' in response.content
    assert b'/fr/secteurs/retire/' not in response.content
    assert b"2026-10-01" in response.content
    response = client.get("/en/secteurs/froid-en/")
    assert response.status_code == 200
    assert b'/fr/secteurs/froid/' in response.content
    assert b"apprentissages en" in response.content
    assert b"prochaine_etape en" in response.content
    n.unpublish()
    for lang, slug in (("fr", "formation"), ("en", "formation-en")):
        assert client.get(f"/{lang}/nouvelles/{slug}/").status_code == 404


@pytest.mark.parametrize("count", [0, 1, 10, 11])
def test_pagination_filtre_et_bascule_langue(client, count):
    configuration()
    s = secteur(publie=True)
    other = secteur("electronique", publie=True)
    for index in range(count):
        n = nouvelle(f"jalon-{index}", publie=True)
        n.secteurs.add(s, other)
    nouvelle("brouillon")
    nouvelle("groupe", publie=True)
    response = client.get("/fr/nouvelles/?secteur=froid")
    assert response.status_code == 200
    page = response.context["page_obj"]
    assert len(page.object_list) == min(count, 10)
    assert page.paginator.count == count
    assert b'/en/nouvelles/?secteur=froid-en' in response.content
    second = client.get("/fr/nouvelles/?secteur=froid&page=2")
    assert second.status_code == (200 if count == 11 else 404)
    if count == 11:
        assert len(second.context["page_obj"]) == 1
        assert b"secteur=froid" in second.content


@pytest.mark.parametrize("query", ["page=0", "page=-1", "page=abc", "page=1.5", "secteur=inconnu"])
def test_filtre_et_page_invalides_404(client, query):
    configuration()
    assert client.get("/fr/nouvelles/?" + query).status_code == 404


def test_retrait_secteur_conserve_nouvelle_comme_groupe(client):
    configuration()
    s = secteur(publie=True)
    n = nouvelle(publie=True)
    n.secteurs.add(s)
    s.unpublish()
    assert client.get("/fr/secteurs/froid/").status_code == 404
    assert client.get("/fr/nouvelles/?secteur=froid").status_code == 404
    response = client.get("/fr/nouvelles/formation/")
    assert response.status_code == 200
    assert b"Groupe" in response.content
    assert n.secteurs.count() == 1


def test_contacts_administrables_et_absence_formulaire(client):
    c = configuration()
    response = client.get("/en/contact/")
    assert b'https://wa.me/237699123456' in response.content
    assert b'mailto:contact@example.com' in response.content
    assert b'<form' not in response.content
    c.email = "nouveau@example.com"
    c.save()
    assert b'mailto:nouveau@example.com' in client.get("/fr/contact/").content


def test_configuration_absente_et_brouillons_sans_exposition(client):
    secteur()
    nouvelle()
    assert client.get("/fr/").status_code == 503
    assert client.get("/fr/nouvelles/formation/").status_code == 404
    assert client.get("/de/").status_code == 404


def test_filtre_tous_depuis_formulaire(client):
    configuration()
    nouvelle(publie=True)
    response = client.get("/fr/nouvelles/?secteur=")
    assert response.status_code == 200
    assert response.context["page_obj"].paginator.count == 1


def test_detail_video_youtube_et_liens_reseaux(client):
    configuration()
    nouvelle(publie=True, video_youtube="https://youtube.com/shorts/dQw4w9WgXcQ?si=trace",
             instagram_url="https://www.instagram.com/reel/Cx1/", facebook_url="https://www.facebook.com/v/1/")
    response = client.get("/fr/nouvelles/formation/")
    html = response.content.decode()
    assert 'src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"' in html
    assert "si=trace" not in html
    assert 'loading="lazy"' in html and 'referrerpolicy="strict-origin-when-cross-origin"' in html
    assert 'title="Vidéo : Formation réelle"' in html
    assert 'href="https://www.instagram.com/reel/Cx1/" target="_blank" rel="noopener noreferrer"' in html
    assert 'href="https://www.facebook.com/v/1/" target="_blank" rel="noopener noreferrer"' in html
    assert "Video in French" not in html
    english = client.get("/en/nouvelles/formation-en/").content.decode()
    assert 'title="Video: Actual training"' in english
    assert "Video in French" in english


def test_detail_sans_video_ni_reseaux(client):
    configuration()
    nouvelle(publie=True)
    html = client.get("/fr/nouvelles/formation/").content.decode()
    assert "<iframe" not in html and "instagram" not in html and "facebook" not in html


@pytest.mark.parametrize("lang,label,quartier", [("fr", "Me prévenir à l’ouverture", "Mon%20quartier"),
                                                 ("en", "Notify me at launch", "My%20neighbourhood")])
def test_bouton_me_prevenir_sur_accueil_et_contact(client, lang, label, quartier):
    c = configuration()
    home = client.get(f"/{lang}/").content.decode()
    assert home.count('href="https://wa.me/237699123456?text=') == 2
    assert label in home and quartier in home
    contact = client.get(f"/{lang}/contact/").content.decode()
    assert 'href="https://wa.me/237699123456?text=' in contact and label in contact
    c.whatsapp = ""
    c.save()
    home = client.get(f"/{lang}/").content.decode()
    assert home.count('href="mailto:contact@example.com?subject=') == 2
    assert "wa.me" not in home


@pytest.mark.parametrize("lang,label,old", [("fr", "Journal de formation", ">Nouvelles<"),
                                            ("en", "Training log", ">News<")])
def test_rubrique_journal_de_formation_sans_changer_les_url(client, lang, label, old):
    configuration()
    response = client.get(f"/{lang}/nouvelles/")
    html = response.content.decode()
    assert response.status_code == 200
    assert f"<h1>{label}</h1>" in html and f"<title>{label} · Ventisax</title>" in html
    assert old not in html and old not in client.get(f"/{lang}/").content.decode()


def test_profils_reseaux_affiches_seulement_si_renseignes(client):
    configuration(tiktok_url="https://www.tiktok.com/@ventisax", facebook_url="https://www.facebook.com/ventisax")
    for page in ("", "contact/"):
        html = client.get(f"/fr/{page}").content.decode()
        assert 'href="https://www.tiktok.com/@ventisax" target="_blank" rel="noopener noreferrer"' in html
        assert 'href="https://www.facebook.com/ventisax" target="_blank" rel="noopener noreferrer"' in html
        assert "instagram" not in html and "youtube.com/@" not in html


@pytest.mark.parametrize("lang,summary,label,value", [
    ("fr", "Compte rendu de manipulation", "Objet", "port du harnais"),
    ("en", "Practical work report", "Purpose", "wearing a harness")])
def test_compte_rendu_replie_en_fiche_et_paragraphes_separes(client, lang, summary, label, value):
    configuration()
    nouvelle(publie=True, corps_fr="Premier paragraphe.\n\nSecond paragraphe.", corps_en="First paragraph.\n\nSecond paragraph.",
             compte_rendu_fr="Objet : port du harnais\nDurée : 4 heures",
             compte_rendu_en="Purpose: wearing a harness\nDuration: 4 hours")
    slug = "formation" if lang == "fr" else "formation-en"
    html = client.get(f"/{lang}/nouvelles/{slug}/").content.decode()
    assert f'<details class="report"><summary>{summary}<span class="report-chevron">' in html
    assert f"<dt>{label}</dt><dd>{value}</dd>" in html
    assert html.count('<p>') >= 2 and "<br>" not in html.split('class="prose"')[1].split("</div>")[0]


def test_journal_groupe_par_jour_en_liste_et_en_grille(client):
    from datetime import date
    configuration()
    s = secteur(publie=True)
    for slug in ("a", "b"):
        nouvelle(slug, publie=True, date_jalon=date(2026, 10, 13), corps_fr=" ".join(["mot"] * 40)).secteurs.add(s)
    nouvelle("c", publie=True, date_jalon=date(2026, 10, 14))
    liste = client.get("/fr/nouvelles/").content.decode()
    assert 'class="journal journal-liste"' in liste and liste.count('class="day-group"') == 2
    assert liste.count('<time class="news-date"') == 2 and "news-excerpt" not in liste
    assert 'href="?vue=grille" class="view-option">' in liste
    assert re.search(r'class="view-option" aria-current="true">(?:(?!</a>).)*Liste</a>', liste, re.S)
    grille = client.get("/fr/nouvelles/?vue=grille&secteur=froid").content.decode()
    assert 'class="journal journal-grille"' in grille and grille.count('class="day-group"') == 1
    assert grille.count('class="news-excerpt"') == 2 and grille.count("mot …</p>") == 2  # extraits tronqués
    assert re.search(r'class="view-option" aria-current="true">(?:(?!</a>).)*Grille</a>', grille, re.S)
    assert '<input type="hidden" name="vue" value="grille">' in grille
    assert "vue=grille" in grille.split('class="language-link" href="')[1].split('"')[0]
    assert client.get("/fr/nouvelles/?vue=inconnue").status_code == 200


def test_pagination_conserve_la_vue_grille(client):
    configuration()
    for index in range(11):
        nouvelle(f"jalon-{index}", publie=True)
    html = client.get("/fr/nouvelles/?vue=grille").content.decode()
    assert 'href="?page=2&amp;vue=grille"' in html
