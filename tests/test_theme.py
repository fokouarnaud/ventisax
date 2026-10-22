from html.parser import HTMLParser

import pytest
from tests.factories import configuration

pytestmark = pytest.mark.django_db


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def first(self, tag, **attrs):
        return next(a for t, a in self.elements if t == tag and all(a.get(k) == v for k, v in attrs.items()))

    def theme_links(self):
        return {a["data-theme-choice"]: a for t, a in self.elements if t == "a" and "data-theme-choice" in a}


def test_sans_preference_le_theme_suit_le_systeme(client):
    configuration()
    document = Document(client.get("/fr/").content.decode())
    assert "data-theme" not in document.first("html")
    assert document.first("meta", name="color-scheme")["content"] == "light dark"
    links = document.theme_links()
    assert set(links) == {"system", "light", "dark"}
    assert links["system"].get("aria-current") == "true"
    assert "aria-current" not in links["dark"]


@pytest.mark.parametrize("lang, labels", [("fr", {"system": "Thème : système", "light": "Thème : clair", "dark": "Thème : sombre"}),
                                          ("en", {"system": "Theme: system", "light": "Theme: light", "dark": "Theme: dark"})])
def test_choix_de_theme_traduits_et_retour_sur_la_page_courante(client, lang, labels):
    configuration()
    document = Document(client.get(f"/{lang}/contact/").content.decode())
    links = document.theme_links()
    assert {choice: a["aria-label"] for choice, a in links.items()} == labels
    assert links["dark"]["href"] == f"/theme/dark/?next=/{lang}/contact/"
    assert document.first("nav", id="main-navigation") is not None


@pytest.mark.parametrize("choice", ["light", "dark"])
def test_preference_enregistree_rendue_des_le_html(client, choice):
    configuration()
    client.cookies["theme"] = choice
    for path in ("/fr/", "/en/nouvelles/", "/fr/page-inexistante/"):
        document = Document(client.get(path).content.decode())
        assert document.first("html")["data-theme"] == choice
        assert document.first("meta", name="color-scheme")["content"] == choice
        assert document.theme_links()[choice].get("aria-current") == "true"


def test_preference_inconnue_ignoree(client):
    configuration()
    client.cookies["theme"] = "<script>"
    document = Document(client.get("/fr/").content.decode())
    assert "data-theme" not in document.first("html")
    assert document.theme_links()["system"].get("aria-current") == "true"


def test_lien_de_theme_enregistre_le_choix_et_revient_sans_javascript(client):
    response = client.get("/theme/dark/", {"next": "/fr/contact/"})
    assert response.status_code == 302 and response.url == "/fr/contact/"
    cookie = response.cookies["theme"]
    assert cookie.value == "dark"
    assert cookie["samesite"] == "Lax" and cookie["path"] == "/" and int(cookie["max-age"]) >= 180 * 24 * 3600
    assert not cookie["httponly"]


def test_retour_au_systeme_supprime_la_preference(client):
    client.cookies["theme"] = "dark"
    response = client.get("/theme/system/", {"next": "/en/"})
    assert response.url == "/en/"
    assert response.cookies["theme"].value == "" and int(response.cookies["theme"]["max-age"]) == 0


@pytest.mark.parametrize("target", ["https://exemple.invalid/", "//exemple.invalid/", ""])
def test_retour_hors_du_site_refuse(client, target):
    response = client.get("/theme/light/", {"next": target})
    assert response.status_code == 302 and response.url == "/"


def test_choix_de_theme_inconnu_introuvable(client):
    assert client.get("/theme/sepia/").status_code == 404
