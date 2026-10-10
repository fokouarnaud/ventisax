import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from hub.models import ConfigurationGenerale, Secteur, Nouvelle

pytestmark = pytest.mark.django_db


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
