# Audit de sécurité local — 10 octobre 2026

Deux failles d'enrôlement TOTP ont été reproduites et corrigées. Aucune injection SQL ni exécution XSS n'a été reproduite dans les scénarios exercés. Ce constat local n'est ni une certification ni une preuve de sécurité du futur hébergement.

## Failles et correctifs

| Constat | Avant correction | Preuve après correction |
| --- | --- | --- |
| **S-01 — élevée, ajout d'appareil depuis une ancienne session** | Une session obtenue par mot de passe avant l'enrôlement pouvait reprendre les POST du wizard, obtenir une nouvelle clé, valider son propre appareil et ouvrir Unfold : 200 au lieu de 302. Le composant tiers ne bloquait l'appareil existant que dans GET. Un mot de passe seul ne suffit pas à créer cette session après un enrôlement déjà terminé. | Middleware refusant setup/QR, GET et POST, dès qu'un appareil confirmé existe, quel que soit son nom. Tests de reprise après enrôlement et de wizard commencé avant l'enrôlement dans un autre onglet : 403, aucun appareil ajouté, accès admin refusé. |
| **S-02 — élevée, cookie inchangé à l'élévation OTP initiale** | Une copie du cookie prise avant la validation du premier appareil ouvrait ensuite Unfold : 200. | Rotation à la réussite de l'enrôlement, ancienne session révoquée. Le navigateur légitime conserve l'accès, la copie revient à la connexion. La connexion TOTP habituelle faisait déjà tourner son identifiant. |
| **S-03 — configuration, debug implicite** | Debug activé et clé éphémère sans opt-in ; risque de diagnostics détaillés et cookies sans Secure en cas d'exposition accidentelle. L'aperçu localhost n'est pas une exposition publique. | Debug désactivé par défaut ; clé absente bloquante ; développement avec DJANGO_DEBUG=1 explicite. Sous-processus éprouvant refus, redirection HTTPS, HSTS et paramètres Secure. |
| **S-04 — durcissement des sessions** | Durée héritée de quatorze jours, sans preuve de vol de cookie. | Expiration serveur après 30 minutes sans requête, renouvelée par les requêtes ; cookie non persistant, HttpOnly et SameSite=Lax explicites. Secure obligatoire en production. |

Réponses admin/account : no-store explicite et Referrer-Policy=same-origin. Un essai no-referrer a entraîné un rejet CSRF dans le navigateur ; après correction, connexion et enregistrement ont réussi. DENY et nosniff restent présents.

## Tests spécifiques et TDD

Les **27 cas ajoutés** dans tests/test_security.py couvrent :

- SQL : `' OR 1=1 --`, commentaire après le compte et DROP TABLE dans connexion, recherche Unfold et filtre secteur ; aucun accès indu, élargissement de résultat ou objet détruit. Aucun SQL construit à partir d'entrées visiteur trouvé ; requêtes fixes dans les sauvegardes.
- XSS : script, image/onerror, SVG/onload et sortie d'attribut, titres/corps/textes généraux, rendus publics et admin. La recherche de commande est sondée ; sa recherche dans les modèles est désactivée par défaut.
- POST admin javascript/data refusés sans enregistrer de lien ni altérer le contenu publié ; PNG avec HTML ajouté réencodé en JPEG sans HTML. Les tests existants couvrent aussi schémas des secteurs, SVG, animation, faux fichiers, poids/dimensions excessifs.
- CSRF avec Client(enforce_csrf_checks=True) : POST sans jeton ou avec origine étrangère refusés, aucune publication.
- Reprise setup, rotations, absence de mot de passe en clair dans la session, facteur d'un autre utilisateur, expiration, rejeu après déconnexion, staff vérifié sans permission. Les tests existants couvrent anonyme, mot de passe seul, non-staff, rejeu TOTP, récupération à usage unique et Axes.

Échecs observés avant correction : accès indus S-01/S-02, POST final accepté, debug implicite, durée de quatorze jours. Le test de durée avait d'abord une erreur de harnais car GET ne réémettait pas le cookie ; corrigé pour lire le cookie du client et l'expiration stockée, il a ensuite échoué sur les quatorze jours. Aucun test de comportement affaibli. Les sondes des protections existantes passaient déjà.

## Essais Browser

