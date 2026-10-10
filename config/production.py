"""Configuration pour le proxy HTTPS de PythonAnywhere uniquement."""
from .settings import *  # noqa: F403

if DEBUG:
    raise RuntimeError("DEBUG interdit en production")

# PythonAnywhere termine TLS et renseigne cet en-tête côté proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
