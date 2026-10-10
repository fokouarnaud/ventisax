import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from hub.models import ConfigurationGenerale, Secteur, Nouvelle

pytestmark = pytest.mark.django_db


def test_initialisation_contact_email_sans_numero_invente(client):
    call_command("seed_content", email="public@example.com")
    config = ConfigurationGenerale.objects.get()
    assert config.whatsapp == ""
    assert config.whatsapp_url == ""
    for lang in ("fr", "en"):
        response = client.get(f"/{lang}/contact/")
        assert response.status_code == 200
        assert b'mailto:public@example.com' in response.content
        assert b'wa.me' not in response.content


def test_annonce_autorisee_bilingue_idempotente():
    from datetime import date
    call_command("seed_content", email="public@example.com", announce_classes=True)
    news = Nouvelle.objects.get()
    assert news.publie and news.date_jalon == date(2026, 10, 12)
    assert "prévu" in news.corps_fr and "scheduled" in news.corps_en
    news.corps_fr = "Annonce revue par le porteur"
    news.save()
    call_command("seed_content", email="public@example.com", announce_classes=True)
    news.refresh_from_db()
    assert news.corps_fr == "Annonce revue par le porteur"
    assert Nouvelle.objects.count() == 1


def test_initialisation_idempotente_preserve_modifications_et_aucun_jalon_invente():
    call_command("seed_content", email="public@example.com", whatsapp="+237699123456")
    assert Secteur.objects.filter(publie=True, etat="preparation").count() == 2
    assert Nouvelle.objects.count() == 0
    config = ConfigurationGenerale.objects.get()
    config.resume_fr = "Texte relu par le propriétaire"
    config.save()
    call_command("seed_content", email="autre@example.com", whatsapp="+237699654321")
    config.refresh_from_db()
    assert config.resume_fr == "Texte relu par le propriétaire"
    assert config.email == "public@example.com"
    assert Secteur.objects.count() == 2


def test_initialisation_refuse_coordonnees_invalides_sans_publication_partielle():
    with pytest.raises(CommandError):
        call_command("seed_content", email="bad", whatsapp="inconnu")
    assert not ConfigurationGenerale.objects.exists()
    assert not Secteur.objects.exists()
