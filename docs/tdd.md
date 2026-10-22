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

## Compte rendu replié et journal groupé par jour — 16 octobre 2026

| Contrat | Échec observé avant correction | Suite verte après correction |
| --- | --- | --- |
| Compte rendu bilingue exigé à la publication s'il est renseigné ; rendu en `<details class="report">` avec `<dt>`/`<dd>` à partir de lignes « Rubrique : valeur » ; corps en paragraphes séparés ; une seule pastille de date par jour dans le journal | `TypeError: Nouvelle() got unexpected keyword arguments: 'compte_rendu_fr'` et pastilles répétées (4 tests) | **142 tests réussis**, hors les 5 préexistants liés au `.env` |

Rendu vérifié sur la base locale : journal à 1 280 px (clair) et 390 px (sombre), 7 entrées et 4 pastilles visibles,
fiche dépliée de 4 rubriques, sans débordement. Le marqueur natif du `<details>` disparaissant avec `display: flex`,
un chevron Tabler signale l'ouverture.

## Journal en liste ou en grille, groupé par jour — 16 octobre 2026

| Contrat | Échec observé avant correction | Suite verte après correction |
| --- | --- | --- |
| Une section par jour (date une seule fois) ; sélecteur Liste/Grille avec `aria-current` ; grille avec extraits tronqués ; vue conservée par le filtre (champ caché), la pagination et le changement de langue ; valeur inconnue sans erreur | Classes `journal`, `day-group` et sélecteur absents (2 tests) | **143 tests réussis**, hors les 5 préexistants liés au `.env` |

Deux assertions de test écrites avant le code supposaient un balisage différent (libellé juste après `aria-current`,
comptage des mots sur toute la page) ; elles ont été réécrites sur la structure réelle, sans réduire ce qu'elles vérifient.
Rendu vérifié sur la base locale : liste et grille à 1 280 px (clair) et 390 px (sombre), accueil compris, sans
débordement ; sélecteur sur une ligne ; passage à la grille au clavier (Tab puis Entrée).

## Journal de formation : fichiers sources et commande `journal` — 22 octobre 2026

Demande explicite : appliquer le TDD au PRD « journal de formation, partie 2 ». Le PRD n'ajoute aucune table ;
les cycles portent sur ses entités hors base (`FichierSource`, `ModuleDeCours`) et leur passage vers `Nouvelle`.
Fichiers : `hub/journal.py`, `hub/management/commands/journal.py`, `tests/test_journal.py`.

| Contrat (story) | Échec observé avant code | Suite verte après code |
| --- | --- | --- |
| Lecture d'un fichier source en champs de `Nouvelle` (US-20) | `ImportError: cannot import name 'journal'` | 1 test |
| Source → nouvelle publiée avec son secteur ; compte rendu anglais manquant refusé par le modèle, rien de publié (US-18) | `AttributeError: publier` (2 tests) | 3 tests |
| Règles RJ-03/RJ-04 : préfixes de titres et slugs, trois paragraphes au plus, quatre rubriques par langue, noms interdits (US-17) | `AttributeError: source_errors` (2 tests) | 5 tests |
| Republication = correction sans doublon ni changement d'horodatage ; slug publié modifié refusé ; secteur inconnu refusé (US-18, US-22) | Contrainte d'unicité violée ; secteur ignoré sans erreur (2 tests) | 8 tests |
| Inventaire des modules de référence sans fichier source, tri numérique (US-21) | `AttributeError: modules_sans_entree` | 9 tests |
| Page publique fr/en comparée au fichier source (US-19, US-20) | `AttributeError: ecarts_page` (2 tests) | 11 tests |
| `manage.py journal inventaire|verifier|comparer` (US-19, US-21) | `Unknown command: 'journal'` (3 tests) | 14 tests ; suite complète **159 tests réussis**, hors les 5 préexistants liés au `.env` |

Ajustements de tests, sans réduire ce qu'ils vérifient : le test du compte rendu manquant ne créait pas le secteur et
ne passait que parce qu'un secteur inconnu était ignoré ; le test de page a reçu la configuration générale requise
par les vues (503 sinon). Le test du slug modifié passait d'abord par la contrainte d'unicité, ensuite par le
verrou des slugs publiés. `check` sans erreur, `makemigrations --check` sans migration. Inventaire réel :
`02_partie2` → modules 1 à 8 sans entrée ; `01_partie1` → aucun. Non exercé : `comparer` contre la production.

