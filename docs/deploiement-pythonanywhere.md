# Déploiement PythonAnywhere — 10 octobre 2026

Compte autorisé : `ventisax`. Le lancement éditorial et l'accès réel par OTP restent à terminer.

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
