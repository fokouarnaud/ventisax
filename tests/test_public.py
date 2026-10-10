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