Cycle complémentaire : `journal verifier` sur le modèle vierge du skill levait `ValueError` (date `JJ/MM/AAAA`).
Test d'abord en échec pour cette raison, puis message `date_jalon : « JJ/MM/AAAA » attendue au format JJ/MM/AAAA.` ;
15 tests dans `test_journal.py`, suite complète à **160 tests réussis**, hors les 5 préexistants liés au `.env`.

## Choix du thème clair, sombre ou système — 22 octobre 2026

| Contrat | Échec observé avant code | Suite verte après code |
| --- | --- | --- |
| Sans préférence : pas de `data-theme`, `color-scheme` « light dark », « système » courant ; libellés fr/en ; lien de retour vers la page courante ; préférence `light`/`dark` rendue dès le HTML sur pages, journal et 404 ; valeur inconnue ignorée ; vue `theme` : cookie (Lax, chemin `/`, un an, lisible par le script), suppression pour « système », retour hors du site refusé, choix inconnu 404 | Contrôle et route absents (11 tests sur 12 ; le 404 passait faute de route) | `tests/test_theme.py` : 12 tests ; suite complète **172 tests réussis**, hors les 5 préexistants liés au `.env` |

`check` sans erreur, `makemigrations --check` sans migration. Comportement réel et rendu vérifiés dans
`docs/validation-interface.md`.

## Renvoi vers l'Académie et demande d'accès — 22 octobre 2026

PRD « Renvoi vers l'Académie Ventisax » (US-23 à US-26, RA-01 à RA-07). Fichiers : `hub/models.py`
(`academie_url`, migration `0012`, `whatsapp_text_url`, `email_text_url`), `hub/admin.py` (section « Académie »),
`hub/views.py` (`LABELS`, `academy_links`, `ACADEMY_PAGES`), `partials/academy.html`, `tests/test_academy.py`.

| Contrat (story) | Échec observé avant code | Suite verte après code |
| --- | --- | --- |
| Adresse facultative, http/https seulement (`javascript:`, `data:`, `ftp:` refusés) (US-25, RA-04) | `AttributeError: … no attribute 'academie_url'` | 1 test |
| Liens de demande d'accès WhatsApp et e-mail encodés ; sans WhatsApp, lien WhatsApp vide (US-24) ; `notify_url` refactorisé sur ces méthodes, ses tests existants restés verts | `AttributeError: whatsapp_text_url` | 2 tests ; `test_models.py` vert |
| Champ modifiable dans Unfold ; adresse dangereuse refusée sans perte ; adresse, e-mail et WhatsApp modifiés ensemble (US-25) | `'name="academie_url"'` absent du formulaire | 3 tests |
| Sans adresse : aucun bloc ; avec adresse : bloc fr/en sur journal, détail, Contact, absent d'accueil, présentation, secteur ; lien exact, nouvel onglet, `rel` ; liens pré-remplis ; ni « centre de formation », ni « gratuit »/« free » ; sans WhatsApp, seule la demande par e-mail, sur les coordonnées en vigueur (US-23, US-24, RA-01 à RA-03) | `data-academy` absent (3 tests ; le test « sans adresse » passait, ce qui est attendu) | 7 tests |

Ajustement de test, sans réduire ce qu'il vérifie : le test « sans WhatsApp » passait d'abord par le `mailto:` de
« Me prévenir » ; il vérifie désormais le libellé et l'objet propres à la demande d'accès, puis a échoué pour la bonne
raison avant le code. Le style (`academy-panel`, `visually-hidden`) relève de la vérification par rendu.

### Critères d'acceptation restants — 22 octobre 2026

Le backend existait déjà : un test écrit après coup passe d'emblée et ne prouve rien. Chaque nouveau test a donc été
mis en échec par **mutation**, c'est-à-dire en cassant temporairement le comportement à partir d'une copie hors
dépôt, puis le code a été restauré à l'identique (`cmp`).

