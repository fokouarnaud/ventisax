from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from tests.factories import nouvelle

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def isolated_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


def image_file(size=(2000, 1000), padding=0):
    stream = BytesIO()
    Image.new("RGB", size, "blue").save(stream, "PNG")
    return SimpleUploadedFile("test.png", stream.getvalue() + b"\0" * padding, content_type="image/png")


def test_image_reduite_compressee_et_alternatives_requises():
    n = nouvelle(image=image_file())
    with Image.open(n.image.path) as img:
        assert img.size == (1600, 800)
        assert img.format == "JPEG"
    with pytest.raises(ValidationError):
        n.publish()
    n.alt_fr, n.alt_en = "Formation", "Training"
    n.publish()


def test_petite_image_non_agrandie_et_limite_incluse():
    file = image_file((20, 10))
    file = image_file((20, 10), padding=2097152 - file.size)
    n = nouvelle(image=file)
    with Image.open(n.image.path) as img:
        assert img.size == (20, 10)
    assert Path(n.image.path).stat().st_size < 2097152


@pytest.mark.parametrize("file", [SimpleUploadedFile("faux.png", b"pas une image"),
                                   SimpleUploadedFile("active.svg", b"<svg></svg>"),
                                   SimpleUploadedFile("trop.png", b"x" * 2097153)])
def test_envoi_invalide_refuse_sans_fichier(file, settings):
    with pytest.raises(ValidationError):
        nouvelle(image=file)
    assert not settings.MEDIA_ROOT.exists() or not list(settings.MEDIA_ROOT.rglob("*.jpg"))


def test_animation_refusee():
    stream = BytesIO()
    Image.new("RGB", (10, 10), "red").save(stream, "GIF", save_all=True,
                                           append_images=[Image.new("RGB", (10, 10), "blue")])
    with pytest.raises(ValidationError):
        nouvelle(image=SimpleUploadedFile("anime.gif", stream.getvalue()))


def test_remplacement_echec_preserve_original_puis_nettoyage():
    n = nouvelle(image=image_file(), alt_fr="Image", alt_en="Image", publie=True)
    old = Path(n.image.path)
    n.image = image_file((30, 20))
    n.corps_en = " "
    with pytest.raises(ValidationError):
        n.save()
    assert old.exists()
    n.refresh_from_db()
    n.image = image_file((30, 20))
    with transaction.atomic():
        n.save()
        assert old.exists()
    assert not old.exists()
    current = Path(n.image.path)
    n.image = ""
    n.save()
    assert not current.exists()


def test_suppression_nouvelle_nettoie_image():
    n = nouvelle(image=image_file())
    path = Path(n.image.path)
    n.delete()
    assert not path.exists()


def test_image_accueil_optimisee_alternatives_requises_et_remplacement_nettoye():
    from hub.models import ConfigurationGenerale
    from tests.factories import configuration
    assert configuration().image_accueil == ""  # sans image, aucune alternative exigée
    ConfigurationGenerale.objects.all().delete()
    with pytest.raises(ValidationError) as error:
        configuration(image_accueil=image_file())
    assert {"alt_accueil_fr", "alt_accueil_en"} <= set(error.value.message_dict)
    with pytest.raises(ValidationError) as error:
        configuration(image_accueil=SimpleUploadedFile("faux.png", b"pas une image"), alt_accueil_fr="A", alt_accueil_en="A")
    assert "image_accueil" in error.value.message_dict
    c = configuration(image_accueil=image_file(), alt_accueil_fr="Photo", alt_accueil_en="Photo")
    old = Path(c.image_accueil.path)
    with Image.open(old) as img:
        assert img.format == "JPEG" and max(img.size) == 1600
    c.image_accueil = image_file((30, 20))
    with transaction.atomic():
        c.save()
        assert old.exists()
    assert not old.exists()
    current = Path(c.image_accueil.path)
    c.image_accueil = ""
    c.save()
    assert not current.exists()


@pytest.mark.parametrize("lang,alt", [("fr", "Atelier de formation"), ("en", "Training workshop")])
def test_accueil_affiche_l_image_d_accueil_sinon_le_logo(client, lang, alt):
    from tests.factories import configuration
    c = configuration()
    html = client.get(f"/{lang}/").content.decode()
    assert "blueprint.svg" in html and "hero-photo" not in html
    c.image_accueil = image_file()
    c.alt_accueil_fr, c.alt_accueil_en = "Atelier de formation", "Training workshop"
    c.save()
    html = client.get(f"/{lang}/").content.decode()
    assert f'class="hero-photo" src="{c.image_accueil.url}" alt="{alt}" width="1600" height="800"' in html
    assert "blueprint.svg" not in html
