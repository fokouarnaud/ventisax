---
name: journal-formation
description: "Met à jour le Journal de formation du site Ventisax à partir des références de cours (programme_shorts_pedago/reference/cours/<partie>/<module>/) : inventaire des modules sans entrée, questions au porteur sur les faits (date réelle, pratique, durée), lecture des pages du manuel, rédaction bilingue fr/en avec compte rendu de manipulation, vérification par `manage.py journal`, publication directe dans Unfold de production via Playwright (connexion faite par le porteur), contrôle des pages publiques et sauvegarde datée par e-mail. Sert aussi à corriger une entrée déjà publiée. À utiliser quand l'utilisateur demande de « mettre à jour les nouvelles », « publier les modules de la semaine », « ajouter une leçon au journal » ou « corriger une nouvelle »."
---

# journal-formation : publier et corriger les entrées du Journal de formation

Référence de cadrage : `AGENTS.md`, sous-section « journal de formation, partie 2 » de `## GOALS`
et son PRD (US-16 à US-22, règles RJ-01 à RJ-07). En cas de conflit, `AGENTS.md` fait foi.

Commandes (depuis la racine `ventisax/`, préfixe obligatoire en local) :

```bash
DJANGO_DEBUG=1 .venv/Scripts/python manage.py journal inventaire <partie>
DJANGO_DEBUG=1 .venv/Scripts/python manage.py journal verifier <fichier.md> --interdit "<Nom>" [--interdit …]
DJANGO_DEBUG=1 .venv/Scripts/python manage.py journal comparer <fichier.md> [--site https://ventisax.pythonanywhere.com]
```

`journal` n'écrit jamais en base. Code : `hub/journal.py`, tests : `tests/test_journal.py`.

## Règles non négociables

1. **Une entrée = un module réellement suivi**, datée du jour du cours. Aucun module à venir.
2. **Les faits viennent du porteur** : date, ce qui a été pratiqué, durée, intitulé d'une nouvelle partie.
   Les « TAF » du manuel ne prouvent pas qu'une manipulation a eu lieu. Sans réponse, ne rien rédiger.
3. **Droits** : aucun nom de formateur, de centre ni de client ; aucun extrait recopié, aucune photo du
   manuel ni du tableau ; une norme (NF C 15-100…) se cite par son nom, sans valeur de ses tableaux.
   Aucune image attachée. Les références ne sont ni versionnées ni envoyées à un service externe.
4. **Ton** : nos mots, au « nous », progression de formation ; aucune promesse de prestation.
5. **Secteur** : `Climatisation et froid` (nom exact en production) pour tout module de la formation froid et climatisation.
6. **Slugs** : `formation-…` / `training-…`, jamais modifiés après publication.
7. **Secrets** : le porteur saisit lui-même mot de passe et code e-mail ; ne jamais les lire, noter,
   capturer ni réutiliser.

## Procédure

### 1. Inventaire

```bash
DJANGO_DEBUG=1 .venv/Scripts/python manage.py journal inventaire 02_partie2
```

Liste les dossiers de `reference/cours/<partie>/` sans fichier `.md` dans `nouvelles/<partie>/`.
Une partie sans dossier `nouvelles/` liste tous ses modules.

### 2. Questions de faits (une seule série, avec recommandation)

Pour chaque module listé, demander : a-t-il été suivi ? à quelle date ? qu'a-t-on réellement pratiqué
(proposer une liste tirée des TAF, à confirmer ou corriger) ? durée ? Pour une nouvelle partie, son
intitulé fr/en. Demander aussi les noms à ne jamais publier (formateur, centre) pour `--interdit`,
sans les écrire dans un fichier. Ne traiter que les modules confirmés.

### 3. Lecture des références

Lire chaque image du module avec Read ; un PDF avec `pages` (20 pages au plus par appel). Relever
l'intitulé, la compétence visée, les notions clés et les TAF. Ne rien recopier mot pour mot.

### 4. Rédaction du fichier source

Chemin : `programme_shorts_pedago/nouvelles/<partie>/<NN>_module<N>/module<N>_<sujet>.md`
(ex. `02_partie2/03_module3/module3_simple_allumage.md`). Partir de
[modele_fichier_source.md](modele_fichier_source.md), qui est le format lu par `hub/journal.py`.

- Titre `Formation : <sujet>` / `Training: <subject>` ; 200 caractères au plus.
- Corps : trois paragraphes au plus par langue, séparés par une ligne vide ; le premier situe le
  module (jour, partie, lien avec la clim ou le froid), les suivants disent ce que nous avons retenu.