| Contrat (story) | Mutation, échec observé | Test |
| --- | --- | --- |
| Migration `0012` : configuration existante (e-mail, WhatsApp, textes) conservée, `academie_url` vide (modèle de données, DoD) | Migration retirée : nœud `0012` introuvable | `test_database_versions.py::test_migration_academie_preserve_configuration_existante` |
| Base importée dont l'adresse d'Académie vaut `javascript:` refusée sans toucher aux emplacements (RA-04, RM-10) | `academie_url` exclu de `clean_fields` dans `validate()` : import accepté | paramètre ajouté à `test_import_incompatible_preserve_slots` |
| Ouverture externe annoncée (« (nouvel onglet) » / « (new tab) » dans le lien) ; un seul bloc par page (US-23) | Annonce retirée du gabarit : 2 échecs fr/en | `test_ouverture_externe_annoncee_et_bloc_unique` |
| E-mail et WhatsApp modifiés : Contact, « Me prévenir » et demande d'accès changent ensemble (US-25, RA-02) | Numéro figé dans `notify_url` | `test_coordonnees_modifiees_reportees_sur_contact_prevenir_et_acces` |
| Message pré-rempli : nom et motif demandés, sans mot de passe, fr/en (US-24) | Motif retiré du message français | `test_message_de_demande_demande_nom_et_motif_sans_secret` |

Constat : retirer le validateur `HTTP_URL` d'`academie_url` ne suffit pas à faire passer `javascript:`, refusé aussi
par le `URLValidator` par défaut ; seul `ftp:` dépend de `HTTP_URL` (test du modèle existant). Suite complète :
**191 tests, 186 réussis**, hors les 5 préexistants liés au `.env` ; `check` et `makemigrations --check` sans constat.
Migration `0012` appliquée sur une copie de `db.sqlite3` (sauvegarde SQLite cohérente, hors dépôt) : configuration,
2 secteurs, 7 nouvelles et 6 associations identiques avant et après ; `academie_url` vide.

## Revue des autres stories backend — 22 octobre 2026

Les contrats publics et de publication (US-04, US-05, US-10, US-11) ont été sondés par un test jetable, sans écart :
page `0`, `-1`, `abc`, `1.0` ou au-delà de la dernière, secteur inconnu ou dépublié → 404 ; filtre et affichage
conservés au changement de langue ; détail visible après dépublication de son secteur ; première publication
inchangée après dépublier/republier ; traduction faite d'espaces refusée. Trois défauts réels, cycle rouge puis vert :

| Contrat (story) | Échec observé avant code | Correction |
| --- | --- | --- |
| Base importée ou restaurée : profil social de la configuration hors domaine, lien Facebook de nouvelle hors domaine, playlist YouTube, compte rendu publié dans une seule langue refusés (US-14, US-07, RM-10, RJ-04, décision du 14 octobre) | 4 paramètres de `test_import_incompatible_preserve_slots` : import accepté (302 au lieu de 200) | `validate()` n'appliquait que `clean_fields()` ; il réutilise `Nouvelle.link_errors()` (extrait de `clean()`), `social_host_errors` et `missing_text` |
| Isolation de la suite : le `.env` de développement réglait les tests et leurs sous-processus (`DJANGO_DEBUG`, `DJANGO_EMAIL_OTP`) | Les 5 échecs dits préexistants de `test_security.py`/`test_deployment.py` | `config/test_settings.py` pointe `DJANGO_ENV_FILE` vers un fichier absent avant d'importer les réglages |
| Fichier source du journal sans date du cours, ou daté dans le futur (RJ-01, hors-scope « modules non suivis ») | `test_date_du_cours_obligatoire_et_jamais_future` : `TypeError` (paramètre `today` absent) | `source_errors(..., today=None)` signale la date absente ou future |

Suite complète : **196 tests réussis, aucun échec** ; `check` et `makemigrations --check` sans constat. Les quatre
fichiers sources de la partie 2 restent conformes à `journal verifier`. Les six de la partie 1, antérieurs au
format (pas de slugs), échouaient déjà avec le code commité ; non modifiés.

### Critères restants des stories V1 — 22 octobre 2026

Comportements déjà présents : chaque nouveau test a passé d'emblée, puis a échoué sous une mutation ciblée (code
restauré à l'identique, `cmp`).

| Story | Test | Mutation, échec observé |
| --- | --- | --- |
| US-01 | `test_seed.py::test_initialisation_presente_un_projet_et_non_une_sarl_operationnelle` | Identité initiale « Ventisax SARL » |
| US-02 | `test_public.py::test_secteurs_dans_l_ordre_administre_avec_etat_traduit` | Tri `-ordre` ; état brut non traduit |
| US-02 | `test_public.py::test_lien_vers_le_site_dedie_seulement_s_il_est_renseigne` | Lien rendu sans condition |
| US-03 | `test_public.py::test_detail_date_du_jalon_et_non_de_publication` | Détail daté de la première publication |
| US-08 | `test_models.py::test_etat_du_secteur_independant_de_sa_visibilite` | `save()` publie un secteur « actif » |
| US-11 | `test_public.py::test_republication_d_un_secteur_retablit_ses_associations_visibles` | `unpublish()` d'un secteur supprime ses associations |

