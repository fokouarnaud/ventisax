"""Opt-in au mode local exclusivement pour la suite de tests isolée."""
import os

os.environ.setdefault("DJANGO_DEBUG", "1")

from .settings import *  # noqa: F403, E402
