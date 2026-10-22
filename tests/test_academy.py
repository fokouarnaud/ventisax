import pytest
from django.core.exceptions import ValidationError
from hub import models
import html
from tests.factories import configuration, nouvelle, secteur
from tests.test_admin import admin_user, verified_client  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db

ACADEMIE = "https://acadventisax.pythonanywhere.com/"


def test_adresse_academie_facultative_et_limitee_a_http():
    assert configuration().academie_url == ""
    models.ConfigurationGenerale.objects.all().delete()
    for url in ("javascript:alert(1)", "data:text/html,x", "ftp://acad.example/"):
        with pytest.raises(ValidationError) as error:
            configuration(academie_url=url)
        assert "academie_url" in error.value.message_dict
    assert configuration(academie_url=ACADEMIE).academie_url == ACADEMIE


def test_liens_de_demande_d_acces_whatsapp_et_email_encodes():
    c = configuration()
    assert c.whatsapp_text_url("Mon nom : ?&") == "https://wa.me/237699123456?text=Mon%20nom%20%3A%20%3F%26"
    assert c.email_text_url("Demande d'accès", "Nom & motif") == (
        "mailto:contact@example.com?subject=Demande%20d%27acc%C3%A8s&body=Nom%20%26%20motif")
    c.whatsapp = ""
    assert c.whatsapp_text_url("Bonjour") == ""


def test_adresse_academie_modifiable_dans_unfold_et_refus_sans_perte(verified_client):
    c = configuration(academie_url=ACADEMIE)
    html = verified_client.get("/admin/hub/configurationgenerale/1/change/").content.decode()
    assert 'name="academie_url"' in html
    payload = {field.name: getattr(c, field.name) for field in c._meta.fields
               if field.editable and not hasattr(getattr(c, field.name), "storage")}
    payload.update(academie_url="javascript:alert(1)", _save="Enregistrer")
    assert verified_client.post("/admin/hub/configurationgenerale/1/change/", payload).status_code == 200
    c.refresh_from_db()
    assert c.academie_url == ACADEMIE
    payload.update(academie_url="https://acad.example.org/", whatsapp="+237600000000", email="acces@example.com")
    assert verified_client.post("/admin/hub/configurationgenerale/1/change/", payload).status_code == 302
    c.refresh_from_db()
    assert (c.academie_url, c.whatsapp, c.email) == ("https://acad.example.org/", "+237600000000", "acces@example.com")


PAGES_AVEC_BLOC = ("nouvelles/", "nouvelles/formation/", "contact/")
PAGES_SANS_BLOC = ("", "presentation/", "secteurs/froid/")


def pages(client, lang, paths):
    secteur(publie=True) if not models.Secteur.objects.exists() else None
    nouvelle(publie=True) if not models.Nouvelle.objects.exists() else None
    slugs = {"fr": {}, "en": {"nouvelles/formation/": "nouvelles/formation-en/", "secteurs/froid/": "secteurs/froid-en/"}}
    for path in paths:
        response = client.get(f"/{lang}/{slugs[lang].get(path, path)}")
        assert response.status_code == 200, path
        yield path, html.unescape(response.content.decode())


def test_sans_adresse_aucun_renvoi_vers_l_academie(client):
    configuration()
    for lang in ("fr", "en"):
        for path, page in pages(client, lang, PAGES_AVEC_BLOC + PAGES_SANS_BLOC):
            assert 'data-academy' not in page, path


@pytest.mark.parametrize("lang, titre, ouvrir, whatsapp, email, message, sujet", [
    ("fr", "Réviser les cours", "Ouvrir l'Académie", "Demander un accès par WhatsApp", "Demander un accès par e-mail",
     "Bonjour%20Ventisax%2C%20je%20souhaite%20un%20identifiant", "Demande%20d%27acc%C3%A8s%20%C3%A0%20l%27Acad%C3%A9mie"),
    ("en", "Review the lessons", "Open the Academy", "Request access on WhatsApp", "Request access by email",
     "Hello%20Ventisax%2C%20I%20would%20like%20a%20login", "Academy%20access%20request"),
])
def test_bloc_academie_sur_journal_detail_et_contact_dans_la_langue(client, lang, titre, ouvrir, whatsapp, email,
                                                                    message, sujet):
    configuration(academie_url=ACADEMIE)
    for path, page in pages(client, lang, PAGES_AVEC_BLOC):
        assert 'data-academy' in page and titre in page and ouvrir in page, path
        assert f'href="{ACADEMIE}" target="_blank" rel="noopener noreferrer"' in page, path
        assert whatsapp in page and f"https://wa.me/237699123456?text={message}" in page, path
        assert email in page and f"mailto:contact@example.com?subject={sujet}&body={message}" in page, path
        assert "centre de formation" not in page.lower() and "gratuit" not in page.lower() and "free" not in page.lower()
    for path, page in pages(client, lang, PAGES_SANS_BLOC):
        assert 'data-academy' not in page, path


def test_sans_whatsapp_seule_la_demande_par_email_et_coordonnees_a_jour(client):
    configuration(academie_url=ACADEMIE, whatsapp="", email="acces@example.com")
    for _, page in pages(client, "fr", ("contact/",)):
        assert "Demander un accès par WhatsApp" not in page and "wa.me" not in page
        assert "Demander un accès par e-mail" in page
        assert "mailto:acces@example.com?subject=Demande%20d%27acc%C3%A8s" in page


@pytest.mark.parametrize("lang, annonce", [("fr", "(nouvel onglet)"), ("en", "(new tab)")])
def test_ouverture_externe_annoncee_et_bloc_unique(client, lang, annonce):
    configuration(academie_url=ACADEMIE)
    for path, page in pages(client, lang, PAGES_AVEC_BLOC):
        assert page.count("data-academy") == 1, path
        lien = page.split(f'href="{ACADEMIE}"', 1)[1].split("</a>", 1)[0]
        assert f'<span class="visually-hidden">{annonce}</span>' in lien, path


def test_coordonnees_modifiees_reportees_sur_contact_prevenir_et_acces(client):
    c = configuration(academie_url=ACADEMIE)
    c.email, c.whatsapp = "nouveau@example.com", "+237600000001"
    c.save()
    for _, page in pages(client, "fr", ("contact/",)):
        assert "237699123456" not in page and "contact@example.com" not in page
        assert page.count("https://wa.me/237600000001") >= 3  # contact direct, « Me prévenir », demande d'accès
        assert "mailto:nouveau@example.com?subject=Demande" in page and 'href="mailto:nouveau@example.com"' in page


@pytest.mark.parametrize("lang, nom, motif, secret", [
    ("fr", "Mon nom", "Pourquoi je m'y intéresse", "mot de passe"),
    ("en", "My name", "Why I'm interested", "password"),
])
def test_message_de_demande_demande_nom_et_motif_sans_secret(lang, nom, motif, secret):
    from urllib.parse import parse_qs, urlsplit
    from hub.views import LABELS, academy_links
    links = academy_links(configuration(academie_url=ACADEMIE), LABELS[lang])
    for url in (links["whatsapp_url"], links["email_url"]):
        message = parse_qs(urlsplit(url).query)["text" if "wa.me" in url else "body"][0]
        assert nom in message and motif in message and secret not in message.lower()
