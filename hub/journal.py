"""Fichiers sources du Journal de formation (hors base) : lecture, règles éditoriales, inventaire des modules,
comparaison au site publié. `publier` sert à l'aperçu et à la validation locale ; la production passe par Unfold."""
import re
from dataclasses import dataclass, field
from datetime import datetime
from html import unescape

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from .models import Nouvelle, Secteur

FIELDS = {"Titre fr": "titre_fr", "Titre en": "titre_en", "Slug fr": "slug_fr", "Slug en": "slug_en",
          "Date du jalon": "date_jalon", "Secteurs": "secteurs"}
SECTIONS = {"Français": ("corps_fr", "Compte rendu de manipulation", "compte_rendu_fr"),
            "English": ("corps_en", "Practical work report", "compte_rendu_en")}
JOURNAL_URL = re.compile(r"^Journal de formation : (\S+)", re.M)


@dataclass
class FichierSource:
    titre_fr: str = ""
    titre_en: str = ""
    slug_fr: str = ""
    slug_en: str = ""
    date_jalon: object = None
    secteurs: list = field(default_factory=list)
    corps_fr: str = ""
    corps_en: str = ""
    compte_rendu_fr: str = ""
    compte_rendu_en: str = ""
    url: str = ""
    erreurs: list = field(default_factory=list)


def _block(lines):
    return "\n".join(lines).strip()


def parse_source(text):
    """FichierSource à partir du Markdown : tableau des champs Unfold, puis sections Français et English."""
    source = FichierSource()
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == 2 and cells[0] in FIELDS:
            setattr(source, FIELDS[cells[0]], cells[1])
    raw_date, source.date_jalon = source.date_jalon, None
    if raw_date:
        try:
            source.date_jalon = datetime.strptime(raw_date, "%d/%m/%Y").date()
        except ValueError:
            source.erreurs.append(f"date_jalon : « {raw_date} » attendue au format JJ/MM/AAAA.")
    source.secteurs = [name.strip() for name in source.secteurs.split(",") if name.strip()] if source.secteurs else []
    found = JOURNAL_URL.search(text)
    source.url = found.group(1) if found else ""
    target, lines = None, []
    for line in text.splitlines() + ["## "]:
        if line.startswith("#"):
            if target:
                setattr(source, target, _block(lines))
            title = line.lstrip("#").strip()
            section = next((s for name, s in SECTIONS.items() if title == name), None)
            report = next((s[2] for s in SECTIONS.values() if title == s[1]), None)
            target, lines = (section[0] if section else report), []
        elif target:
            lines.append(line)
    return source


MODULE = re.compile(r"module(\d+)")


def _module_number(path):
    found = MODULE.search(path.name)
    return int(found.group(1)) if found else None


def modules_sans_entree(reference_dir, nouvelles_dir):
    """Dossiers de modules de référence (Path) sans fichier source .md dans le dossier de la même partie."""
    done = {_module_number(d) for d in nouvelles_dir.iterdir()
            if d.is_dir() and any(d.glob("*.md"))} if nouvelles_dir.is_dir() else set()
    modules = [d for d in reference_dir.iterdir() if d.is_dir() and _module_number(d) is not None]
    return [d.name for d in sorted(modules, key=_module_number) if _module_number(d) not in done]


PREFIXES = {"titre_fr": "Formation : ", "titre_en": "Training: ", "slug_fr": "formation-", "slug_en": "training-"}
RUBRIQUES = {"compte_rendu_fr": ("Objet", "Matériel", "Déroulement", "Durée"),
             "compte_rendu_en": ("Purpose", "Equipment", "Procedure", "Duration")}
MAX_PARAGRAPHES = 3


def source_errors(source, interdits=()):
    """Écarts aux règles RJ-03 et RJ-04 et noms interdits (formateur, centre, client), en messages lisibles."""
    errors = list(source.erreurs)
    errors += [f"{name} doit commencer par « {prefix} »." for name, prefix in PREFIXES.items()
              if not getattr(source, name).startswith(prefix)]
    for name in ("corps_fr", "corps_en"):
        if len([p for p in getattr(source, name).split("\n\n") if p.strip()]) > MAX_PARAGRAPHES:
            errors.append(f"{name} : {MAX_PARAGRAPHES} paragraphes au plus.")
    for name, labels in RUBRIQUES.items():
        present = {line.partition(":")[0].strip() for line in getattr(source, name).splitlines()}
        errors += [f"{name} : rubrique « {label} » absente." for label in labels if label not in present]
    texts = " ".join(str(value) for value in vars(source).values())
    errors += [f"Nom interdit présent : {term}." for term in interdits if term.lower() in texts.lower()]
    return errors


TAG = re.compile(r"<[^>]+>")


def _visible_text(html):
    return " ".join(unescape(TAG.sub(" ", html)).split())


def ecarts_page(source, html, lang):
    """Éléments du fichier source (titre, paragraphes, valeurs du compte rendu) absents de la page publique."""
    page = _visible_text(html)
    expected = [(f"titre_{lang}", getattr(source, f"titre_{lang}"))]
    expected += [(f"corps_{lang}", p) for p in getattr(source, f"corps_{lang}").split("\n\n") if p.strip()]
    expected += [(f"compte_rendu_{lang}", line.partition(":")[2])
                 for line in getattr(source, f"compte_rendu_{lang}").splitlines() if line.strip()]
    return [f"{name} : « {text.strip()} » absent de la page." for name, text in expected
            if " ".join(text.split()) not in page]


NOUVELLE_FIELDS = ("titre_fr", "titre_en", "slug_fr", "slug_en", "date_jalon",
                   "corps_fr", "corps_en", "compte_rendu_fr", "compte_rendu_en")


@transaction.atomic
def publier(source):
    """Crée ou corrige la nouvelle (retrouvée par l'un de ses slugs), l'associe à ses secteurs puis la publie ;
    tout échec annule l'ensemble. Un slug déjà publié reste verrouillé par le modèle."""
    secteurs = list(Secteur.objects.filter(nom_fr__in=source.secteurs))
    inconnus = set(source.secteurs) - {s.nom_fr for s in secteurs}
    if inconnus:
        raise ValidationError({"secteurs": f"Secteur inconnu : {', '.join(sorted(inconnus))}."})
    nouvelle = (Nouvelle.objects.filter(Q(slug_fr=source.slug_fr) | Q(slug_en=source.slug_en)).first()
                or Nouvelle())
    for name in NOUVELLE_FIELDS:
        setattr(nouvelle, name, getattr(source, name))
    nouvelle.save()
    nouvelle.secteurs.set(secteurs)
    nouvelle.publish()
    return nouvelle
