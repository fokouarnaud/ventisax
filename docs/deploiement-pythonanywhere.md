# Déploiement PythonAnywhere — 10 octobre 2026

Compte autorisé : `ventisax`. L'accès réel par OTP a été confirmé lors du déploiement initial ; les codes de récupération restent à finaliser.

## Journal partie 2, choix du thème — 22 octobre 2026

Quatre entrées du Journal de formation (modules 1 à 4 de la partie 2) publiées dans Unfold le 22/10/2026 à 01:36,
créées dans l'ordre 4, 3, 2, 1 ; `journal comparer` : 8 pages fr/en conformes à leurs fichiers sources. Sauvegarde
de la base courante envoyée par e-mail depuis `/admin/database/` (réception à confirmer par le porteur).

Mot de passe du compte administrateur changé par le porteur dans la console (`changepassword`, saisie privée ;
une première proposition trop proche de l'identifiant a été refusée par le validateur).

Commits `df221b9` et `88d92af` sur develop, main en avance rapide, poussés. Serveur : arbre propre, `git pull
--ff-only` de `428b13b` à `88d92af`, `migrate` sans migration à appliquer, `collectstatic` (2 fichiers copiés,
161 inchangés), `check --deploy` sans problème, rechargement par `touch` du fichier WSGI. Vérifié après quelques
secondes : pages fr/en, journal (liste, grille) et contact en 200 ; sélecteur de thème présent ; `/theme/dark/`
302 vers la page d'origine avec cookie `Secure; SameSite=Lax` ; `data-theme="dark"` rendu avec le cookie ;
feuille `site.<empreinte>.css` contenant les nouveaux jetons ; choix inconnu 404.

Second passage le même jour avec le skill `ventisax-deploy` : `2dc37a2` (hauteur `100dvh`, audit taste) tiré
par avance rapide, aucune migration, 1 fichier statique copié, `check --deploy` sans problème, rechargement. Vérifié
avec Playwright sur le site en ligne : feuille `site.3dad71cb297f.css` contenant `100dvh`, hauteur minimale égale à la
fenêtre à 390 et 1 280 px, aucun débordement, en-tête de 73 px, grille du journal conforme à l'aperçu validé.

Non exercé : `scripts/check_deployment.py`, interrompu deux fois côté poste local (délai TLS, WinError 10053)
puis par une reconnexion de la console. Procédure consignée dans le skill `.claude/skills/ventisax-deploy/`.

## Gestion des versions de base déployée

Le commit `1bf988b` a été fusionné par avance rapide de develop vers main et les deux branches
ont été poussées. Le serveur a récupéré main ; la migration `hub.0007` est appliquée.
`check --deploy` réussit et `collectstatic` confirme 160 fichiers inchangés. L'application a été
réactivée et rechargée après une interruption des écritures pour la sauvegarde et la migration.

Avant mise à jour, SQLite et médias ont été sauvegardés dans
`/home/ventisax/private_backups/pre-versions-20261010` sous permissions privées.
La restauration distante dans `restore-versions-20261010` a réussi. L'archive a été téléchargée
hors hébergement, puis restaurée localement : manifest SHA-256, intégrité SQLite, relations et
présence des médias référencés vérifiés. Le téléchargement navigateur décompresse le transport
gzip : la copie persistante est donc nommée `C:/Users/cedric/.codex/backups/ventisax/pre-versions-20261010.tar`.
Son SHA-256 correspond au flux tar décompressé distant :
`f029a019609214c7c4641126dc5c68042acddc5c3c4a89ecfde663a1d5bed6e8`.
Aucune sauvegarde ni donnée d'authentification n'est suivie dans Git.

Sur Python 3.13, SQLite expose `serialize` et `deserialize`. Un export réel de la base migrée
(335 872 octets) a passé le validateur de compatibilité de la nouvelle gestion des versions.
Les données restent : une configuration, deux secteurs, une nouvelle, zéro lien ; UUID présents
sur tous les contenus, superadministrateur et facteur e-mail confirmé conservés. L'espace total
mesuré par `du -sh /home/ventisax` est 136 Mio, sous le quota affiché de 512 Mio.

Le script `check_deployment.py` réussit sans modification : fr/en et CSS 200 ; `.env`, SQLite
et média privé 404 ; admin anonyme 302 ; connexion 200 ; protections HTTPS vérifiées.
Les deux accueils ont aussi été affichés dans le navigateur intégré ; capture :
`docs/screenshots/pythonanywhere-versions-live.png`.

La suite locale de la fonctionnalité compte 118 tests réussis. L'ouverture authentifiée de
`/admin/database/` après ce déploiement reste à vérifier : l'identifiant `fokou` avec le mot de
passe fourni pour cette opération a été refusé ; aucun changement de mot de passe ni contournement
du second facteur n'a été effectué. Aucun e-mail contenant la base ni échange des bases de
production n'a été exécuté pendant le déploiement. Les tests locaux couvrent ces comportements.
Les sauvegardes de maintenance privées antérieures restent conservées pour le retour arrière ;
les deux emplacements de l'interface sont distincts de ces archives de déploiement.

## Accès administrateur et contact confirmés

Le porteur a défini son mot de passe dans la console privée ; Django a confirmé son enregistrement.
La connexion du compte `fokou` a réussi dans le Browser intégré. Le facteur Courriel a été choisi,
puis le porteur a reçu et validé son OTP. L’administration Unfold a ensuite été affichée :
`docs/screenshots/pythonanywhere-admin-email-verified.jpg`. Aucun mot de passe ni code n’est consigné ici.

Le numéro WhatsApp public fourni par le porteur a été enregistré via le formulaire de configuration
générale dans Unfold, avec confirmation de modification réussie. Les pages Contact fr/en affichent
le lien exact `https://wa.me/237652317898` ; capture française :
`docs/screenshots/pythonanywhere-whatsapp-live.jpg`. Ces coordonnées sont enregistrées dans la base
distante et restent modifiables par l’administrateur ; aucune base SQLite n’est poussée dans Git.

Les codes de récupération, leur conservation hors hébergement et une récupération réelle restent
à finaliser, ainsi que la sauvegarde téléchargée et la restauration distante isolée.
Les sections suivantes retracent les étapes antérieures et leurs limites au moment des observations.

## SMTP et HTTPS — reprise réussie

La console a retrouvé sa connexion. Une sauvegarde SQLite cohérente et les médias ont été
copiés dans `/home/ventisax/private_backups/pre-email-20261010`, répertoire privé 700.
Cette copie distante ne remplace pas une sauvegarde téléchargée et restaurée hors hébergement.

Gmail a accepté l’authentification SMTP avec TLS et un message de test adressé au porteur.
Le secret a été saisi sans écho ni inscription dans l’historique des commandes, puis enregistré
dans `.env` (600), hors Git. `DJANGO_EMAIL_OTP=1` est activé. Les six migrations du composant
`otp_email` et `check --deploy` ont réussi ; l’application a été rechargée.
L’acceptation SMTP ne prouve pas encore la réception ni l’usage d’un OTP réel.

Le script `check_deployment.py`, exécuté sur PythonAnywhere contre l’URL publique, a réussi
sans modification des assertions : fr/en et CSS 200 ; `.env`, SQLite et média privé 404 ;
admin anonyme 302 ; connexion 200 ; cookies sécurisés, protection contre l’encadrement,
HSTS et redirection HTTP vers HTTPS vérifiés. La connexion française a également été affichée
dans le Browser intégré. Preuve : `docs/screenshots/pythonanywhere-https-email-ready.jpg`.

Le compte `fokou` existe. La commande privée `changepassword fokou` est positionnée à son
invite de saisie ; aucun résultat de définition du mot de passe n’est encore confirmé.
Réception, enrôlement du facteur e-mail, connexion réelle à Unfold et récupération restent ouverts.
Les sections suivantes conservent les constats précédents.

## État actualisé après initialisation autorisée

- Commit `e2b02f6` poussé sur main après develop et avance rapide ; récupéré sur le serveur.
- Migration `hub.0006` et `check --deploy` réussis. Suite locale : 99 tests réussis.
- `seed_content --email ADRESSE_PUBLIQUE --announce-classes` exécuté sur la base distante :
  une configuration générale, deux secteurs publics en préparation et une nouvelle publique.
  L’annonce bilingue présente le début des cours et la présentation des locaux comme prévus
  le 12 octobre 2026. Les contenus restent modifiables dans Unfold.
- Aucun numéro WhatsApp inventé : champ facultatif, contact e-mail conservé, lien WhatsApp masqué
  jusqu’à l’ajout d’un numéro international valide.
- Après Reload, les accueils français et anglais ont été affichés dans le Browser intégré.
  Capture : `docs/screenshots/pythonanywhere-content-live.jpg`. Le contrôle HTTP a obtenu
  200 pour les deux accueils et le CSS, 404 pour `.env`, puis une réinitialisation de connexion
  au contrôle SQLite. Le contact anglais et la console ont ensuite rencontré la même coupure.
  La vérification complète HTTPS reste ouverte ; le script n’a pas été affaibli.
- Compte administrateur `fokou` créé avec l’adresse fournie ; aucun mot de passe utilisable
  n’est encore défini. Il ne constitue donc pas encore un accès fonctionnel. La saisie privée
  du mot de passe et l’enrôlement du second facteur restent à terminer.
- Paramètres Gmail préparés dans `.env` privé (permissions 600), sans secret SMTP.
  L’option OTP e-mail reste désactivée tant que l’envoi réel n’est pas possible.
  Aucun e-mail réel n’a été envoyé. La connexion Google autorisée a atteint la validation
  sur téléphone ; création du mot de passe d’application et réception restent à vérifier.

Les sections suivantes conservent l’historique des vérifications précédentes.

## Résultats observés

- Commit initial `d4796f4` créé sur develop, fusionné par avance rapide sur main et poussé vers le dépôt GitHub demandé.
- Commit `26c4229` : procédure README, `.env` privé, configuration production, OTP e-mail optionnel et initialisation bilingue ; même parcours develop → main → push.
- 97 tests locaux réussis ; contrôles Django, migrations manquantes et dépendances sans problème.
- Dépôt cloné puis mis à jour dans `/home/ventisax/ventisax`. Python 3.13.1 et virtualenv `/home/ventisax/.virtualenvs/ventisax` ; exigences installées, dont python-dotenv.
- `.env` créé avec clé aléatoire générée sur le serveur, sans affichage ; permissions `600`, DEBUG désactivé, hôte limité au domaine du compte. Aucun secret ajouté à Git.
- Migrations, `check --deploy` et collecte de 160 fichiers statiques exécutés avec succès. Les doublons admin signalés par collectstatic correspondent aux fichiers surchargés par Unfold, installé avant l'admin Django.
- Application Manual configuration / Python 3.13 créée ; code, répertoire de travail, virtualenv, WSGI Django et mappings statiques/médias renseignés. Force HTTPS activé puis application rechargée.
- `du -sh /home/ventisax` : **132 Mio**, soit environ **380 Mio de marge** sous 512 Mio à cette étape. Échéance affichée : **10 novembre 2026** ; renouvellement manuel requis.
- Browser intégré : `/fr/` a affiché la page Django « En préparation » via HTTPS.
- Contrôles HTTP : `/fr/` et `/en/` ont répondu 503 (configuration éditoriale absente), `/static/hub/site.css` 200 et `/.env` 404.

## Limites et reprise

La vérification HTTP a ensuite échoué par délai de connexion sur `/db.sqlite3`. La navigation anglaise et le tableau de bord PythonAnywhere ont également rencontré des délais de connexion ; la console s'est déconnectée. La cause réseau n'est pas établie. Ne pas interpréter ces contrôles partiels comme un lancement validé.

La commande de préparation du compte `fokou` sans mot de passe utilisable et du brouillon bilingue annoncé pour le 12 octobre a été envoyée pendant la coupure, **sans résultat confirmé**. Vérifier l'état de la base avant de reprendre ; aucune affirmation de création ni de publication n'est justifiée à cette étape.

Le numéro WhatsApp public n'a pas été fourni. Le jalon précisé par le porteur est le début des cours et la présentation des locaux **prévus le 12 octobre 2026** ; le texte préparé est une annonce d'événement à venir, pas une réalisation accomplie. La commande `seed_content` exige les contacts authentiques avant création de la configuration publique. Aucun contact de test n'est utilisé en production.

L'option e-mail n'est pas activée sur le serveur : compte et secret SMTP manquants. Le test local utilise un transport en mémoire et ne prouve pas une livraison réelle. Aucun OTP réel n'a été envoyé. L'administrateur doit disposer d'un mot de passe utilisable et enrôler son facteur ; les contrôles d'accès OTP restent en place.

Après rétablissement de la connexion, renseigner les contacts et SMTP privés, vérifier/créer le compte, tester réception et usage unique du code puis récupération, initialiser et relire les contenus, et terminer les contrôles suivants :

```bash
python scripts/check_deployment.py https://ventisax.pythonanywhere.com --preparing
```

Retirer `--preparing` lorsque la configuration authentique est publiée. Le script ne fait que des GET et ne modifie aucune donnée. Il contrôle aussi les chemins privés, l'administration anonyme, les cookies et la redirection HTTP → HTTPS ; ces derniers contrôles n'ont pas abouti lors de la coupure.

Effectuer et télécharger une sauvegarde privée, puis démontrer sa restauration isolée suivant `docs/exploitation.md`. Cette preuve distante et les critères de lancement de la Definition of Done restent ouverts.

Capture de l'interruption de console : `docs/screenshots/pythonanywhere-console.jpg`.

## Recontrôle de la page Web à la demande du porteur

La page Web a été rouverte dans un onglet neuf après l'erreur réseau de l'ancien onglet.
Les paramètres persistants suivants ont été lus : Python 3.13 ; source et répertoire de travail
`/home/ventisax/ventisax` ; virtualenv `/home/ventisax/.virtualenvs/ventisax` ; mappings `/static/`
et `/media/` vers les répertoires correspondants du projet ; Force HTTPS activé et certificat fourni.
L'éditeur WSGI a confirmé le code enregistré et `DJANGO_SETTINGS_MODULE=config.production`.
L'application a été rechargée, puis le bouton Reload est redevenu disponible.
Capture de la configuration : `docs/screenshots/pythonanywhere-web-configured.jpg`.

Le contrôle HTTP a de nouveau obtenu 503 pour les pages bilingues, 200 pour le CSS et 404 pour `.env`,
puis a échoué par réinitialisation de connexion sur le contrôle SQLite. Une ouverture Browser neuve
de `/en/` a également échoué par réinitialisation de connexion. Les paramètres Web sont donc
effectivement enregistrés ; l'initialisation éditoriale et la vérification complète du site restent ouvertes.

La console a ensuite retrouvé sa connexion. Une lecture directe des modèles a confirmé :
configuration générale 0, secteurs 0, nouvelles 0 et compte `fokou` absent.
La commande envoyée pendant la précédente coupure n'avait donc pas préparé ces données.
L'absence de configuration générale explique le 503 de préparation ; aucun paramètre Web manquant
n'a été constaté lors de ce recontrôle.

## Déploiement du 16 octobre 2026 (demande explicite du porteur)

- Sauvegarde cohérente de la base de production avant toute opération (`~/deploy-backups/prod-avant-deploiement-2026-10-16.sqlite3`, droits 600) et copie téléchargée hors hébergement ; intégrité vérifiée (1 nouvelle, 1 compte).
- Code mis à jour en `8f6741c`, puis, à la demande du porteur, dossier applicatif recréé par `git clone` de `main` ; `.env`, base et `backups/admin` repris de l'ancien dossier avant sa suppression. Migrations `0008` à `0011` appliquées, `check --deploy` sans problème, statiques collectés, application rechargée.
- Base préparée en local importée par la même séquence que « Charger le fichier comme courante » (empreinte SHA-256 vérifiée, accès et second facteur de production conservés, ancienne courante placée en backup).
- Contrôle en ligne (navigateur) : accueil, journal en liste et en grille (4 jours, 7 entrées), compte rendu replié, contact `fokouvirtualone@gmail.com` et lien « Me prévenir » ; `/db.sqlite3` et `/.env` répondent 404, `/admin/` redirige vers la connexion. Espace utilisé : 136 Mio.
- Non exercé : connexion administrateur avec second facteur après l'import (sessions réinitialisées), envoi réel du message WhatsApp.

## Déploiement du 22 octobre 2026, `0ca1593` (demande explicite du porteur : « déploie en production »)

Procédure du skill `ventisax-deploy`.

- Contrôles locaux : suite à 204 tests réussis, `check` et `makemigrations --check` sans constat, arbre propre,
  aucun secret dans les changements ; `main` avancé en avance rapide de `92a009c` à `0ca1593` et poussé.
- Sauvegarde avant mise à jour : base courante envoyée par e-mail au superadministrateur depuis la console
  PythonAnywhere, par le même code que le bouton d'Unfold (`snapshot()` puis `EmailMessage`), la session Unfold
  n'étant pas ouverte ; envoi accepté par le serveur SMTP (1 message, 405 504 octets, `20261022T055915Z`).
- Serveur : arbre propre à `92a009c` ; `git pull --ff-only` jusqu'à `0ca1593` ; migration `0012`
  (`academie_url`) appliquée ; `collectstatic` (1 fichier copié, 120 post-traités) ; `check --deploy` sans
  problème ; WSGI rechargé.
- Vérifications : `/fr/`, `/en/`, journal en liste et en grille, Contact fr/en en 200 ; CSS servi avec empreinte
  (`site.b9e261d92218.css`) contenant les règles du jour ; bloc Académie absent tant que l'adresse n'est pas saisie
  (attendu) ; `journal comparer` sans écart sur les quatre entrées de la partie 2 (huit pages) ;
  `check_deployment.py` lancé depuis la console (le poste local subissait `WinError 10054`) : pages 200, `.env`,
  `db.sqlite3` et `media/.env` en 404, `/admin/` en 302, connexion 200, HTTP vers HTTPS vérifié.
- Non exercé : réception effective de l'e-mail de sauvegarde ; bloc Académie en ligne (adresse à saisir par le
  porteur dans Unfold, section « Académie ») ; téléphone physique.
