@AGENTS.md

# Cartographie du dépôt Ventisax (pour Claude Code)

`AGENTS.md`, importé ci-dessus, porte le cadrage, le PRD et l'historique des décisions : il fait foi.
Journal de formation : GOALS et PRD du 22 octobre 2026 (US-16 à US-22, règles RJ-01 à RJ-07) dans la sous-section « journal de formation, partie 2 » de `## GOALS`.
Renvoi vers l'Académie Ventisax (`acadventisax.pythonanywhere.com`) et demande d'accès par WhatsApp/e-mail : GOALS validés et PRD du 22 octobre 2026 (US-23 à US-26, règles RA-01 à RA-07, PRD en attente de validation) dans la sous-section « renvoi vers l'Académie » de `## GOALS` ; backend et gabarits implémentés en TDD, parcours réels non exercés.
Ce fichier décrit seulement **où se trouve quoi**. Relevé le 14 octobre 2026 sur `develop`, mis à jour le 22 octobre 2026.

## Points d'entrée

| Entrée | Rôle |
| --- | --- |
| `manage.py` | Commandes Django (`config.settings`). En local : `DJANGO_DEBUG=1` obligatoire, sinon `DJANGO_SECRET_KEY` est exigée. |
| `config/wsgi.py` | `application` WSGI ; en production PythonAnywhere, réglages `config.production` (proxy HTTPS, debug refusé, statiques avec empreinte `ManifestStaticFilesStorage` : `collectstatic` obligatoire à chaque déploiement). |
| `config/urls.py` | **Routeur principal.** `/` → `hub.views.root` (redirige vers `/fr/`) ; `/<fr\|en>/…` → `hub.views.public(page=…)` pour `home`, `about` (`presentation/`), `contact`, `news` (`nouvelles/`), `sector` (`secteurs/<slug>/`), `detail` (`nouvelles/<slug>/`) ; `/admin/` → `hub.admin.site` ; routes `two_factor`. 404 : `hub.views.not_found`. |

## Flux d'une page publique

`config/urls.py` → `hub/views.py::public()` (filtre `publie=True`, pagination par 10, filtre secteur, affichage `?vue=liste|grille` du journal, URL de la
langue opposée) → `localized(obj, lang)` aplatit les champs `*_fr` / `*_en` et ajoute secteurs publics, liens,
image, `youtube_id`, réseaux → `hub/templates/hub/page.html` inclut `pages/<page>.html`
(`partials/news_list.html`, `partials/breadcrumbs.html`, `partials/profiles.html`) dans `base.html`. Libellés d'interface : `LABELS` dans `views.py` (la rubrique `news` s'affiche « Journal de formation » / « Training log », bouton `notify` « Me prévenir à l'ouverture » et son message pré-rempli).
Statique : `hub/static/hub/site.css`, `site.js` (menu, bandeau, retour en haut, choix du thème sans rechargement), SVG.
Thème : cookie `theme` lu par `hub/context_processors.py::theme` (`data-theme` sur `<html>`), vue `hub.views.theme` (`/theme/<system|light|dark>/?next=`), contrôle `partials/theme_switch.html` en fin de navigation.

## Modèles (`hub/models.py`)

