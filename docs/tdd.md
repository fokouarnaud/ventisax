# Journal TDD

Commande de régression : `.venv/Scripts/python -m pytest`.
Les données des tests sont fabriquées dans la base temporaire de pytest, jamais dans la base publique.
## Cycles observés le 10 octobre 2026

| Contrat | Échec observé avant correction | Suite verte après correction |
| --- | --- | --- |
| Premier test du modèle secteur | `DID NOT RAISE ValidationError` pour publication sans anglais | 1 test |
| Secteur complet, première publication, URL stables | Transition et champs absents ; ajout du schéma puis validation | 3 tests |
| Nouvelles, liens, associations, configuration | Après ajout du schéma : liens incomplets acceptés, numéros invalides acceptés | 13 tests |
| Pages bilingues, détail, contacts, filtres, pagination | Les nouvelles routes répondaient 404 au lieu de 200/302/503 | 27 tests |
| Images et filtre « tous » | Après ajout des champs : taille 2000×1000 conservée, faux fichier accepté, ancien média non nettoyé ; filtre vide en 404 | 36 tests |
| Unfold, TOTP, codes de récupération, verrouillage | Routes absentes, puis redirections incorrectes et mot de passe valide accepté après cinq échecs | 46 tests |
| Sauvegarde/restauration | Commandes absentes ; restauration et refus des fichiers corrompus ensuite exercés | 49 tests |
| Formulaires Unfold et limite par IP | Les formulaires passaient avec le code existant ; rotation de noms d’utilisateur contournait le verrouillage | 52 tests |
| Contacts réservés et autres limites | `mailto:support?subject=bad@example.com` était ambigu, au lieu de l’adresse encodée | 55 tests |
| Connexions SQLite sous Windows | Le parcours HTTP révélait un `WinError 32` au nettoyage ; le test de régression a échoué pour la même raison | 56 tests après fermeture explicite |

Les erreurs initiales d’absence de schéma/routes sont distinguées des échecs d’assertion métier.
Les tests qui passaient dès leur ajout vérifient le comportement déjà couvert ; ils ne sont pas présentés comme des cycles rouges.
Aucun test n’a été ignoré ou affaibli. L’ajout du champ de création a demandé une valeur par défaut pour produire la migration
intermédiaire ; l’échec de migration a été corrigé et la suite relancée. Les avertissements Django de formulaires URL
ont été traités avec `assume_scheme` sur les champs Unfold, sans masquer les avertissements.

## Correspondance backend

| Stories | Preuves |
| --- | --- |
| US-01, US-02, US-03 | `test_public.py` : pages, secteurs, jalons, associations visibles et HTML échappé |
| US-04, US-05 | `test_public.py` : 0/1/10/11 jalons, filtre, URL de traduction, 404 et langue du document |
| US-06, US-07 | Modèles et requêtes : validation, singleton, liens directs et modification réelle dans Unfold |
| US-08, US-09, US-10, US-11 | Modèles et Unfold : brouillons, liens bilingues, actions explicites, URL et dates conservées, protection de suppression |
| US-12 | `test_images.py` : vrai décodage, 2 Mio inclus, refus, réduction, alternatives et nettoyage après commit |
| US-13 | `test_admin.py` : connexion réelle par wizard et TOTP, rejeu refusé, récupération unique, accès sans OTP/non staff et verrouillage |
| US-14 | `test_backup.py` : snapshot SQLite et restauration complète isolée, refus de corruption/écrasement |

Lors de la livraison backend initiale, US-15 nécessitait encore une finition et une vérification visuelle mobile/clavier.
La mise en ligne, le quota distant, l’enrôlement du véritable administrateur et la relecture des contenus authentiques
ne sont pas validés par les données temporaires des tests.

## Templates et assets — 10 octobre 2026

Les tests de `test_presentation.py` ont été ajoutés avant l’implémentation : assets locaux disponibles,
navigation courante et titre traduit, dimensions et alternative de l’image, erreurs 404 traduites et bandeau
réservé à l’aperçu isolé. Le premier lancement a échoué sur les comportements absents ; les templates,
les contextes de vues et les assets ont ensuite permis leur passage. La suite atteignait 62 tests réussis.

L’inspection réelle de la connexion a révélé que le template amont du second facteur prenait priorité et chargeait
du CSS distant. Un nouveau test a reproduit cet échec. Le répertoire de templates du projet a été placé avant
les templates des applications installées ; le test et la suite sont passés : **63 tests réussis**.
Le rendu de connexion a ensuite été revérifié sur ordinateur et à 360 pixels.

Les liens de secteurs associés et du fil d’Ariane étaient visuellement trop petits pour un usage tactile confortable.
Le CSS porte maintenant leur hauteur minimale à 44 pixels. Les ajustements de présentation ont été vérifiés
dans le navigateur ; aucun test reproduisant les classes CSS n’a été ajouté.

