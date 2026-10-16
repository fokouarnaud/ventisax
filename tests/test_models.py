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


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtube.com/shorts/dQw4w9WgXcQ?feature=share",
    "https://m.youtube.com/watch?v=dQw4w9WgXcQ&t=12s",
    "https://www.youtube.com/embed/dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ?si=abc",
])
def test_video_youtube_accepte_formats_courants_et_extrait_id(url):
    n = nouvelle(video_youtube=url)
    assert n.youtube_id == "dQw4w9WgXcQ"


@pytest.mark.parametrize("url", [
    "https://vimeo.com/123456",
    "https://www.youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/playlist?list=PL1234567890",
    "https://www.youtube.com/watch?v=court",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL1234567890",
    "javascript:alert(1)",
])
def test_video_youtube_refuse_domaine_playlist_et_id_invalide(url):
    with pytest.raises(ValidationError) as error:
        nouvelle(video_youtube=url)
    assert "video_youtube" in error.value.message_dict
    assert models.Nouvelle.objects.count() == 0


def test_liens_reseaux_limites_a_instagram_et_facebook():
    n = nouvelle(instagram_url="https://www.instagram.com/reel/Cx1/", facebook_url="https://fb.watch/abc/")
    assert n.youtube_id == ""
    n2 = nouvelle("autre", facebook_url="https://www.facebook.com/ventisax/videos/1/")
    assert n2.facebook_url
    for field, url in (("instagram_url", "https://instagram.com.evil.example/reel/1/"),
                       ("instagram_url", "https://www.facebook.com/x"),
                       ("facebook_url", "https://www.instagram.com/reel/1/"),
                       ("facebook_url", "data:text/html,x")):
        with pytest.raises(ValidationError) as error:
            nouvelle("refus", **{field: url})
        assert field in error.value.message_dict


def test_profils_reseaux_de_la_configuration_limites_a_leur_domaine():
    c = configuration(youtube_channel_url="https://www.youtube.com/@ventisax",
                      instagram_url="https://www.instagram.com/ventisax/",
                      facebook_url="https://www.facebook.com/ventisax",
                      tiktok_url="https://www.tiktok.com/@ventisax")
    assert c.tiktok_url
    c.delete()
    assert configuration().youtube_channel_url == ""
    models.ConfigurationGenerale.objects.all().delete()
    for field, url in (("youtube_channel_url", "https://www.tiktok.com/@ventisax"),
                       ("tiktok_url", "https://tiktok.com.evil.example/@x"),
                       ("instagram_url", "javascript:alert(1)")):
        with pytest.raises(ValidationError) as error:
            configuration(**{field: url})
        assert field in error.value.message_dict


def test_lien_me_prevenir_prerempli_whatsapp_puis_email():
    c = configuration()
    assert c.notify_url("Mon quartier : ?&", "Sujet") == "https://wa.me/237699123456?text=Mon%20quartier%20%3A%20%3F%26"
    c.whatsapp = ""
    assert c.notify_url("Bonjour & merci", "Me prévenir") == (
        "mailto:contact@example.com?subject=Me%20pr%C3%A9venir&body=Bonjour%20%26%20merci")


def test_compte_rendu_bilingue_exige_a_la_publication_s_il_est_renseigne():
    n = nouvelle(compte_rendu_fr="Objet : essai")
    with pytest.raises(ValidationError) as error:
        n.publish()
    assert "compte_rendu_en" in error.value.message_dict
    n.refresh_from_db()
    n.compte_rendu_en = "Purpose: test"
    n.publish()
    assert nouvelle("sans-cr", publie=True).compte_rendu_fr == ""