scripts/security_preview.py crée base, médias et administrateur synthétiques hors dépôt et écoute uniquement 127.0.0.1. Aucun compte réel ou secret de production utilisé. La base éditoriale conserve 303 104 octets et son ancien horodatage ; cela complète l'isolation, sans comparaison par empreinte.

Observé dans le navigateur intégré : anonyme refusé ; mot de passe puis TOTP demandé ; accès direct avant TOTP refusé ; code valide ouvrant treize nouvelles synthétiques. Sonde SQL : zéro résultat, treize objets disponibles. Lien javascript soumis par formulaire : « Saisissez une URL valide ». Remplacement par HTTPS et enregistrement d'un titre SVG/onload : succès, chaîne littérale dans liste/message de succès. Setup déjà configuré : refus visible. Détail français puis anglais : chaînes littérales, aucun img[onerror]/svg[onload] ni dialogue JavaScript. Après expiration forcée des seules sessions jetables, retour à la connexion ; aucune attente réelle de trente minutes. Les POST d'exploitation sont éprouvés par pytest.

Captures sans secret : [SQL](screenshots/security-admin-sqli.jpg), [lien refusé](screenshots/security-admin-url-rejected.jpg), [XSS admin](screenshots/security-admin-xss.jpg), [XSS public](screenshots/security-public-xss.jpg), [expiration](screenshots/security-session-expired.jpg).

## Vérification et reproduction

```powershell
.venv/Scripts/python -m pytest -q
$env:DJANGO_DEBUG = "1"
.venv/Scripts/python manage.py check
.venv/Scripts/python manage.py makemigrations --check --dry-run
.venv/Scripts/python -m pip check
.venv/Scripts/python scripts/smoke_backend.py
```

**92 tests réussis** (65 existants, 27 ajoutés). check sans problème, aucune migration manquante, aucune incompatibilité de dépendances ; smoke HTTP et restauration isolée réussis. check --deploy avec DEBUG=0, clé aléatoire temporaire et hôte synthétique : aucun problème. Windows, Python 3.14.3, Django 5.2.18, Unfold 0.108.0, two-factor-auth 1.18.1, django-otp 1.7.4.

Browser : lancer `.venv/Scripts/python scripts/security_preview.py`. AUDIT_RUNTIME indique le répertoire des identifiants synthétiques réservés à ce serveur ; ne pas copier credentials.json dans Git. Arrêt normal : nettoyage automatique ; arrêt forcé : supprimer uniquement le répertoire exact créé par la commande.

## Limites

Le contrôle automatique a refusé la suppression des trois répertoires temporaires (« blocked by policy », sans motif plus détaillé). Le serveur d'audit est arrêté et son port 8011 fermé. Ces dossiers contiennent uniquement bases, médias et identifiants synthétiques ; leur suppression manuelle reste à effectuer :

- `C:\Users\cedric\AppData\Local\Temp\ventisax-security-gyunqfr2`
- `C:\Users\cedric\AppData\Local\Temp\ventisax-security-1nuxu0eg`
- `C:\Users\cedric\AppData\Local\Temp\ventisax-security-i5vc3eqf`

Pas de TLS/proxy/mappings PythonAnywhere réels, inspection effective des cookies Secure sous TLS, fuzzing exhaustif, déni de service, confirmations d'enrôlement strictement simultanées, revue cryptographique ou recherche exhaustive CVE. HTTPS est simulé par le client Django ; pip check vérifie la compatibilité, pas l'absence de vulnérabilités. Pas de CSP complet ajouté sans validation des scripts Alpine d'Unfold.

Certains navigateurs restaurent leurs cookies à la réouverture : fermeture n'est pas révocation garantie. Déconnexion et expiration sont les frontières éprouvées. Un cookie OTP déjà volé reste utilisable jusqu'à révocation/expiration. Pour une installation ayant déjà servi, invalider ses sessions à la mise à jour et contrôler les appareils légitimes ; les correctifs ne retirent pas rétroactivement un appareil déjà ajouté. Aucun compte existant modifié ici.

Références primaires : [sécurité Django](https://docs.djangoproject.com/en/5.2/topics/security/), [sessions et rotation](https://docs.djangoproject.com/en/5.2/topics/http/sessions/), [vues TOTP](https://django-two-factor-auth.readthedocs.io/en/1.18.1/class-reference.html). S-01/S-02 reposent sur le code installé et les reproductions locales ; aucun avis CVE n'est attribué au composant tiers.
