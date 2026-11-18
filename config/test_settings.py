"""Opt-in au mode local exclusivement pour la suite de tests isolée."""
import os
from pathlib import Path

# Le .env de développement ne doit ni régler la suite, ni se propager aux sous-processus qu'elle lance.
os.environ.setdefault("DJANGO_ENV_FILE", str(Path(__file__).resolve().parent / ".env.tests-absent"))
os.environ.setdefault("DJANGO_DEBUG", "1")
# Ni les variables exportées par le shell de développement, retirées au chargement de la suite ; un sous-processus
# lancé pendant un test (PYTEST_CURRENT_TEST défini) garde celles que ce test fixe explicitement.
if "PYTEST_CURRENT_TEST" not in os.environ:
    for name in ("DJANGO_EMAIL_OTP", "DJANGO_ALLOWED_HOSTS", "DJANGO_SECRET_KEY"):
        os.environ.pop(name, None)

from .settings import *  # noqa: F403, E402
