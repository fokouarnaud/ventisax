from datetime import date

import pytest

from hub import journal

SOURCE = """# Module 3 : Formation : câbler un simple allumage

Source : références du module, contenu reformulé.
Journal de formation : /fr/nouvelles/formation-simple-allumage/ (21/10/2026).

| Champ Unfold | Valeur |
| --- | --- |
| Titre fr | Formation : câbler un simple allumage |
| Titre en | Training: wiring a single light switch |
| Slug fr | formation-simple-allumage |
| Slug en | training-single-switch-wiring |
| Date du jalon | 21/10/2026 |
| Secteurs | Climatisation / froid |

## Français

Un simple allumage commande une lampe depuis un seul endroit.

La phase passe par l'interrupteur, le neutre va directement à la lampe.

### Compte rendu de manipulation

Objet : câbler un simple allumage sur planche
Matériel : interrupteur, douille, câbles 1,5 mm²
Déroulement : fixation, câblage, test à vide puis sous tension
Durée : 4 heures

## English

A single switch controls a lamp from one place.

The live wire goes through the switch, the neutral goes straight to the lamp.

### Practical work report

Purpose: wire a single switch on a board
Equipment: switch, lamp holder, 1.5 mm² cables
Procedure: fixing, wiring, dead test then live test
Duration: 4 hours
"""


def test_fichier_source_lu_en_champs_de_nouvelle():
    source = journal.parse_source(SOURCE)
    assert source.titre_fr == "Formation : câbler un simple allumage"
    assert source.titre_en == "Training: wiring a single light switch"
    assert source.slug_fr == "formation-simple-allumage"
    assert source.slug_en == "training-single-switch-wiring"
    assert source.date_jalon == date(2026, 10, 21)
    assert source.secteurs == ["Climatisation / froid"]
    assert source.corps_fr == ("Un simple allumage commande une lampe depuis un seul endroit.\n\n"
                               "La phase passe par l'interrupteur, le neutre va directement à la lampe.")
    assert source.corps_en.startswith("A single switch controls")
    assert source.compte_rendu_fr.splitlines()[0] == "Objet : câbler un simple allumage sur planche"
    assert source.compte_rendu_en.splitlines()[-1] == "Duration: 4 hours"
    assert source.url == "/fr/nouvelles/formation-simple-allumage/"


@pytest.mark.django_db
def test_fichier_source_donne_une_nouvelle_publiable_avec_son_secteur():
    from tests.factories import secteur
    froid = secteur(nom_fr="Climatisation / froid", publie=True)
    nouvelle = journal.publier(journal.parse_source(SOURCE))
    nouvelle.refresh_from_db()
    assert nouvelle.publie and nouvelle.premiere_publication
    assert nouvelle.slug_en == "training-single-switch-wiring"
    assert nouvelle.compte_rendu_en.endswith("Duration: 4 hours")
    assert list(nouvelle.secteurs.all()) == [froid]


@pytest.mark.django_db
def test_fichier_source_sans_compte_rendu_anglais_refuse_par_le_modele():
    from django.core.exceptions import ValidationError
    from hub.models import Nouvelle
    from tests.factories import secteur
    secteur(nom_fr="Climatisation / froid", publie=True)
    incomplet = SOURCE.split("### Practical work report")[0]
    with pytest.raises(ValidationError) as error:
        journal.publier(journal.parse_source(incomplet))
    assert "compte_rendu_en" in error.value.message_dict
    assert not Nouvelle.objects.filter(publie=True).exists()


def test_regles_editoriales_respectees_par_une_source_conforme():
    assert journal.source_errors(journal.parse_source(SOURCE), interdits=["Dupont"]) == []


def test_regles_editoriales_signalent_chaque_ecart():
    texte = (SOURCE.replace("| Titre en | Training: wiring", "| Titre en | Wiring")
             .replace("| Slug fr | formation-simple-allumage", "| Slug fr | simple-allumage")
             .replace("Durée : 4 heures\n", "")
             .replace("from one place.", "from one place.\n\nThird.\n\nFourth, as told by M. Dupont."))
    errors = journal.source_errors(journal.parse_source(texte), interdits=["Dupont"])
    assert any("titre_en" in e for e in errors)
    assert any("slug_fr" in e for e in errors)
    assert any("compte_rendu_fr" in e and "Durée" in e for e in errors)
    assert any("corps_en" in e and "paragraphes" in e for e in errors)
    assert any("Dupont" in e for e in errors)


@pytest.mark.django_db
def test_republier_une_source_corrige_sans_dupliquer_ni_changer_les_urls():
    from hub.models import Nouvelle
    from tests.factories import secteur
    secteur(nom_fr="Climatisation / froid", publie=True)
    premiere = journal.publier(journal.parse_source(SOURCE))
    publiee_le = premiere.premiere_publication
    corrige = journal.publier(journal.parse_source(SOURCE.replace("depuis un seul endroit", "d'un seul endroit")))
    assert Nouvelle.objects.count() == 1
    assert corrige.pk == premiere.pk
    assert "d'un seul endroit" in corrige.corps_fr
    assert corrige.premiere_publication == publiee_le


@pytest.mark.django_db
def test_correction_qui_change_un_slug_publie_est_refusee():
    from django.core.exceptions import ValidationError
    from hub.models import Nouvelle
    from tests.factories import secteur
    secteur(nom_fr="Climatisation / froid", publie=True)
    journal.publier(journal.parse_source(SOURCE))
    with pytest.raises(ValidationError):
        journal.publier(journal.parse_source(SOURCE.replace("| Slug en | training-single-switch-wiring",
                                                            "| Slug en | training-one-switch")))
    assert Nouvelle.objects.get().slug_en == "training-single-switch-wiring"


