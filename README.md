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

La gestion manuelle de la base courante et d’un backup est accessible depuis l’accueil Unfold.
Voir [la procédure des versions de base](docs/versions-bd.md) pour sauvegarder, charger,
interchanger, télécharger ou envoyer la courante par e-mail. Appliquer la migration `0007`
après sauvegarde avant d’utiliser ces commandes. Les contenus reçoivent des UUID sans changement d’URL.

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

## Publication sur PythonAnywhere gratuit

Procédure pour le compte `ventisax`, avec Python 3.13. Aucun secret ni fichier SQLite ne doit être ajouté à Git.
Références : [déployer Django](https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/),
[variables privées](https://help.pythonanywhere.com/pages/EnvironmentVariables/) et
[limites du compte gratuit](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/).

Dans **Files → /home/ventisax → Open Bash console here** :

```bash
git clone --branch main https://github.com/fokouarnaud/ventisax.git /home/ventisax/ventisax
python3.13 -m venv /home/ventisax/.virtualenvs/ventisax
source /home/ventisax/.virtualenvs/ventisax/bin/activate
cd /home/ventisax/ventisax
pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
python -c "import secrets; from pathlib import Path; p=Path('.env'); p.write_text(p.read_text().replace('DJANGO_SECRET_KEY=','DJANGO_SECRET_KEY='+secrets.token_urlsafe(48)))"
```

La commande génère la clé sans l’afficher. Compléter `.env` dans l’éditeur privé PythonAnywhere.
Les valeurs du processus prévalent sur celles du fichier. Ne jamais activer `DJANGO_DEBUG=1` en production.

Pour l’OTP par e-mail demandé le 10 octobre 2026, renseigner un compte SMTP autorisé,
son mot de passe d’application dans `EMAIL_HOST_PASSWORD` et `DJANGO_EMAIL_OTP=1`.
Le mot de passe de connexion PythonAnywhere ou Django n’est pas un mot de passe SMTP.
Les codes expirent après cinq minutes, ne sont utilisables qu’une fois et les renvois sont espacés de 60 secondes.
La disponibilité et les restrictions SMTP du compte gratuit doivent être vérifiées sur le compte réel.
Sans SMTP opérationnel, conserver l’application en préparation ; ne pas contourner le second facteur.

```bash
export DJANGO_SETTINGS_MODULE=config.production
python manage.py migrate
python manage.py check --deploy
python manage.py collectstatic --noinput
python manage.py createsuperuser --username fokou --email fokouvirtualone@gmail.com
```

Saisir le mot de passe dans l’invite privée. Avec l’OTP e-mail activé, le compte peut enrôler
son adresse via `/account/two_factor/setup/` et doit prouver sa réception avant tout accès à Unfold.
Le choix de méthode permet aussi l’application mobile. Les codes de récupération restent disponibles après vérification.

Initialiser les contenus validés uniquement avec de vraies coordonnées publiques :

```bash
python manage.py seed_content --email ADRESSE_PUBLIQUE --announce-classes
```

Cette commande crée la présentation bilingue, les deux secteurs en préparation et, avec
`--announce-classes`, l’annonce autorisée du début des cours et de la présentation des locaux
prévus le 12 octobre 2026. Elle conserve les contenus déjà présents. Sans cette option, aucune nouvelle n’est créée.
Ajouter `--whatsapp +NUMERO_INTERNATIONAL` uniquement avec un numéro public authentique.
Le numéro peut être ajouté ultérieurement dans Unfold ; sans numéro, seul le contact e-mail apparaît.
Ne pas présenter l’annonce comme un événement déjà accompli.
Relire les traductions et les contacts avant publication.

Dans **Web → Add a new web app**, choisir **Manual configuration**, puis **Python 3.13**.
Renseigner `/home/ventisax/ventisax` comme code source et répertoire de travail,
et `/home/ventisax/.virtualenvs/ventisax` comme virtualenv. Remplacer le contenu du fichier WSGI proposé par :

```python
import os
import sys

project = '/home/ventisax/ventisax'
if project not in sys.path:
    sys.path.insert(0, project)
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.production'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Ajouter les mappings `/static/` → `/home/ventisax/ventisax/staticfiles/` et
`/media/` → `/home/ventisax/ventisax/media/`. Aucun mapping pour le projet complet, `.env`, SQLite ou les sauvegardes.
Activer **Force HTTPS**, puis **Reload**. Vérifier `/fr/`, `/en/`, les statiques et
la connexion avec mot de passe puis OTP ; vérifier également que le mot de passe seul ne donne pas accès à `/admin/`.
`config.production` fait confiance à l’en-tête HTTPS du proxy PythonAnywhere ; ne pas réutiliser cette configuration
derrière un proxy qui laisse les visiteurs fixer cet en-tête.

Mesurer `du -sh /home/ventisax` et garder une marge sous 512 Mio pour le compte entier.
Noter l’échéance affichée dans Web et renouveler manuellement chaque mois.
Effectuer une sauvegarde et une restauration isolée selon `docs/exploitation.md` avant lancement et chaque mise à jour.
Pour mettre à jour ensuite : arrêter les écritures, sauvegarder, `git pull --ff-only origin main`,
installer les exigences, migrer, collecter les statiques, contrôler, puis recharger l’application.

L'état réellement constaté et les étapes encore ouvertes sont consignés dans
[docs/deploiement-pythonanywhere.md](docs/deploiement-pythonanywhere.md).