- Complément (demande du porteur : le lien vers l'Académie n'apparaissait pas) : `academie_url` renseignée en
  production à `https://acadventisax.pythonanywhere.com/` depuis la console (`ConfigurationGenerale.save()`, avec
  validation complète ; valeur précédente vide). Vérifié en ligne : bloc et lien (nouvel onglet,
  `rel="noopener noreferrer"`) présents sur le journal, une entrée et Contact en fr et en, absents de l'accueil et de
  la présentation ; demande d'accès WhatsApp pré-remplie sur le numéro public.
- Complément (demande du porteur) : coordonnées publiques de production mises à jour depuis la console
  (`ConfigurationGenerale.save()`, validation complète) : e-mail `fokouarnaud@gmail.com` (auparavant
  `fokouvirtualone@gmail.com`), WhatsApp `+237652317898` (inchangé, format international). Vérifié en ligne :
  liens e-mail et WhatsApp de Contact, de « Me prévenir » et de la demande d'accès à l'Académie sur les nouvelles
  coordonnées, en fr et en ; ancienne adresse absente.

## Déploiement du 23 octobre 2026, `d6f958e` (demande explicite du porteur : déployer avec le skill deploy après passe taste)

Procédure du skill `ventisax-deploy`, entièrement par la console PythonAnywhere (le porteur a demandé de ne pas passer
par Unfold).

