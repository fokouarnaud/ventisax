import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from hub.database_versions import open_readonly, sha256_tree


class Command(BaseCommand):
    help = "Vérifie et restaure une sauvegarde dans un nouveau répertoire isolé."

    def add_arguments(self, parser):
        parser.add_argument("source")
        parser.add_argument("destination")

    def handle(self, *args, **options):
        source = Path(options["source"]).resolve()
        dest = Path(options["destination"]).resolve()
        if dest.exists():
            raise CommandError("La destination existe déjà ; aucun écrasement autorisé.")
        if source == dest or source in dest.parents:
            raise CommandError("Choisir une destination hors de la sauvegarde.")
        try:
            manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
            if manifest["version"] != 1:
                raise ValueError("Version inconnue")
            if any(p.is_symlink() for p in source.rglob("*")):
                raise ValueError("Lien symbolique")
            actual = sha256_tree(source, exclude=("manifest.json",))
            if actual != manifest["sha256"] or "db.sqlite3" not in actual:
                raise ValueError("Fichiers modifiés ou manquants")
            with closing(open_readonly(source / "db.sqlite3")) as db:
                if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                    raise ValueError("SQLite invalide")
                if db.execute("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("Associations invalides")
                for (name,) in db.execute("SELECT image FROM hub_nouvelle WHERE image != ''"):
                    image = (source / "media" / name).resolve()
                    if source / "media" not in image.parents or not image.is_file():
                        raise ValueError("Illustration manquante ou hors médias")
        except (OSError, ValueError, KeyError, TypeError, sqlite3.DatabaseError) as exc:
            raise CommandError(f"Échec du contrôle d’intégrité de la sauvegarde : {exc}") from exc
        dest.mkdir(parents=True)
        shutil.copy2(source / "db.sqlite3", dest / "db.sqlite3")
        shutil.copytree(source / "media", dest / "media")
        self.stdout.write(self.style.SUCCESS(f"Restauration isolée vérifiée : {dest}"))
