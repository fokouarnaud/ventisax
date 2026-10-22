---
name: ventisax-deploy
description: "Déploie le site Ventisax sur PythonAnywhere (compte ventisax) : contrôles locaux, commits sur develop, avance rapide de main, push GitHub, puis dans la console Bash PythonAnywhere pilotée par Playwright (connexion faite par le porteur) git pull, migrate, collectstatic, check --deploy, rechargement par touch du fichier WSGI, et vérifications publiques. À utiliser quand l'utilisateur demande de « déployer », « mettre en ligne », « pousser en production », « faire le pull sur PythonAnywhere » ou « mettre à jour la base en ligne »."
---

# ventisax-deploy : mise en production sur PythonAnywhere

Procédure éprouvée le 22 octobre 2026 (déploiement `88d92af`). `AGENTS.md` fait foi : **pas de fusion sur
`main` ni de déploiement sans demande explicite du porteur** dans la conversation en cours.

Repères : dépôt `https://github.com/fokouarnaud/ventisax.git` ; serveur `/home/ventisax/ventisax` ;
virtualenv `/home/ventisax/.virtualenvs/ventisax` ; réglages `config.production` ; WSGI
`/var/www/ventisax_pythonanywhere_com_wsgi.py` ; site `https://ventisax.pythonanywhere.com`.

## Règles

1. **Secrets** : le porteur se connecte lui-même à PythonAnywhere et à Unfold (mot de passe, code e-mail).
   Ne jamais écrire un mot de passe dans un fichier, un commit, un compte rendu ou une commande visible ;
   un mot de passe à changer se saisit à l'invite cachée de `changepassword` (le validateur refuse un
   mot de passe proche de l'identifiant : ne pas le contourner).
2. **Sauvegarde avant toute mise à jour technique** : `/admin/database/`, bouton « Envoyer la base
   courante par e-mail » (confirmation « Base courante envoyée par e-mail. »). Si une migration modifie
   des données ou si des médias changent : sauvegarde complète `backupventisax` (voir `docs/exploitation.md`).
3. **Avance rapide uniquement** (`--ff-only`) ; jamais de `--force`, jamais de modification directe sur le serveur.
4. Ne rien déclarer « en ligne » sans vérification publique (étape 5).

## 1. Contrôles locaux (racine `ventisax/`)

```bash
.venv/Scripts/python -m pytest -q          # 5 échecs préexistants tolérés si .env local (voir CLAUDE.md)
DJANGO_DEBUG=1 .venv/Scripts/python manage.py check
DJANGO_DEBUG=1 .venv/Scripts/python manage.py makemigrations --check --dry-run
git status --short                          # rien de privé : programme_shorts_pedago/, .env, db, media, .playwright-mcp/
git diff | grep -i "password\|secret"       # aucun secret
```

## 2. Commits, main, push

```bash
git add <fichiers> && git commit            # message conventionnel + ligne Co-Authored-By
git checkout main && git merge --ff-only develop && git push origin main develop && git checkout develop
```

## 3. Console PythonAnywhere (Playwright)

1. Nouvel onglet `https://www.pythonanywhere.com/user/ventisax/consoles/` ; si la page de connexion
   s'affiche, demander au porteur de se connecter et attendre sa confirmation.
2. Ouvrir `https://www.pythonanywhere.com/user/ventisax/consoles/bash/new` (ou une console existante),
   attendre l'invite `$`, cliquer dans le terminal puis taper avec `page.keyboard.type(..., {delay: 3})`
   suivi de `\n`. Lire le résultat par capture d'écran (le terminal n'expose pas son texte au DOM).
3. Environnement :
   ```bash
   source /home/ventisax/.virtualenvs/ventisax/bin/activate && cd /home/ventisax/ventisax && export DJANGO_SETTINGS_MODULE=config.production
   ```

## 4. Mise à jour du serveur

```bash
git status --short; git log --oneline -1; git pull --ff-only origin main; git log --oneline -1
python manage.py migrate --noinput          # « met à jour la base » ; « No migrations to apply » est normal
python manage.py collectstatic --noinput    # obligatoire à chaque déploiement (ManifestStaticFilesStorage)
python manage.py check --deploy             # attendu : « System check identified no issues »
touch /var/www/ventisax_pythonanywhere_com_wsgi.py   # recharge l'application web
```

Un arbre de travail serveur non propre avant `git pull` : s'arrêter et le signaler.

## 5. Vérifications publiques

Le rechargement prend **quelques secondes** : une première requête peut encore servir l'ancien code.
Toujours borner le temps (`curl -m 20`).

```bash
B=https://ventisax.pythonanywhere.com
for p in /fr/ /en/ /fr/nouvelles/ /en/nouvelles/?vue=grille /fr/contact/; do curl -s -m 20 -o /dev/null -w "%{http_code} $p\n" $B$p; done
curl -s -m 20 $B/fr/ | grep -o '/static/hub/site[^"]*css'      # nom avec empreinte = collectstatic pris en compte
```

Puis vérifier la fonctionnalité livrée (exemple du 22/10 : `/theme/dark/?next=/fr/contact/` → 302 et cookie
`Secure`), `journal comparer` sur les fichiers sources si des entrées ont été touchées, et
`python scripts/check_deployment.py https://ventisax.pythonanywhere.com`. Si le poste local subit des délais
TLS (`handshake operation timed out`, `WinError 10053`), lancer ce script **depuis la console PythonAnywhere**.

## 6. Clôture

- Consigner dans `docs/deploiement-pythonanywhere.md` : commit déployé, migrations, fichiers statiques,
  `check --deploy`, vérifications réussies et **non exercées** ; commiter sur `develop` (et `main` en avance rapide).
- Rappeler au porteur de se déconnecter de la console et de PythonAnywhere dans le navigateur piloté.
- Retour arrière : `git revert <commit>` sur `develop`, puis refaire cette procédure (jamais de réécriture
  d'historique ni de modification directe sur le serveur). Une migration annulée exige une décision du
  porteur et la sauvegarde prise à l'étape « Règles ».
