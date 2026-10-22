"""Opt-in au mode local exclusivement pour la suite de tests isolée."""
import os
from pathlib import Path

# Le .env de développement ne doit ni régler la suite, ni se propager aux sous-processus qu'elle lance.
os.environ.setdefault("DJANGO_ENV_FILE", str(Path(__file__).resolve().parent / ".env.tests-absent"))
os.environ.setdefault("DJANGO_DEBUG", "1")

from .settings import *  # noqa: F403, E402