La matrice publique compte 36 combinaisons : six types de pages, deux langues et trois largeurs.
Aucun débordement horizontal, image non chargée, langue de document incorrecte ou titre principal manquant
n’a été observé. Le filtre, sa pagination et sa conservation lors d’un changement de langue ont été exercés,
ainsi que le lien d’évitement et la soumission au clavier. Les détails figurent dans `validation-interface.md`.

## Nouvelles-leçons : vidéo YouTube et liens réseaux — 14 octobre 2026

| Contrat | Échec observé avant correction | Suite verte après correction |
| --- | --- | --- |
| Formats YouTube acceptés et ID extrait ; domaines, playlists, ID invalides et `javascript:` refusés ; Instagram/Facebook limités à leurs domaines | `TypeError: Nouvelle() got unexpected keyword arguments: 'video_youtube'` (13 tests, champs absents) | 27 tests du modèle |
| Détail : iframe `youtube-nocookie` construit depuis l'ID seul (paramètres de l'URL d'origine non réinjectés), titre localisé, `loading="lazy"`, `referrerpolicy` ; liens réseaux en nouvel onglet ; mention « Video in French » | Même absence de champs | **132 tests réussis** |

Le test « détail sans vidéo ni réseaux » passait dès son ajout (comportement déjà vrai) ; il protège contre une régression.
Rendu exercé dans l'aperçu isolé (`scripts/preview_site.py`) avec Playwright et Chrome : aucun débordement horizontal
à 320, 360, 768 et 1 280 px en français et en anglais ; lecteur 9:16 de 246×437 px à 320 px, plafonné à 360×640 px.
Non exercé : lecture effective de la vidéo (le navigateur sans interface ne charge pas le lecteur), saisie dans Unfold
derrière le second facteur (la validation est portée par `Nouvelle.clean()`, appelée par le formulaire).

## Acquisition honnête : « Me prévenir », Journal de formation, profils — 15 octobre 2026

| Contrat | Échec observé avant correction | Suite verte après correction |
| --- | --- | --- |
| Profils YouTube/Instagram/Facebook/TikTok de la configuration limités à leur domaine, vides acceptés ; `notify_url` encode le message (`wa.me?text=`) ou bascule sur `mailto:?subject=&body=` | `TypeError: ConfigurationGenerale() got unexpected keyword arguments: 'tiktok_url', 'facebook_url'` ; `notify_url` absent | 29 tests du modèle |
| Bouton « Me prévenir à l'ouverture » / « Notify me at launch » deux fois sur l'accueil et sur Contact, repli e-mail sans WhatsApp ; « Journal de formation » / « Training log » en titre, `<title>` et navigation, URL inchangées ; profils en liens `noopener noreferrer` seulement s'ils sont renseignés | Libellés et bouton absents (5 tests) | **134 tests réussis**, hors 5 préexistants |

Les 5 tests de `test_security.py`/`test_deployment.py` qui échouent le font aussi sur `HEAD` sans ces modifications :
le `.env` local (`DJANGO_DEBUG`, `DJANGO_SECRET_KEY`) est chargé par les réglages et contredit les scénarios
« sans opt-in ». Non corrigé dans cette passe. Rendu exercé dans l'aperçu isolé avec Playwright et Chrome : accueil
et Contact en fr/en à 390 et 1 280 px sans débordement, message WhatsApp décodé conforme, bouton atteint au clavier
(Tab). Non exercé : saisie des profils dans Unfold derrière le second facteur.

## Image d'accueil administrable — 16 octobre 2026

| Contrat | Échec observé avant correction | Suite verte après correction |
| --- | --- | --- |
| Image d'accueil optimisée (JPEG, 1 600 px), alternatives fr/en exigées seulement avec image, fichier invalide refusé sur `image_accueil`, ancienne image supprimée après un remplacement validé puis au retrait | `AttributeError: 'ConfigurationGenerale' object has no attribute 'image_accueil'` | **143 tests réussis**, hors les 5 préexistants liés au `.env` |
| Hero : `<img class="hero-photo">` avec alternative localisée et dimensions ; logo sans image ; champs présents dans Unfold | Même absence de champ | idem |

La validation des bases chargées (`database_versions`) exigeait tout champ `_fr`/`_en` non vide : elle utilise désormais
`ConfigurationGenerale.required_texts()` et vérifie l'image d'accueil (fichier présent, alternatives) comme celles des
nouvelles. Le test d'administration n'envoie plus le champ fichier vide, comme un navigateur. Rendu vérifié dans un aperçu
isolé avec une image neutre : 1 280 px en clair et 390 px en sombre, CLS ≤ 0,03, sans débordement.
Non exercé : envoi réel d'une image dans Unfold derrière le second facteur.
