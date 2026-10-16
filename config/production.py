"""Configuration pour le proxy HTTPS de PythonAnywhere uniquement."""
from .settings import *  # noqa: F403

if DEBUG:
    raise RuntimeError("DEBUG interdit en production")

# PythonAnywhere termine TLS et renseigne cet en-tête côté proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Noms de fichiers statiques avec empreinte (site.<hash>.css) : chaque version a une nouvelle URL,
# donc aucun navigateur ne garde l'ancien CSS ou JS en cache. Exige `collectstatic` à chaque déploiement.
from django.conf import global_settings  # noqa: E402

STORAGES = {**global_settings.STORAGES,
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"}}
