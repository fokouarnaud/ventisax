import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from hub.database_versions import sha256_tree


class Command(BaseCommand):
    help = "Sauvegarde SQLite et médias après arrêt manuel des écritures."

    def add_arguments(self, parser):
        parser.add_argument("destination")
        parser.add_argument("--confirm-stopped", action="store_true")

    def handle(self, *args, **options):
        if not options["confirm_stopped"]:
            raise CommandError("Confirmer l’arrêt des écritures avec --confirm-stopped.")
        dest = Path(options["destination"]).resolve()
        media = Path(settings.MEDIA_ROOT).resolve()
        if dest.exists():
            raise CommandError("La destination existe déjà ; aucun écrasement autorisé.")
        if dest == media or media in dest.parents:
            raise CommandError("La sauvegarde doit être hors du répertoire média.")
        connection.ensure_connection()
        dest.mkdir(parents=True)
        with closing(sqlite3.connect(dest / "db.sqlite3")) as snapshot:
            connection.connection.backup(snapshot)
            if snapshot.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise CommandError("Échec du contrôle d’intégrité SQLite.")
        if media.exists():
            if any(p.is_symlink() for p in media.rglob("*")):
                raise CommandError("Liens symboliques refusés dans les médias.")
            shutil.copytree(media, dest / "media")
        else:
            (dest / "media").mkdir()
        manifest = {"version": 1, "sha256": sha256_tree(dest)}
        (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde créée : {dest}. Télécharger hors hébergement."))
