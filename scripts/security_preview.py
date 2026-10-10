"""Administration jetable pour les essais Browser, liée uniquement à 127.0.0.1.

Les identifiants synthétiques sont écrits dans un fichier temporaire hors dépôt.
Arrêter le processus à la fin de l'audit : base, médias et secrets sont supprimés.
"""
import argparse
import json
import os
import secrets
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.environ["DJANGO_DEBUG"] = "1"
os.environ["DJANGO_ALLOWED_HOSTS"] = "127.0.0.1,localhost"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()
    import django
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connections
    with tempfile.TemporaryDirectory(prefix="ventisax-security-") as directory:
        root = Path(directory)
        settings.DATABASES["default"]["NAME"] = root / "db.sqlite3"
        settings.MEDIA_ROOT = root / "media"
        settings.DATABASE_BACKUP_DIR = root / "backups"
        settings.EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
        settings.EMAIL_FILE_PATH = root / 'emails'
        settings.VENTISAX_PREVIEW = True
        settings.DEBUG = False
        django.setup()
        call_command("migrate", verbosity=0)
        from scripts.preview_site import seed
        seed()
        from django.contrib.auth import get_user_model
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from hub.models import Nouvelle
        credentials = {"username": "audit_local", "password": secrets.token_urlsafe(24)}
        user = get_user_model().objects.create_superuser(credentials["username"], "audit@example.invalid", credentials["password"])
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        credentials["totp_key"] = device.key
        (root / "credentials.json").write_text(json.dumps(credentials), encoding="utf-8")
        payload = '<img src=x onerror="alert(\'VENTISAX_XSS\')">'
        Nouvelle.objects.create(titre_fr=payload, titre_en=payload, corps_fr=payload,
            corps_en=payload, slug_fr="sonde-xss", slug_en="xss-probe", date_jalon="2026-10-10", publie=True)
        from django.urls import re_path
        from django.views.static import serve
        from config import urls
        urls.urlpatterns.append(re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}))
        print(f"AUDIT_RUNTIME={root}", flush=True)
        print(f"Audit isolé : http://127.0.0.1:{args.port}/account/login/", flush=True)
        try:
            call_command("runserver", f"127.0.0.1:{args.port}", use_reloader=False, insecure=True)
        finally:
            connections.close_all()


if __name__ == "__main__":
    main()