- Contrôles locaux : 211 tests réussis, `check` et `makemigrations --check` sans constat, passe taste du bloc
  (`docs/validation-interface.md`), aucun secret dans les changements ; `main` avancé de `151d57f` à `d6f958e` et poussé.
- Sauvegarde avant mise à jour : copie SQLite cohérente par l'API `backup`
  (`/home/ventisax/backups/avant-0013-20261023.sqlite3`).
- Serveur : arbre propre à `0ca1593` ; `git pull --ff-only` jusqu'à `d6f958e` ; migration `0013`
  (`Secteur.formation_url`) appliquée ; `collectstatic` (1 fichier copié, 120 post-traités) ; `check --deploy` sans
  problème ; WSGI rechargé.
- Contenu (US-29) : secteur « Matériel électronique » mis à jour depuis la console par `Secteur.save()` (validation
  complète) : `formation_url` = `https://electroacadventisax.pythonanywhere.com/fr/catalogue/` (auparavant vide),
  apprentissages et prochaine étape fr/en du PRD ; publié, en préparation, slugs inchangés. Script transmis en base64
  (SHA-256 identique), fichier temporaire supprimé.
- Après publication : base courante envoyée par e-mail au superadministrateur depuis la console, par le code du bouton
  d'Unfold ; envoi accepté par le serveur SMTP (1 message, 405 504 octets, `20261023T191430Z`).
- Vérifications : `/fr/`, `/en/`, journal en liste et en grille, Contact, fiches secteur fr/en en 200 ; CSS avec
  empreinte `site.94d5ee650ff3.css` contenant `.formation-panel` ; bloc « Approfondir en ligne » présent une fois sur
  la fiche électronique fr et en, absent de l'accueil, du journal, de Contact et de la fiche clim ; ni « centre de
  formation », ni « gratuit », ni « certificat » ; Playwright sur le site réel à 320 et 1 280 px, clair et sombre :
  aucun débordement, lien de 44 px ; clic : nouvel onglet sur le catalogue Electro Acad, `window.opener` nul ;
  `check_deployment.py` depuis la console (le poste local subissait `WinError 10060`) : pages 200, `.env`,
  `db.sqlite3` et `media/.env` en 404, `/admin/` en 302, connexion 200, HTTP vers HTTPS vérifié.
- Non exercé : réception effective de l'e-mail de sauvegarde ; saisie de l'adresse dans le formulaire Unfold réel ;
  téléphone physique ; correction de « centre de formation » sur Electro Acad (à la charge du porteur).

