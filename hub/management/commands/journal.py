"""Outils du skill journal-formation : inventaire, vérification d'un fichier source, comparaison au site."""
from pathlib import Path
from urllib.request import urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from hub import journal
from hub.models import Nouvelle


def read_source(path):
    return journal.parse_source(Path(path).read_text(encoding="utf-8"))


class Command(BaseCommand):
    help = "Journal de formation : modules sans entrée, vérification d'un fichier source, comparaison au site publié."

    def add_arguments(self, parser):
        actions = parser.add_subparsers(dest="action", required=True)
        inventaire = actions.add_parser("inventaire", help="Modules de référence sans fichier source.")
        inventaire.add_argument("partie", help="Dossier de partie, par exemple 02_partie2.")
        inventaire.add_argument("--racine", default=str(settings.BASE_DIR / "programme_shorts_pedago"))
        verifier = actions.add_parser("verifier", help="Règles éditoriales et validation de publication, sans écrire en base.")
        verifier.add_argument("fichier")
        verifier.add_argument("--interdit", action="append", default=[], help="Nom à ne jamais publier (répétable).")
        comparer = actions.add_parser("comparer", help="Compare le fichier source aux pages publiques fr/en.")
        comparer.add_argument("fichier")
        comparer.add_argument("--site", default="https://ventisax.pythonanywhere.com")

    def handle(self, *args, action, **options):
        getattr(self, action)(**options)

    def inventaire(self, partie, racine, **options):
        racine = Path(racine)
        for module in journal.modules_sans_entree(racine / "reference" / "cours" / partie, racine / "nouvelles" / partie):
            self.stdout.write(module)

    def verifier(self, fichier, interdit, **options):
        source = read_source(fichier)
        errors = journal.source_errors(source, interdits=interdit)
        nouvelle = Nouvelle(publie=True, **{name: getattr(source, name) for name in journal.NOUVELLE_FIELDS})
        try:
            nouvelle.full_clean(validate_unique=False, validate_constraints=False)
        except ValidationError as exc:
            errors += [f"{name} : {' '.join(messages)}" for name, messages in exc.message_dict.items()]
        if errors:
            raise CommandError("\n".join(errors))
        self.stdout.write(f"{fichier} : conforme.")

    def comparer(self, fichier, site, **options):
        source, errors = read_source(fichier), []
        for lang in ("fr", "en"):
            url = f"{site.rstrip('/')}/{lang}/nouvelles/{getattr(source, 'slug_' + lang)}/"
            with urlopen(url, timeout=30) as response:
                errors += journal.ecarts_page(source, response.read().decode("utf-8"), lang)
            self.stdout.write(f"{url} : vérifiée.")
        if errors:
            raise CommandError("\n".join(errors))
