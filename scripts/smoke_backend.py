"""Parcours HTTP et restauration dans un environnement entièrement temporaire."""
import os
import sys
import tempfile
import threading
from pathlib import Path
from urllib.request import urlopen
from wsgiref.simple_server import make_server, WSGIRequestHandler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_DEBUG"] = "1"


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def main():
    from django.conf import settings
    from django.core.management import call_command
    from django.core.wsgi import get_wsgi_application
    from django.db import connections

    with tempfile.TemporaryDirectory(prefix="ventisax-smoke-") as temp:
        root = Path(temp)
        settings.DATABASES["default"]["NAME"] = root / "db.sqlite3"
        settings.MEDIA_ROOT = root / "media"
        settings.DATABASE_BACKUP_DIR = root / "admin-backups"
        settings.ALLOWED_HOSTS = ["127.0.0.1"]
        application = get_wsgi_application()
        call_command("migrate", verbosity=0)
        from tests.factories import configuration, secteur, nouvelle
        configuration()
        sector = secteur(publie=True)
        news = nouvelle(publie=True)
        news.secteurs.add(sector)
        with make_server("127.0.0.1", 0, application, handler_class=QuietHandler) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                for path in ("/", "/fr/", "/en/", "/en/contact/", "/fr/nouvelles/?secteur=froid",
                             "/en/nouvelles/formation-en/", "/fr/secteurs/froid/"):
                    with urlopen(base + path, timeout=10) as response:
                        assert response.status == 200
                        assert b"Ventisax" in response.read()
                with urlopen(base + "/admin/", timeout=10) as response:
                    assert "/account/login/" in response.url
                print("HTTP : pages bilingues, filtre, détail et accès OTP observés.")
            finally:
                server.shutdown()
                worker.join(timeout=10)
        call_command("backupventisax", str(root / "backup"), confirm_stopped=True, verbosity=0)
        call_command("restoreventisax", str(root / "backup"), str(root / "restored"), verbosity=0)
        connections.close_all()
        print("Restauration isolée : contrôles d’intégrité passés. Aucun contenu ajouté à la base du projet.")


if __name__ == "__main__":
    main()
