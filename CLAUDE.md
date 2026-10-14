@AGENTS.md

# Cartographie du dépôt Ventisax (pour Claude Code)

`AGENTS.md`, importé ci-dessus, porte le cadrage, le PRD et l'historique des décisions : il fait foi.
Ce fichier décrit seulement **où se trouve quoi**. Relevé le 14 octobre 2026 sur `develop`.

## Points d'entrée

| Entrée | Rôle |
| --- | --- |
| `manage.py` | Commandes Django (`config.settings`). En local : `DJANGO_DEBUG=1` obligatoire, sinon `DJANGO_SECRET_KEY` est exigée. |
| `config/wsgi.py` | `application` WSGI ; en production PythonAnywhere, réglages `config.production` (proxy HTTPS, debug refusé). |
| `config/urls.py` | **Routeur principal.** `/` → `hub.views.root` (redirige vers `/fr/`) ; `/<fr\|en>/…` → `hub.views.public(page=…)` pour `home`, `about` (`presentation/`), `contact`, `news` (`nouvelles/`), `sector` (`secteurs/<slug>/`), `detail` (`nouvelles/<slug>/`) ; `/admin/` → `hub.admin.site` ; routes `two_factor`. 404 : `hub.views.not_found`. |

## Flux d'une page publique

`config/urls.py` → `hub/views.py::public()` (filtre `publie=True`, pagination par 10, filtre secteur, URL de la
langue opposée) → `localized(obj, lang)` aplatit les champs `*_fr` / `*_en` et ajoute secteurs publics, liens,
image, `youtube_id`, réseaux → `hub/templates/hub/page.html` inclut `pages/<page>.html`
(`partials/news_list.html`, `partials/breadcrumbs.html`) dans `base.html`. Libellés d'interface : `LABELS` dans `views.py`.
Statique : `hub/static/hub/site.css`, `site.js` (menu, bandeau, retour en haut), SVG.

## Modèles (`hub/models.py`)

- `ValidatedModel` : `save()` appelle `full_clean()`.
- `Publication` (abstrait) : `uuid`, `publie`, `slug_fr/en` verrouillés après `premiere_publication`, `publish()` / `unpublish()`, complétude bilingue des `translated_fields`.
- `Secteur` : textes fr/en, `etat` (préparation/actif, distinct de la visibilité), `ordre`, `site_url`.
- `Nouvelle` : titre/corps fr/en, `date_jalon`, image optimisée (`hub/images.py::optimize`) + alt fr/en, secteurs (M2M via `NouvelleSecteur`, suppression de secteur protégée), `video_youtube` (`youtube_video_id()`, propriété `youtube_id`), `instagram_url`, `facebook_url`. Nettoyage des images remplacées après commit.
- `LienNouvelle` : liens externes ordonnés, libellés fr/en exigés à la publication.
- `ConfigurationGenerale` : singleton (identité, présentation, parcours, implantation, e-mail, WhatsApp facultatif).
- `DatabaseVersion` : métadonnées des versions de base (voir ci-dessous).

## Administration et sécurité

- `hub/admin.py` : `SecureAdminSite` (Unfold + second facteur obligatoire sur toutes les vues), `PublicationAdmin` (actions publier/dépublier, slugs en lecture seule après publication), admins `Secteur`, `Nouvelle` (inlines liens et secteurs), `ConfigurationGenerale`.
- `hub/security.py` : identifiant de verrouillage `axes`, `AccountSecurityMiddleware` (rotation de session, appareil OTP).
- `hub/database_versions.py` + `hub/database_admin.py` + `hub/templates/admin/database_versions.html` : base courante et backup SQLite, verrou d'accès (`DatabaseAccessMiddleware`), validation, permutation, envoi daté par e-mail.
- Réglages : `config/settings.py` (SQLite, `Africa/Douala`, `axes`, OTP e-mail optionnel, HTTPS/HSTS hors debug), `config/test_settings.py` (tests).

## Commandes, scripts, tests

- `hub/management/commands/` : `seed_content` (contenus du brief, `--announce-classes`), `backupventisax`, `restoreventisax`.
- `scripts/` : `preview_site.py` (aperçu isolé, base temporaire, données fictives), `security_preview.py`, `smoke_backend.py`, `check_deployment.py`.
- Tests : `.venv/Scripts/python -m pytest` (`pytest.ini` → `config.test_settings`), 132 tests ; fabriques dans `tests/factories.py`. Contrôles : `DJANGO_DEBUG=1 .venv/Scripts/python manage.py check` et `makemigrations --check --dry-run`. Journal TDD : `docs/tdd.md`.
- Styles : `hub/static/hub/site.css` (Lexend auto-hébergée dans `hub/static/hub/fonts/`, licence OFL).
- Documentation : `README.md` (installation, déploiement PythonAnywhere), `docs/` (exploitation, déploiement, sécurité, validation d'interface, versions de base).

## Hors dépôt et outils associés

- `programme_shorts_pedago/` (non suivi) : scripts et capsule du module 3, visuels et générateurs dans `visuels/src/`. Médias `*.mp4 *.mp3 *.wav` ignorés.
- `videos/` (ignoré) : photos du manuel et du planning de formation, sources privées à ne pas publier.
- `C:\openshorts` : OpenShorts (Docker) utilisé par les skills `clip-local` (montage, sous-titres karaoké, contrôle de voix) et `voix-off-locale` (Kokoro, Piper).
- `db.sqlite3`, `media/`, `staticfiles/`, `backups/`, `.env` : données locales, jamais versionnées.

## Zones d'ombre connues

- La lecture effective du lecteur YouTube et la saisie Unfold derrière le second facteur n'ont pas été exercées dans un navigateur réel pour les champs vidéo/réseaux.
- La politique de sécurité du contenu (CSP) n'existe pas : l'iframe YouTube fonctionne sans elle ; en ajouter une imposera d'autoriser `youtube-nocookie.com`.
- Déploiement des migrations `0008` sur PythonAnywhere : non fait, soumis à accord explicite.