@pytest.mark.django_db
def test_secteur_inconnu_refuse_sans_rien_publier():
    from django.core.exceptions import ValidationError
    from hub.models import Nouvelle
    with pytest.raises(ValidationError) as error:
        journal.publier(journal.parse_source(SOURCE))
    assert "secteurs" in error.value.message_dict
    assert not Nouvelle.objects.exists()


def test_inventaire_liste_les_modules_de_reference_sans_fichier_source(tmp_path):
    reference, nouvelles = tmp_path / "reference" / "02_partie2", tmp_path / "nouvelles" / "02_partie2"
    for module in ("module1", "module2", "module10", "module3"):
        (reference / module).mkdir(parents=True)
    (nouvelles / "01_module1").mkdir(parents=True)
    (nouvelles / "01_module1" / "module1_bases.md").write_text(SOURCE, encoding="utf-8")
    (nouvelles / "02_module2").mkdir()
    assert journal.modules_sans_entree(reference, nouvelles) == ["module2", "module3", "module10"]
    assert journal.modules_sans_entree(reference, tmp_path / "absent") == ["module1", "module2", "module3", "module10"]


@pytest.mark.django_db
@pytest.mark.parametrize("lang", ["fr", "en"])
def test_page_publique_comparee_au_fichier_source(client, lang):
    from tests.factories import configuration, secteur
    configuration()
    secteur(nom_fr="Climatisation / froid", publie=True)
    source = journal.parse_source(SOURCE)
    journal.publier(source)
    page = client.get(f"/{lang}/nouvelles/{getattr(source, 'slug_' + lang)}/")
    assert page.status_code == 200
    assert journal.ecarts_page(source, page.content.decode(), lang) == []
    modifiee = journal.parse_source(SOURCE.replace("le neutre va directement", "le neutre passe")
                                    .replace("the neutral goes straight", "the neutral passes")
                                    .replace("4 heures", "5 heures").replace("4 hours", "5 hours"))
    ecarts = journal.ecarts_page(modifiee, page.content.decode(), lang)
    assert any(e.startswith(f"corps_{lang}") for e in ecarts)
    assert any(e.startswith(f"compte_rendu_{lang}") for e in ecarts)


def test_commande_inventaire_affiche_les_modules_a_traiter(tmp_path):
    from io import StringIO
    from django.core.management import call_command
    (tmp_path / "reference" / "cours" / "02_partie2" / "module1").mkdir(parents=True)
    (tmp_path / "reference" / "cours" / "02_partie2" / "module5").mkdir()
    entree = tmp_path / "nouvelles" / "02_partie2" / "01_module1"
    entree.mkdir(parents=True)
    (entree / "module1_bases.md").write_text(SOURCE, encoding="utf-8")
    out = StringIO()
    call_command("journal", "inventaire", "02_partie2", "--racine", str(tmp_path), stdout=out)
    assert out.getvalue().split() == ["module5"]


@pytest.mark.django_db
def test_commande_verifier_accepte_une_source_conforme_et_refuse_les_ecarts(tmp_path):
    from io import StringIO
    from django.core.management import call_command
    from django.core.management.base import CommandError
    from hub.models import Nouvelle
    conforme, fautive = tmp_path / "conforme.md", tmp_path / "fautive.md"
    conforme.write_text(SOURCE, encoding="utf-8")
    fautive.write_text(SOURCE.replace("| Date du jalon | 21/10/2026 |\n", "").replace("Durée : 4 heures\n", ""),
                       encoding="utf-8")
    out = StringIO()
    call_command("journal", "verifier", str(conforme), "--interdit", "Dupont", stdout=out)
    assert "conforme" in out.getvalue()
    with pytest.raises(CommandError) as error:
        call_command("journal", "verifier", str(fautive))
    assert "Durée" in str(error.value) and "date_jalon" in str(error.value)
    assert not Nouvelle.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_commande_comparer_verifie_les_deux_langues_sur_un_site(live_server, tmp_path):
    from io import StringIO
    from django.core.management import call_command
    from django.core.management.base import CommandError
    from tests.factories import configuration, secteur
    configuration()
    secteur(nom_fr="Climatisation / froid", publie=True)
    journal.publier(journal.parse_source(SOURCE))
    fichier = tmp_path / "module3.md"
    fichier.write_text(SOURCE, encoding="utf-8")
    out = StringIO()
    call_command("journal", "comparer", str(fichier), "--site", live_server.url, stdout=out)
    assert "/fr/nouvelles/formation-simple-allumage/" in out.getvalue()
    assert "/en/nouvelles/training-single-switch-wiring/" in out.getvalue()
    fichier.write_text(SOURCE.replace("4 hours", "5 hours"), encoding="utf-8")
    with pytest.raises(CommandError) as error:
        call_command("journal", "comparer", str(fichier), "--site", live_server.url)
    assert "compte_rendu_en" in str(error.value)


@pytest.mark.django_db
def test_commande_verifier_signale_une_date_mal_formee_sans_planter(tmp_path):
    from django.core.management import call_command
    from django.core.management.base import CommandError
    fichier = tmp_path / "modele.md"
    fichier.write_text(SOURCE.replace("| Date du jalon | 21/10/2026 |", "| Date du jalon | JJ/MM/AAAA |"), encoding="utf-8")
    with pytest.raises(CommandError) as error:
        call_command("journal", "verifier", str(fichier))
    assert "date_jalon" in str(error.value) and "JJ/MM/AAAA" in str(error.value)
