from html.parser import HTMLParser
from io import BytesIO

import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.staticfiles import finders
from tests.factories import configuration, nouvelle

pytestmark = pytest.mark.django_db


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def test_pages_et_indisponibilite_chargent_css_locale(client):
    for ready in (False, True):
        if ready:
            configuration()
        response = client.get("/fr/")
        document = Document(response.content.decode())
        css = [attrs["href"] for tag, attrs in document.elements if tag == "link" and attrs.get("rel") == "stylesheet"]
        assert css
        assert all(url.startswith("/static/") for url in css)
        for url in css:
            assert finders.find(url.removeprefix("/static/"))


def test_navigation_signale_page_courante_et_titre_detail(client):
    configuration()
    nouvelle(publie=True)
    response = client.get("/en/nouvelles/formation-en/")
    document = Document(response.content.decode())
    current = [attrs for tag, attrs in document.elements if tag == "a" and attrs.get("aria-current") == "page"]
    assert any(attrs["href"] == "/en/nouvelles/" for attrs in current)
    assert "Actual training" in response.content.decode().split("<title>")[1].split("</title>")[0]


def test_image_detail_reserve_dimensions_et_alt_traduit(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    configuration()
    output = BytesIO()
    Image.new("RGB", (200, 100), "blue").save(output, "PNG")
    nouvelle(publie=True, image=SimpleUploadedFile("test.png", output.getvalue()), alt_fr="Formation", alt_en="Training")
    document = Document(client.get("/en/nouvelles/formation-en/").content.decode())
    images = [attrs for tag, attrs in document.elements if tag == "img"]
    assert len(images) == 1
    assert images[0]["alt"] == "Training"
    assert images[0].get("width") == "200"
    assert images[0].get("height") == "100"


@pytest.mark.parametrize("lang,message", [("fr", "Page introuvable"), ("en", "Page not found")])
def test_erreur_404_traduite_et_navigation_retour(client, settings, lang, message):
    settings.DEBUG = False
    response = client.get(f"/{lang}/nouvelles/inconnue/")
    assert response.status_code == 404
    assert message in response.content.decode()
    document = Document(response.content.decode())
    assert any(tag == "a" and attrs.get("href") == f"/{lang}/" for tag, attrs in document.elements)


def test_apercu_signale_demo_seulement_dans_environnement_isole(client, settings):
    configuration()
    settings.VENTISAX_PREVIEW = True
    assert "Démonstration" in client.get("/fr/").content.decode()
    settings.VENTISAX_PREVIEW = False
    assert "Démonstration" not in client.get("/fr/").content.decode()


def test_connexion_utilise_assets_du_projet_sans_css_ou_scripts_distants(client):
    response = client.get("/account/login/")
    assert response.status_code == 200
    document = Document(response.content.decode())
    assets = [attrs["href"] for tag, attrs in document.elements if tag == "link" and attrs.get("rel") == "stylesheet"]
    assets += [attrs["src"] for tag, attrs in document.elements if tag == "script" and "src" in attrs]
    assert assets
    assert all(url.startswith("/static/") for url in assets)
    for url in assets:
        assert finders.find(url.removeprefix("/static/"))


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_controles_publics_accessibles_et_script_local(client, settings, lang):
    configuration()
    settings.VENTISAX_PREVIEW = True
    document = Document(client.get(f"/{lang}/").content.decode())
    buttons = [attrs for tag, attrs in document.elements if tag == "button"]
    menu = [attrs for attrs in buttons if "aria-controls" in attrs]
    assert len(menu) == 1
    assert menu[0].get("aria-expanded") == "false"
    assert menu[0].get("aria-label")
    assert any(tag == "nav" and attrs.get("id") == menu[0]["aria-controls"]
               for tag, attrs in document.elements)
    assert any(attrs.get("aria-label") for attrs in buttons if "data-dismiss-preview" in attrs)
    assert any(tag == "a" and attrs.get("href") == "#page-top" and attrs.get("aria-label")
               for tag, attrs in document.elements)
    scripts = [attrs for tag, attrs in document.elements if tag == "script"]
    assert scripts
    for attrs in scripts:
        assert "defer" in attrs
        assert attrs["src"].startswith("/static/")
        assert finders.find(attrs["src"].removeprefix("/static/"))