- Compte rendu : exactement les rubriques `Objet`, `Matériel`, `Déroulement`, `Durée` /
  `Purpose`, `Equipment`, `Procedure`, `Duration`, une ligne « Rubrique : valeur » chacune.
- L'anglais traduit le même contenu, sans ajout.

### 5. Vérification locale et aperçu

```bash
DJANGO_DEBUG=1 .venv/Scripts/python manage.py journal verifier <fichier.md> --interdit "<Nom>"
```

Corriger le fichier jusqu'à « conforme ». Aperçu isolé (base temporaire, aucune donnée fictive) :
`.venv/Scripts/python scripts/preview_site.py --port 8011 --journal programme_shorts_pedago/nouvelles/<partie>`,
puis contrôle Playwright du journal (liste, grille) et des détails fr/en à 1 280 et 390 px, clair et sombre :
aucun débordement, titre du détail sur 2 lignes au plus en ordinateur. Relire soi-même contre les règles 2 à 4 : la commande
ne juge ni l'exactitude ni la qualité de traduction.

### 6. Publication dans Unfold de production (Playwright)

1. Avant tout, vérifier l'absence de doublon : `https://ventisax.pythonanywhere.com/fr/nouvelles/<slug_fr>/`
   doit répondre 404. Une réponse 200 signifie que l'entrée existe : passer en **Correction** (section 8).
2. `browser_navigate` vers `https://ventisax.pythonanywhere.com/admin/` ; demander au porteur de se
   connecter dans la fenêtre ouverte (mot de passe, puis code reçu par e-mail) et attendre sa confirmation.
   Ne pas faire de capture pendant la saisie.
3. Pour chaque fichier, dans l'ordre des modules, **sauf pour plusieurs modules du même jour** : le journal
   trie un même jour par identifiant décroissant (RM-05), donc créer le module le plus élevé d'abord
   (module 4 puis module 3) pour que le module 3 s'affiche au-dessus. Pour chaque entrée : `/admin/hub/nouvelle/add/` ; remplir titres, slugs,
   date du jalon (format affiché par le champ), corps fr/en, compte rendu fr/en ; laisser image,
   alternatives, vidéo et réseaux vides ; dans l'inline des secteurs, « Ajouter » puis choisir
   `Climatisation et froid` ; « Enregistrer ».
4. Dans la liste `/admin/hub/nouvelle/`, cocher les nouvelles entrées, action « Publier les contenus
   complets en français et anglais », « Exécuter ». Lire le message : une erreur de validation se
   corrige dans le contenu (fichier puis Unfold), jamais en la contournant.
5. Si la session expire ou si la connexion échoue : s'arrêter, dire ce qui est publié et ce qui reste.

### 7. Contrôle public, trace et sauvegarde

```bash
DJANGO_DEBUG=1 .venv/Scripts/python manage.py journal comparer <fichier.md>
```

- Doit afficher deux URL « vérifiée » sans écart ; sinon corriger dans Unfold puis recomparer.
- Ouvrir `/fr/nouvelles/` et `/en/nouvelles/` : entrées sous la bonne date (plusieurs modules du même
  jour sont regroupés), compte rendu replié, changement de langue vers la même entrée. Capture
  Playwright de la page publique uniquement.
- Inscrire en tête du fichier source : `Journal de formation : /fr/nouvelles/<slug_fr>/ (JJ/MM/AAAA).`
- Une fois par session de publication : `/admin/database/`, bouton « Envoyer la base courante par
  e-mail » ; lire la confirmation. La réception reste à confirmer par le porteur.

### 8. Correction d'une entrée publiée

Modifier d'abord le fichier source, `journal verifier`, puis dans Unfold ouvrir l'entrée (recherche
par titre français), corriger les deux langues ensemble, « Enregistrer » ; les slugs sont en lecture
seule et ne changent pas. Terminer par `journal comparer`.

### 9. Compte rendu final

Lister : URL publiées ou corrigées (fr/en), résultat de `comparer`, envoi de la sauvegarde, et ce qui
n'a pas été vérifié (réception de l'e-mail, relecture du porteur). Les modules restants de l'inventaire
sont annoncés pour la semaine où ils seront suivis. Le porteur relit après coup et peut dépublier
(action « Dépublier sans supprimer les données »).

## Hors du skill

Capsule vidéo et voix off (`clip-local`, `voix-off-locale`), lien YouTube et réseaux, image
d'illustration, script d'import en base, console PythonAnywhere, secteur Matériel électronique.