- `ValidatedModel` : `save()` appelle `full_clean()`.
- `Publication` (abstrait) : `uuid`, `publie`, `slug_fr/en` verrouillés après `premiere_publication`, `publish()` / `unpublish()`, complétude bilingue des `translated_fields`.
- `Secteur` : textes fr/en, `etat` (préparation/actif, distinct de la visibilité), `ordre`, `site_url`.
- `Nouvelle` : titre/corps fr/en, `date_jalon`, image optimisée (`hub/images.py::optimize`) + alt fr/en, secteurs (M2M via `NouvelleSecteur`, suppression de secteur protégée), `video_youtube` (`youtube_video_id()`, propriété `youtube_id`), `instagram_url`, `facebook_url`, `compte_rendu_fr/en` (lignes « Rubrique : valeur », rendues par `views.report_rows()` en fiche repliée). Nettoyage des images remplacées après commit.
- `LienNouvelle` : liens externes ordonnés, libellés fr/en exigés à la publication.
- `ConfigurationGenerale` : singleton (identité, présentation, parcours, implantation, e-mail, WhatsApp facultatif, profils facultatifs YouTube/Facebook/TikTok/Instagram validés par `SOCIAL_HOSTS` et `social_host_errors`) ; `notify_url(message, sujet)` construit le lien « Me prévenir » (`wa.me?text=` ou `mailto:` en repli) ; `image_accueil` + `alt_accueil_fr/en` (image du hero, logo sinon), `academie_url` (renvoi vers l'Académie, facultatif), `required_texts()`. Sauvegarde d'image partagée : `save_with_image()` (optimisation, nettoyage différé de l'ancienne image).
- `DatabaseVersion` : métadonnées des versions de base (voir ci-dessous).

## Administration et sécurité

- `hub/admin.py` : `SecureAdminSite` (Unfold + second facteur obligatoire sur toutes les vues), `PublicationAdmin` (actions publier/dépublier, slugs en lecture seule après publication), admins `Secteur`, `Nouvelle` (inlines liens et secteurs), `ConfigurationGenerale`.
- `hub/security.py` : identifiant de verrouillage `axes`, `AccountSecurityMiddleware` (rotation de session, appareil OTP).
- `hub/database_versions.py` + `hub/database_admin.py` + `hub/templates/admin/database_versions.html` : base courante et backup SQLite, verrou d'accès (`DatabaseAccessMiddleware`), validation, permutation, envoi daté par e-mail.
- Réglages : `config/settings.py` (SQLite, `Africa/Douala`, `axes`, OTP e-mail optionnel, HTTPS/HSTS hors debug), `config/test_settings.py` (tests).

## Commandes, scripts, tests

- `hub/management/commands/` : `seed_content` (contenus du brief, `--announce-classes`), `backupventisax`, `restoreventisax`, `journal` (`inventaire <partie>`, `verifier <fichier>`, `comparer <fichier> --site URL`, sans écriture en base).
- `hub/journal.py` : fichiers sources du Journal de formation (`parse_source`, `source_errors`, `modules_sans_entree`, `ecarts_page`, `publier` pour l'aperçu local).
- `scripts/` : `preview_site.py` (aperçu isolé, base temporaire, données fictives ; `--journal <dossier>` publie les fichiers sources réels du journal à la place), `security_preview.py`, `smoke_backend.py`, `check_deployment.py`.
- Tests : `.venv/Scripts/python -m pytest` (`pytest.ini` → `config.test_settings`), 203 tests, dont 16 dans `test_journal.py`, 12 dans `test_theme.py` et 12 dans `test_academy.py` (`config/test_settings.py` neutralise le `.env` local via `DJANGO_ENV_FILE`) ; fabriques dans `tests/factories.py`. Contrôles : `DJANGO_DEBUG=1 .venv/Scripts/python manage.py check` et `makemigrations --check --dry-run`. Journal TDD : `docs/tdd.md`.
- Skill de projet `.claude/skills/ventisax-deploy/` : procédure de déploiement PythonAnywhere (commits, main en avance rapide, console Playwright : pull, migrate, collectstatic, check --deploy, touch WSGI, vérifications).
- Skill de projet `.claude/skills/journal-formation/` : publication et correction des entrées du Journal de formation à partir des références de cours (publication directe dans Unfold de production via Playwright, connexion du porteur).
- Styles : `hub/static/hub/site.css` (Lexend auto-hébergée dans `hub/static/hub/fonts/`, licence OFL).
- Documentation : `README.md` (installation, déploiement PythonAnywhere), `docs/` (exploitation, déploiement, sécurité, validation d'interface, versions de base, `acquisition.md` : capsules, réseaux, WhatsApp Business).

## Hors dépôt et outils associés

- `programme_shorts_pedago/` (non suivi) : scripts et capsule du module 3, visuels et générateurs dans `visuels/src/` ; `reference/cours/<partie>/<module>/` (pages du manuel, sources privées à ne pas publier) et `nouvelles/<partie>/<module>/` (fichier source de chaque entrée du Journal de formation). Médias `*.mp4 *.mp3 *.wav` ignorés.
- `videos/` (ignoré) : photos du manuel et du planning de formation, sources privées à ne pas publier.
- `C:\openshorts` : OpenShorts (Docker) utilisé par les skills `clip-local` (montage, sous-titres karaoké, contrôle de voix) et `voix-off-locale` (Kokoro, Piper).
- `db.sqlite3`, `media/`, `staticfiles/`, `backups/`, `.env` : données locales, jamais versionnées.

## Zones d'ombre connues

- La lecture effective du lecteur YouTube et la saisie Unfold derrière le second facteur n'ont pas été exercées dans un navigateur réel pour les champs vidéo/réseaux.
- La politique de sécurité du contenu (CSP) n'existe pas : l'iframe YouTube fonctionne sans elle ; en ajouter une imposera d'autoriser `youtube-nocookie.com`.
- Déploiement des migrations `0008` à `0012` sur PythonAnywhere : non fait, soumis à accord explicite.
- Académie : `ConfigurationGenerale.academie_url` (migration `0012`, section « Académie » d'Unfold), `whatsapp_text_url()` / `email_text_url()` (réutilisées par `notify_url`), `views.academy_links()` limité à `ACADEMY_PAGES` (journal, détail, Contact), `partials/academy.html` ; vérifié dans l'aperçu Playwright (largeurs, thèmes, clavier), non déployé ; aperçu fictif avec `academie_url` ; l'e-mail et le WhatsApp de contact sont déjà administrables (section « Coordonnées » de `hub/admin.py`). L'Académie se présente encore comme « centre de formation » : correction à la charge du porteur, hors dépôt.
