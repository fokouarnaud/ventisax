import pytest
from django.core.exceptions import ValidationError
from hub.models import Secteur
from hub import models
from tests.factories import secteur, nouvelle, configuration
from django.db.models.deletion import ProtectedError
from datetime import date

pytestmark = pytest.mark.django_db


def test_secteur_publication_refuse_traduction_absente():
    secteur = Secteur(nom_fr="Froid", publie=True)
    with pytest.raises(ValidationError) as error:
        secteur.save()
    assert "nom_en" in error.value.message_dict
    assert Secteur.objects.count() == 0


def test_secteur_brouillon_complet_publication_et_urls_stables():
    s = Secteur.objects.create()
    for language in ("fr", "en"):
        for name in ("nom", "description", "apprentissages", "prochaine_etape"):
            setattr(s, f"{name}_{language}", "Formation réelle")
        setattr(s, f"slug_{language}", f"froid-{language}")
    s.publish()
    first = s.premiere_publication
    s.nom_fr = "Nouveau nom"
    s.save()
    s.unpublish()
    s.publish()
    s.refresh_from_db()
    assert s.premiere_publication == first
    assert s.slug_fr == "froid-fr"
    assert s.etat == "preparation"
    s.slug_fr = "autre"
    with pytest.raises(ValidationError):
        s.save()
    s.refresh_from_db()
    assert s.slug_fr == "froid-fr"


def test_secteur_description_anglaise_espaces_bloque_publication():
    s = Secteur(nom_fr="Froid", nom_en="Cooling", slug_fr="froid", slug_en="cooling",
                description_fr="Formation", description_en="  ", publie=True)
    with pytest.raises(ValidationError) as error:
        s.save()
    assert "description_en" in error.value.message_dict


def test_nouvelle_brouillon_liens_traduits_et_publication_atomique():
    n = nouvelle(corps_en="")
    with pytest.raises(ValidationError):
        n.publish()
    n.refresh_from_db()
    assert not n.publie and n.premiere_publication is None
    n.corps_en = "Training"
    n.save()
    link = models.LienNouvelle.objects.create(nouvelle=n, url="https://example.com", libelle_fr="Formation")
    with pytest.raises(ValidationError):
        n.publish()
    link.libelle_en = "Training"
    link.save()
    n.publish()
    first = n.premiere_publication
    n.titre_fr = "Titre corrigé"
    n.save()
    n.unpublish()
    n.publish()
    assert n.premiere_publication == first
    n.corps_en = " "
    with pytest.raises(ValidationError):
        n.save()
    n.refresh_from_db()
    assert n.corps_en == "Training"
    link.libelle_en = ""
    with pytest.raises(ValidationError):
        link.save()


def test_associations_uniques_et_suppression_secteur_protegee():
    s = secteur()
    n = nouvelle()
    n.secteurs.add(s, s)
    assert n.secteurs.count() == 1
    with pytest.raises(ProtectedError):
        s.delete()
    s.unpublish()
    n.refresh_from_db()
    assert n.secteurs.count() == 1
    n.delete()
    assert models.Secteur.objects.filter(pk=s.pk).exists()


def test_collision_slugs_et_tri_jalons():
    n1 = nouvelle("a", date_jalon=date(2026, 9, 1), publie=True)
    n2 = nouvelle("b", date_jalon=date(2026, 10, 1), publie=True)
    n3 = nouvelle("c", date_jalon=date(2026, 10, 1), publie=True)
    assert list(models.Nouvelle.objects.values_list("pk", flat=True)) == [n3.pk, n2.pk, n1.pk]
    with pytest.raises(ValidationError):
        nouvelle("a")


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,test", "ftp://example.com"])
def test_liens_dangereux_refuses(url):
    n = nouvelle()
    with pytest.raises(ValidationError):
        models.LienNouvelle.objects.create(nouvelle=n, url=url)
    with pytest.raises(ValidationError):
        secteur(site_url=url)


def test_configuration_unique_validation_et_contacts():
    c = configuration()
    assert c.whatsapp_url == "https://wa.me/237699123456"
    assert c.email_url == "mailto:contact@example.com"
    c.presentation_en = " "
    with pytest.raises(ValidationError):
        c.save()
    c.refresh_from_db()
    assert c.presentation_en == "Texte réel en"
    with pytest.raises(ValidationError):
        configuration()


@pytest.mark.parametrize("values", [{"email": "pas-un-email"}, {"whatsapp": "699123456"}, {"whatsapp": "+01234"}])
def test_coordonnees_invalides_refusees(values):
    with pytest.raises(ValidationError):
        configuration(**values)


def test_email_valide_avec_caracteres_reserves_ne_devient_pas_parametre_mailto():
    c = configuration(email="support?subject=bad@example.com")
    assert c.email_url == "mailto:support%3Fsubject%3Dbad@example.com"


def test_jalon_absent_refuse_et_brouillon_incomplet_autorise():
    n = models.Nouvelle.objects.create()
    with pytest.raises(ValidationError):
        n.publish()
    n = nouvelle("sans-date", date_jalon=None)
    with pytest.raises(ValidationError) as error:
        n.publish()
    assert "date_jalon" in error.value.message_dict
