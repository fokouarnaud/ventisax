import importlib.util
import os
from pathlib import Path

import pytest

from hub.models import ConfigurationGenerale, Nouvelle, Secteur

pytestmark = pytest.mark.django_db


@pytest.fixture
def preview(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    environ = dict(os.environ)  # le script règle l'environnement à l'import : restauré ensuite
    path = Path(__file__).resolve().parents[1] / "scripts" / "preview_site.py"
    spec = importlib.util.spec_from_file_location("preview_site", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module
    os.environ.clear()
    os.environ.update(environ)


def test_apercu_fictif_cree_secteurs_publies_et_renvoi_academie(preview, client):
    preview.seed()
    assert Secteur.objects.filter(publie=True).count() >= 2 and Nouvelle.objects.filter(publie=True).exists()
    assert ConfigurationGenerale.objects.get().academie_url
    assert client.get("/fr/").status_code == 200
    assert b"data-academy" in client.get("/fr/nouvelles/").content
    assert b"data-formation" in client.get("/fr/secteurs/materiel-electronique/").content


def test_apercu_fictif_sans_video_reseaux_ni_image_sur_les_nouvelles(preview):
    preview.seed()
    assert not Nouvelle.objects.exclude(video_youtube="").exists()
    assert not Nouvelle.objects.exclude(instagram_url="").exists()
    assert not Nouvelle.objects.exclude(facebook_url="").exists()
    assert not Nouvelle.objects.exclude(image="").exists()
