from io import BytesIO
from pathlib import Path
import sqlite3

import pytest
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from tests.factories import configuration, secteur, nouvelle

pytestmark = pytest.mark.django_db(transaction=True)


def test_sauvegarde_restauree_environnement_isole(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    configuration()
    s = secteur(publie=True)
    stream = BytesIO()
    Image.new("RGB", (25, 15), "red").save(stream, "PNG")
    n = nouvelle(image=SimpleUploadedFile("preuve.png", stream.getvalue()), alt_fr="Formation",
                 alt_en="Training", publie=True)
    n.secteurs.add(s)
    backup = tmp_path / "backup"
    restored = tmp_path / "restored"
    call_command("backupventisax", str(backup), confirm_stopped=True)
    n.titre_fr = "Modifié après sauvegarde"
    n.save()
    call_command("restoreventisax", str(backup), str(restored))
    with sqlite3.connect(restored / "db.sqlite3") as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("SELECT titre_fr, titre_en, slug_fr, date_jalon FROM hub_nouvelle").fetchone() == (
            "Formation réelle", "Actual training", "formation", "2026-10-01")
        assert db.execute("SELECT COUNT(*) FROM hub_nouvellesecteur").fetchone() == (1,)
        assert db.execute("SELECT whatsapp FROM hub_configurationgenerale").fetchone() == ("+237699123456",)
        assert db.execute("SELECT premiere_publication FROM hub_nouvelle").fetchone()[0]
    image = restored / "media" / n.image.name
    assert image.read_bytes() == Path(n.image.path).read_bytes()
    with Image.open(image) as img:
        assert img.size == (25, 15)


def test_backup_exige_arret_et_refuse_ecrasement(tmp_path):
    dest = tmp_path / "backup"
    with pytest.raises(CommandError, match="arrêt"):
        call_command("backupventisax", str(dest))
    assert not dest.exists()
    call_command("backupventisax", str(dest), confirm_stopped=True)
    with pytest.raises(CommandError, match="existe"):
        call_command("backupventisax", str(dest), confirm_stopped=True)


def test_restauration_refuse_corruption_et_ecrasement(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    dest = tmp_path / "backup"
    call_command("backupventisax", str(dest), confirm_stopped=True)
    exists = tmp_path / "existing"
    exists.mkdir()
    with pytest.raises(CommandError, match="existe"):
        call_command("restoreventisax", str(dest), str(exists))
    with (dest / "db.sqlite3").open("ab") as file:
        file.write(b"corrompu")
    new = tmp_path / "new"
    with pytest.raises(CommandError, match="intégrité"):
        call_command("restoreventisax", str(dest), str(new))
    assert not new.exists()


def test_commandes_liberent_fichiers_sqlite_pour_nettoyage_windows(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    backup = tmp_path / "backup"
    call_command("backupventisax", str(backup), confirm_stopped=True)
    call_command("restoreventisax", str(backup), str(tmp_path / "restored"))
    (backup / "db.sqlite3").unlink()
    assert not (backup / "db.sqlite3").exists()