## Traçabilité des stories backend — 22 octobre 2026

| Story | Tests | Preuve de l'échec |
| --- | --- | --- |
| US-01 Comprendre Ventisax | `test_public::test_entree_francaise_et_pages_bilingues`, `test_seed::…sarl_operationnelle` | V1 ; mutation |
| US-02 Consulter un secteur | `test_public::test_details_traduits…`, `…ordre_administre…`, `…site_dedie…` | V1 ; mutations |
| US-03 Lire un jalon | `test_public::test_details_traduits…`, `…date_du_jalon…`, `test_detail_sans_video_ni_reseaux` | V1 ; mutation |
| US-04 Filtrer, paginer | `test_public::test_pagination_filtre_et_bascule_langue[0,1,10,11]`, `test_filtre_et_page_invalides_404`, `test_pagination_conserve_la_vue_grille` | V1 |
| US-05 Changer de langue | `test_public::test_entree_francaise…` (`<html lang>`), `test_pagination_filtre_et_bascule_langue`, `test_models::test_secteur_description_anglaise_espaces…` | V1 |
| US-06 Contacter | `test_public::test_contacts_administrables_et_absence_formulaire`, `test_models::test_email_valide…mailto` | V1 |
| US-07 Présentation, coordonnées | `test_models::test_configuration_unique…`, `test_coordonnees_invalides_refusees`, `test_admin::test_configuration_modifiee_dans_unfold_invalidite_preserve`, import (`test_database_versions`) | V1 ; rouge réel (import) |
| US-08 Gérer les secteurs | `test_models::test_secteur_brouillon_complet…`, `…etat_du_secteur_independant…`, `test_admin::test_creation_et_modification_reelles_dans_unfold` | V1 ; mutation |
| US-09 Préparer une nouvelle | `test_models::test_nouvelle_brouillon_liens_traduits…`, `test_jalon_absent_refuse_et_brouillon_incomplet_autorise`, `test_associations_uniques…` | V1 |
| US-10 Publier | `test_models::test_secteur_publication_refuse…`, `test_collision_slugs_et_tri_jalons`, `test_compte_rendu_bilingue…` | V1 |
| US-11 Retirer | `test_public::test_retrait_secteur_conserve_nouvelle_comme_groupe`, `…republication…`, `test_models::test_associations_uniques_et_suppression_secteur_protegee` | V1 ; mutation |
| US-12 Image légère | `test_images.py` (8 tests) | V1 |
| US-13 Sécuriser l'administration | `test_admin.py`, `test_security.py` | V1 (audit du 10 octobre) |
| US-14 Sauvegarder, restaurer | `test_backup.py`, `test_database_versions.py` | V1 ; rouge réel (4 cas d'import) |
| US-15 Mobile, clavier | `test_presentation.py`, `test_theme.py` (balisage) ; parcours réels dans `docs/validation-interface.md` | V1 |
| US-16 à US-20 Entrées de la partie 2 | Contenu de production : `journal comparer` sur le site (8 pages, aucun écart) ; outillage `test_journal.py` | Rouge réel (14 tests du 22 octobre) |
| US-21 Inventaire, faits | `test_journal::test_inventaire…`, `…date_du_cours_obligatoire_et_jamais_future` | Rouge réel |
| US-22 Corriger | `test_journal::test_republier_une_source_corrige…`, `test_correction_qui_change_un_slug_publie_est_refusee` | Rouge réel |
| US-23 à US-25 Académie | `test_academy.py` (12), migration `0012`, import `javascript:` | Rouge réel (7) ; mutations (5) |
| US-26 Bloc mobile, clavier, thèmes | Rendu et accessibilité, non backend : à vérifier dans le navigateur (DoD ouverte) | — |

« V1 » renvoie aux cycles rouge-vert consignés plus haut dans ce journal. Suite complète : **202 tests réussis, aucun
échec** ; `check` et `makemigrations --check` sans constat.
