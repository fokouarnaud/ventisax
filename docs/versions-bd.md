# Gestion des bases dans Unfold

Décision du 10 octobre 2026 : l’administrateur dispose désormais d’opérations manuelles de sauvegarde, import, permutation et export par e-mail. Cette demande fait évoluer le cadrage initial, qui prévoyait uniquement des commandes privées. Aucun envoi programmé ni déploiement n’est ajouté.

Depuis l’accueil de l’administration, ouvrir **Gérer les versions de base de données** (`/admin/database/`). Un superadministrateur ayant vérifié son second facteur est nécessaire. Toutes les mutations passent par POST avec protection CSRF.

| Action | Résultat |
| --- | --- |
| Sauvegarder la courante en backup | Remplace le backup par un instantané cohérent de SQLite, avec un nouvel UUID et sa date UTC. |
| Interchanger courante et backup | Active les contenus du backup et place l’ancienne courante dans le backup. |
| Charger le fichier en backup | Contrôle puis remplace uniquement le backup. |
| Charger le fichier comme courante | Contrôle puis active les contenus importés ; l’ancienne courante devient le backup. |
| Télécharger la courante / le backup | Produit une pièce jointe SQLite datée en UTC, sans conserver un troisième export sur disque. |
| Envoyer la courante par e-mail | Un bouton envoie un instantané daté avec UUID, à l’adresse du compte connecté ou à l’adresse saisie. |

Les opérations qui remplacent un emplacement exigent la case de confirmation. Télécharger une copie hors hébergement avant de remplacer le backup. La première sauvegarde peut être créée sans cette case, car elle ne remplace aucun backup.

## Stockage, compatibilité et accès

Les deux emplacements persistants gérés sont la base configurée par Django et `backups/admin/backup.sqlite3`. Le répertoire privé contient également un petit verrou, sans données éditoriales. Aucun historique de copies SQLite ne s’accumule. Un fichier temporaire existe pendant le remplacement atomique du backup ; prévoir au moins la taille d’une base supplémentaire en espace libre durant cette opération, en plus des journaux SQLite. Les instantanés de travail sont en mémoire, limités à 20 Mio par base ; l’envoi par e-mail est limité à 10 Mio avant encodage MIME. Ces limites ne garantissent pas le quota de 512 Mio du compte : mesurer le compte entier et conserver une marge avant utilisation. Les sauvegardes manuelles anciennes restent sous la responsabilité de l’exploitant.

Un import doit présenter exactement le schéma et la liste des migrations de l’application installée, passer les contrôles SQLite d’intégrité et de clés étrangères, et respecter les champs, UUID, liens et publications bilingues requis. Une ancienne base doit être migrée dans un environnement isolé avant import. Le chargement attribue un nouvel UUID de version et sa date UTC ; les UUID des contenus sont conservés.

Les comptes, mots de passe hachés, permissions, appareils OTP, état des codes de récupération et limitations Axes **actuels** sont conservés lors de l’activation. Les comptes contenus dans le fichier importé ne deviennent pas des accès administratifs. Toutes les sessions sont supprimées ; se reconnecter avec les accès actuels. La restauration complète des accès après un sinistre reste une opération privée hors ligne suivant la procédure d’exploitation.

Les requêtes Django sont sérialisées par un verrou de fichier et de thread, depuis l’authentification jusqu’à l’enregistrement des sessions. Arrêter les commandes CLI, migrations et autres processus qui écrivent sans ce verrou avant toute opération. Le remplacement de la courante utilise l’API de sauvegarde SQLite et garde le fichier actif en place. La copie de l’ancienne courante est enregistrée avant activation : un échec d’écriture du backup laisse la courante intacte. Les deux emplacements ne forment pas une transaction distribuée : une interruption du processus entre ces étapes peut laisser deux copies de l’ancienne courante. Garder l’export hors hébergement pour récupérer la version que l’on souhaitait activer.

## Médias, e-mail et temps

