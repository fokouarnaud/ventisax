# Ventisax

Backend Django/SQLite et administration Unfold du hub de progression bilingue décrit dans `AGENTS.md`.
Le développement backend a été autorisé par la demande explicite du 10 octobre 2026. Le brief et son entretien sont conservés.

## Installation locale (PowerShell)

Environnement vérifié : Windows, Python 3.14.3, Django 5.2.18.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
$env:DJANGO_DEBUG = "1"
.venv/Scripts/python manage.py migrate
$env:DJANGO_SECRET_KEY = .venv/Scripts/python -c "import secrets; print(secrets.token_urlsafe(48))"
.venv/Scripts/python manage.py createsuperuser
.venv/Scripts/python manage.py runserver
```

Ouvrir `/account/login/`, se connecter puis aller à `/account/two_factor/setup/` pour enrôler l’application mobile.
L’accès à `/admin/` reste refusé avant vérification du second facteur. Une fois vérifié, générer les codes dans
`/account/two_factor/backup/tokens/` et les conserver hors du site. Aucun compte ni mot de passe par défaut n’est créé.
Conserver une clé privée stable dans l’environnement pour ne pas invalider les sessions au redémarrage ; sans clé,
le mode local génère une clé éphémère. En production, la clé est obligatoire.
Le mode debug exige désormais `DJANGO_DEBUG=1` explicitement ; sans cette option,
le démarrage utilise les protections de production et refuse une clé absente.
Les sessions expirent après 30 minutes d’inactivité et leur cookie est non persistant.
Un compte ayant déjà un facteur confirmé ne peut pas reprendre l’enrôlement initial,
même par POST depuis une ancienne session ; utiliser les codes ou la procédure privée.

Dans Unfold, créer la configuration générale bilingue, les secteurs puis les nouvelles. Enregistrer les textes,
liens et associations comme brouillons, puis sélectionner l’action **Publier les contenus complets en français et anglais**.
L’état publié est en lecture seule dans le formulaire ; la publication et la dépublication sont explicites.
Les URL deviennent non modifiables après publication. Dépublier avant de rendre une traduction incomplète.
Les actions de publication traitent chaque contenu indépendamment et signalent les champs invalides.

La base locale ne contient aucun contenu éditorial. Sans configuration, les pages publiques répondent 503 avec un message bilingue.
Les données de test ne sont créées que dans les bases et médias temporaires.

## Vérifier

```powershell
.venv/Scripts/python -m pytest -q
.venv/Scripts/python manage.py check
.venv/Scripts/python manage.py makemigrations --check --dry-run
.venv/Scripts/python -m pip check
.venv/Scripts/python scripts/smoke_backend.py
```

Voir `docs/tdd.md` pour les cycles observés et la correspondance avec les User Stories.
L'audit de sécurité, ses 27 sondes supplémentaires et les preuves Browser figurent dans
`docs/audit-securite.md`. Relancer uniquement ces sondes avec
`.venv/Scripts/python -m pytest tests/test_security.py -q`.
Pour les essais d'administration sans toucher aux comptes existants, utiliser
`.venv/Scripts/python scripts/security_preview.py` ; les identifiants synthétiques restent
dans le répertoire temporaire annoncé par la commande.
Le script smoke démarre un serveur HTTP éphémère avec une base isolée, consulte les pages bilingues et exerce une restauration.
Il ne modifie pas `db.sqlite3` ni les médias du projet.

## Exploitation et lancement

La procédure est dans `docs/exploitation.md`. Le déploiement PythonAnywhere, les contenus authentiques,
leur relecture et l’enrôlement du véritable administrateur restent à effectuer avant lancement.
Les templates publics et les assets locaux sont maintenant mis en forme et vérifiés dans le navigateur en français
et en anglais, à 360, 768 et 1 280 pixels, avec des parcours au clavier. Voir `docs/validation-interface.md`.
Ces vérifications ne constituent pas un audit exhaustif d’accessibilité ni un essai sur téléphone physique.

## Aperçu de l’interface

```powershell
.venv/Scripts/python scripts/preview_site.py
```

Ouvrir `http://127.0.0.1:8000/fr/`. Le serveur utilise une base et des médias temporaires, avec un bandeau
explicite de démonstration. Ses textes, coordonnées et jalons sont fictifs ; ils ne sont jamais ajoutés à la base du projet.
Un troisième secteur de démonstration sert uniquement à vérifier l’état sans nouvelle. Arrêter avec Ctrl+C.
Pour vérifier la page sans configuration, lancer `scripts/preview_site.py --empty --port 8001`.

Le CSS, l’icône, le décor de l’accueil et un petit script d’interactions résident dans `hub/static/hub/`.
Le script replie le menu mobile, ferme le bandeau de démonstration et propose le retour en haut.
Sans JavaScript, la navigation reste visible et utilisable. Aucune police distante ni aucun framework CSS externe n’est requis.