Le fichier SQLite ne contient pas les images. Sauvegarder les médias séparément avec `backupventisax`, comme auparavant. Un import faisant référence à une image absente du répertoire média est refusé. Une image encore utilisée par le backup est protégée de la suppression normale lors de l’édition d’une nouvelle. Après remplacement réussi du backup, ses anciennes images sont supprimées uniquement si aucune des deux bases ne les utilise encore. Un échec de nettoyage affiche un avertissement pour une intervention manuelle ; aucun autre fichier du répertoire média n’est parcouru ou supprimé.

L’envoi réutilise les variables SMTP privées existantes : `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`. Il exige un SMTP opérationnel ; aucune adresse SMTP ni aucun secret n’est saisi dans cette page. Le succès signifie que le backend a accepté le message, pas qu’il est déjà livré dans la boîte du destinataire. Une erreur SMTP ou une base trop volumineuse affiche un refus sans message de succès. La base exportée contient des données d’authentification privées : choisir un destinataire de confiance. Aucun e-mail réel n’est envoyé par les tests ni l’aperçu isolé.

Les UUID sont également ajoutés aux secteurs, nouvelles, liens et à la configuration générale. La migration remplit chaque ligne existante avec un UUID distinct avant d’appliquer l’unicité. Les clés internes, associations et URL publiques restent stables.

`USE_TZ=True` conserve les instants UTC en SQLite. L’interface applique explicitement `localtime` pour `Africa/Douala` et présente aussi l’instant UTC ; les noms d’export utilisent UTC avec `Z`. La date civile d’un jalon reste une date, sans conversion de fuseau.

## Vérification locale

```powershell
.venv/Scripts/python -m pytest tests/test_database_versions.py -q
.venv/Scripts/python -m pytest -q
$env:DJANGO_DEBUG = "1"
.venv/Scripts/python manage.py check
.venv/Scripts/python manage.py makemigrations --check --dry-run
```

Avant mise à jour sur l’hébergement : sauvegarder SQLite et médias hors ligne, arrêter les écritures, installer le code, exécuter `manage.py migrate`, collecter les statiques et recharger l’application. Vérifier ensuite la livraison SMTP réelle, l’espace disponible et la restauration avec les médias réels. Aucune base de production n’a été remplacée pendant le développement.

Résultats du 10 octobre 2026 : **118 tests réussis**, dont 19 ciblés sur les versions de bases ; `check`, contrôle des migrations et `pip check` sans erreur. Les 14 tests d’administration ont aussi été relancés après l’ajustement du template d’accueil. Le parcours HTTP public et une restauration isolée passent également. Les tests ont d’abord constaté l’absence de page, puis reproduit les imports invalides, la panne de stockage avant activation, le manque de refus anticipé des fichiers trop volumineux et la conservation inutile d’une image après remplacement du backup. Les tests de migration des contenus existants et de conservation des images ont été ajoutés comme vérifications après l’implémentation.

Dans le navigateur intégré : connexion réelle par mot de passe et TOTP, sauvegarde au clavier, export par backend e-mail local, refus sans confirmation, permutation et reconnexion observés. Le message MIME généré a été relu pour vérifier destinataire, nom daté, UUID et pièce jointe SQLite. Le rendu final mesure 305 px de largeur de document à 320 px de viewport et 345 px à 360 px, sans débordement ; les boutons métier atteignent au moins 44 px. Captures : `docs/screenshots/database-admin-320.png` et `docs/screenshots/database-admin-desktop.png`. Imports des deux emplacements et téléchargements couverts par les tests HTTP Django ; non exercés via le sélecteur de fichiers du navigateur. Livraison SMTP externe, panne système pendant permutation, Linux, quota réel PythonAnywhere et téléphone physique non exercés.

Références techniques : [API de sauvegarde SQLite de Python](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup) et [pièces jointes e-mail de Django](https://docs.djangoproject.com/en/5.2/topics/email/#emailmessage-objects).
