# Validation de l’interface — 10 octobre 2026

Les templates Django des six pages publiques, des états indisponible/introuvable et du parcours de connexion
utilisent les assets locaux. Le bleu profond, le fond clair et l’accent turquoise suivent le PRD.
Le décor de l’accueil est un SVG de présentation ; il ne représente aucune réalisation du projet.

## Environnement et preuves

La vérification utilise le Browser Plugin, dans le navigateur intégré, avec un serveur Django sur l’adresse
de boucle locale. `scripts/preview_site.py` crée une base SQLite et des médias temporaires. Un bandeau précise
que tous les contenus de cet aperçu sont fictifs. La base éditoriale du projet reste vide.

| Pages | Langues | Largeurs | Résultat observé |
| --- | --- | --- | --- |
| Accueil, présentation, secteur, liste des nouvelles, détail et contact | Français et anglais | 360, 768 et 1 280 px | 36 combinaisons ; aucun débordement horizontal ; un titre principal ; langue correcte ; images chargées |
| Connexion | Français | 360 et 1 280 px | Formulaire lisible, labels présents, assets locaux ; aucun débordement |
| Secteur sans nouvelle, filtre sans résultat, détail sans image | Français | Mobile ou ordinateur | Messages explicites ; lecture sans élément factice ni espace d’image vide |
| Erreur 404 et absence de configuration | Français et anglais | Mobile ou ordinateur | Navigation de retour ou de langue disponible ; mise en page cohérente |

La matrice mesurée se trouve dans `screenshots/layout-matrix.json`. Les captures `home-360.jpg`,
`home-768.jpg`, `home-1280.jpg` et leurs équivalents pour les cinq autres pages permettent de revoir les layouts.
`home-preview.jpg` montre le haut de l’accueil ; `login-mobile.jpg` et `login-desktop.jpg` montrent la connexion.
Les captures sont des preuves de démonstration, pas des contenus à publier.

## Interactions exercées

- Sélection du secteur climatisation/froid : dix nouvelles sur la première page et deux sur la suivante.
- Pagination conservant le filtre ; changement vers l’anglais conservant le secteur et revenant à la première page.
- Tabulation vers le lien d’évitement et activation par Entrée : focus transféré au contenu principal.
- Sélection du filtre au clavier, focus visible sur le bouton, soumission par Entrée et pagination au clavier.
- Lecture du détail illustré en anglais, avec alternative traduite et dimensions réservées ; lecture d’un détail sans image.

## Corrections issues de l’observation

Les liens du fil d’Ariane et les étiquettes de secteurs ont été agrandis à au moins 44 pixels de hauteur.
Le pied de page reste en bas des pages courtes. Le formulaire de connexion adopte une présentation verticale
sur petit écran. Une priorité incorrecte de résolution des templates chargeait l’interface amont du second facteur :
le dossier de templates du projet est désormais prioritaire et un test couvre l’absence d’assets distants.

## Vérifications reproductibles

```powershell
.venv/Scripts/python -m pytest -q
.venv/Scripts/python manage.py check
.venv/Scripts/python manage.py makemigrations --check --dry-run
.venv/Scripts/python manage.py collectstatic --noinput
.venv/Scripts/python scripts/smoke_backend.py
```

`collectstatic` trouve les trois nouveaux assets du hub. Les avertissements de doublons des scripts Django admin
correspondent aux remplacements fournis par Unfold ; ils ne concernent pas les assets du hub.

Les largeurs mobiles sont simulées dans le navigateur de bureau. Un appareil physique, les technologies
d’assistance, un audit exhaustif de contraste/accessibilité et l’ouverture des véritables coordonnées de contact
n’ont pas été vérifiés. La mise en ligne et la validation des contenus réels restent des étapes distinctes.

## Passe de précision visuelle — 10 octobre 2026

L'application a été exécutée dans le Browser Plugin intégré avec `scripts/preview_site.py --port 8002`.
L'en-tête mobile présentait auparavant une ligne de langue pleine largeur en français à 360 px,
alors que la version anglaise gardait les cinq liens sur une ligne. Le sélecteur est désormais séparé
de la navigation : identité et langue en première ligne jusqu'à 960 px, navigation en dessous,
puis deux colonnes jusqu'à 700 px. Les cibles gardent 44 px de hauteur avec 8 px entre les liens mobiles.
Les titres des nouvelles gagnent un interligne de 1,4 et une taille de 1,125 rem ; les descriptions
de secteurs utilisent 1 rem sur mobile. Jusqu'à 380 px, marges de 16 px et cartes remplies à 20 px.
La palette, les polices système et le contenu métier restent ceux du PRD. Ces décisions sont consignées dans AGENTS.md.

`screenshots/refinement-matrix.json` contient 48 mesures : six pages, français/anglais,
320/360/768/1 280 px. Aucun débordement horizontal mesuré, un h1 par page, langue correcte
et liens d'en-tête d'au moins 44 px. Une première mesure de l'image à 320 px a précédé son
chargement ; le contrôle visuel suivant confirme `complete=true` et `naturalWidth=900`.
Captures : `refinement-home-360.jpg`, `refinement-contact-320.jpg`, `refinement-home-desktop.jpg`.

Au clavier, Entrée sur le lien d'évitement transfère le focus à `content` ; le sélecteur ouvre
la traduction du même détail. Le filtre est manipulé avec la flèche puis Tab ; le bouton reçoit
un contour visible. La pagination du secteur climatisation donne deux nouvelles en seconde page,
puis la bascule en français conserve le secteur et revient aux dix éléments de la première page.
Le lien Contact ouvre la page correspondante. Aucun envoi vers les coordonnées fictives n'est effectué.

Vérifications observées : `.venv/Scripts/python -m pytest -q` → 63 tests réussis ;
`.venv/Scripts/python manage.py check` → aucune erreur ;
`.venv/Scripts/python manage.py makemigrations --check --dry-run` → aucune modification détectée.
Il s'agit d'une passe de présentation, validée par rendu réel et tests existants, sans nouveau cycle TDD métier.
Les limites concernant téléphone physique, technologies d'assistance et audit exhaustif restent applicables.

## Retours Browser : quatre contrôles demandés

- Menu à trois barres, replié jusqu'à 960 px, ouvert par Entrée/clic et fermé par Échap ; le focus revient au bouton. À partir de 961 px, navigation visible et bouton masqué.
- Bandeau refermable au clavier ; fermeture conservée lors de la navigation vers Contact dans l'onglet. Mention de démonstration conservée dans le pied de page.
- Lien de traduction explicite, avec langue actuelle et destination ; changement anglais/français depuis Contact conservant cette page.
- Retour en haut absent avant défilement, visible après 500 px ; Ctrl+Fin sur Contact le rend visible. Entrée ramène à `scrollY=0` et transfère le focus à `page-top`.

Le test `test_controles_publics_accessibles_et_script_local` échoue d'abord dans les deux langues
sur l'absence de contrôle de menu, puis passe après implémentation. Le parseur HTML représente
les attributs booléens présents par `None` : le test a été corrigé pour vérifier leur présence.
La suite `.venv/Scripts/python -m pytest -q` donne **65 passed** ; `manage.py check`
ne signale aucune erreur, `makemigrations --check --dry-run` aucune modification.

Le navigateur intégré utilise l'aperçu isolé sur `http://127.0.0.1:8003/` pour charger les nouveaux assets.
`screenshots/controls-matrix.json` mesure 14 combinaisons des deux langues à
320/360/495/768/960/961/1 280 px : aucun débordement, état du menu conforme au seuil.
`controls-mobile.jpg` montre l'en-tête compact et `controls-back-to-top.jpg` le bouton flottant.

Sans JavaScript, la navigation est laissée visible par le HTML/CSS. Le stockage indisponible et
la réduction des mouvements sont traités dans le script. Ces trois configurations, les lecteurs
d'écran et un téléphone physique n'ont pas été exercés ; elles ne sont pas déclarées validées ici.

## Refonte visuelle (typinclub) — 14 octobre 2026

Référence relevée avec Playwright sur `https://typinclub.pythonanywhere.com/` (Lexend, fond `#f6f8f7`, accent vert,
pilules, cartes arrondies, bandeau sombre). Transposition sur la palette Ventisax, sans changer gabarits structurels,
URL ni scripts (seules deux étiquettes d'accueil retirées).

| Contrôle | Résultat |
| --- | --- |
| Six pages publiques (accueil, nouvelles, détail, présentation, contact, secteur) à 1 280 et 390 px | Aucun débordement horizontal |
| Police | Lexend locale chargée (`document.fonts`), aucun CSS distant (test de présentation) |
| Menu mobile au clavier | Entrée ouvre (`aria-expanded=true`), Échap ferme et rend le focus au bouton |
| Passage en format ordinateur | Navigation visible, bouton de menu masqué |
| Suite automatisée | 132 tests réussis |

Non couvert : téléphone physique, lecteur d'écran, contraste mesuré par outil (couleurs de texte reprises de la palette
validée ; boutons blanc sur `#0b2d46` et `#0d665e` sur fonds clairs).

## Audit skill taste (`design-taste-frontend`) — 15 octobre 2026

Lecture : refonte-préservation d'un hub local bilingue, ton sobre et technique, confiance d'abord ;
esthétique inspirée de typinclub (Lexend, bleu profond `#0b2d46`, turquoise), CSS natif sans système de
design officiel (règle d'honnêteté : aucun paquet imité). Réglages : DESIGN_VARIANCE 5, MOTION_INTENSITY 2,
VISUAL_DENSITY 4 (préservation de l'existant). Mesures : Playwright + Chrome sur la base locale, pages
publiques fr/en (24 rendus) à 1 280 et 390 px.

| Point de la section 14 | Statut | Preuve ou justification |
| --- | --- | --- |
| Lecture, réglages, système, mode refonte | Conforme | Ci-dessus ; audit de l'existant dans les sections précédentes de ce document |
| Zéro tiret cadratin visible | Conforme | 0 sur toutes les pages ; état vide sans `—` ; accroche recommandée sans tiret |
| Thème unique | Conforme | Thème clair ; le bandeau sombre d'appel est un composant teinté, pas une section inversée |
| Accent, formes, contraste des boutons | Conforme | Turquoise seul accent (sombre en clair, vif en sombre) ; aucun blanc ni noir purs ; pilules interactives, cartes 24 px, surfaces 20 px, champs 12 px ; tous les boutons ≥ 4,5:1 |
| Libellés d'appel sur une ligne, pas de doublon d'intention | Conforme | « Me prévenir à l'ouverture » identique partout ; contact et WhatsApp sont des intentions distinctes |
| Contraste des formulaires | Conforme | Bordures de champ portées à 3,47:1 (clair) et 3,46:1 (sombre), contre 2,01 et 2,64 auparavant (WCAG 1.4.11) ; textes et libellés AA |
| Hero : titre ≤ 2 lignes, sous-texte ≤ 20 mots, ≤ 4 éléments, appel visible | Conforme | 2 lignes, 15-16 mots, 4 éléments, bouton à 491 px sur 800 |
| Étiquettes en capitales | Conforme | 1 par page au plus (« Nos domaines » retirée) |
| Numérotation décorative, points décoratifs | Conforme | « 01 / 02 » des cartes et point d'implantation retirés ; le point du statut « En préparation » porte un état réel |
| Icônes d'une bibliothèque, pas de SVG fait main | Conforme | Tabler Icons v3 (MIT) via `partials/icon.html` ; flèches typographiques remplacées |
| Illustration décorative faite main, grille décorative | Corrigé en partie | Grille et nœuds retirés ; reste le logo seul (marque géométrique simple, admise) |
| Images réelles | **Ouvert : photo à charger par le porteur** | Champ « Image d'accueil » dans Unfold (Configuration générale) : image optimisée, alternatives fr/en obligatoires, ancienne image supprimée au remplacement ; le hero l'affiche (4:3, sans décalage) et revient au logo sans image. Deux images écartées le 16/10 : l'une générée, l'autre issue d'un document imprimé montrant des personnes dont l'accord n'est pas confirmé |
| Navigation sur une ligne, ≤ 80 px | Conforme | 73 px ; une ligne à 1 280 px |
| Core Web Vitals | Conforme en local | LCP ≤ 1,2 s, CLS ≤ 0,03 (menu mobile replié en CSS dès le premier rendu, rouvert par `<noscript>` sans JavaScript) |
| Mouvement réduit, retour tactile | Conforme | `prefers-reduced-motion` coupe les transitions ; `:active` décale le bouton de 1 px |
| États vide, erreur | Conforme | États vides du journal et des secteurs, page 404, page 503 sans configuration |
| Mode sombre | Conforme | Ajouté sur décision du porteur (16/10) : `prefers-color-scheme`, jetons sémantiques dans `:root`, `<meta name="color-scheme">` ; 24 rendus sans infraction et aucun texte sous AA dans les deux modes, connexion et 404 comprises |
| React, Tailwind, Motion, `min-h-[100dvh]`, `useEffect` | Sans objet | Cadrage Q32 : templates Django, CSS natif, JavaScript minimal ; aucune animation à orchestrer |
| Bento, logos, citations, marquee, sticky-stack, listes longues, tableaux | Sans objet | Absents du site |

Image d'accueil, 16/10 : une image générée montrant l'enseigne et les locaux d'un centre de formation a été écartée sur décision du porteur (contenu fictif, locaux d'un tiers sans accord). Le hero garde le logo ; seule une vraie photo publiable, sans enseigne du centre, fermera ce point.

Limites : mesures sur serveur local, pas sur PythonAnywhere ; Lighthouse non exécuté ; pas d'essai sur téléphone
physique. Si `site.js` ne se charge pas alors que JavaScript est actif, le menu mobile reste replié.

## Journal de formation, partie 2 : rendu des entrées réelles — 22 octobre 2026

Aperçu isolé `scripts/preview_site.py --journal programme_shorts_pedago/nouvelles/02_partie2` (base temporaire,
les quatre fichiers sources publiés par `hub.journal.publier`, aucune donnée fictive). Contrôle Playwright du journal
(liste, grille) et des huit détails fr/en à 1 280, 768, 390 et 320 px, en clair et en sombre (skill taste,
refonte-préservation, sans nouvelle dépendance).

| Écart observé | Correction CSS | Mesure après correction |
| --- | --- | --- |
| Titre de détail de 70 caractères sur 3 lignes à 60 px (ordinateur) | `.article-heading h1` : `clamp(2rem, 3.2vw, 2.5rem)`, interligne 1,15 | 40 px, 2 lignes au plus |
| Même titre sur 5 lignes à 32 px (390 px) | mobile : 1,625 rem, interligne 1,2 | 26 px, 2 à 4 lignes ; texte visible dès le premier écran |
| Carte de grille seule sur sa journée : flèche isolée sur une ligne, bande vide | flèche à droite du contenu (`minmax(0, 1fr) auto`), contenu en haut | carte de 224 à 162 px |
| Mobile : colonne et espacement de la flèche masquée conservés | une seule colonne en grille mobile | contenu sur toute la largeur de la carte |

Aucun débordement horizontal mesuré. Deux entrées du même jour s'affichent par identifiant décroissant (RM-05,
conservé) : publier le module 4 avant le module 3 pour lire le 3 en premier (consigné dans le skill).
Captures locales non versionnées (`.playwright-mcp/`). Non exercés : téléphone physique, lecteur d'écran.

## Choix du thème — 22 octobre 2026

Aperçu isolé, Playwright. En-tête sur une ligne (73 px) de 961 à 1 440 px en fr et en, sans débordement ; un premier
essai repliait la navigation sur 2 ou 3 lignes entre 961 et 1 180 px (en-tête de 101 px), corrigé par un en-tête
compact jusqu'à 1 260 px (langue « FR → EN », marque sans sous-titre, espacements réduits ; cibles de 44 px gardées).
Sur mobile, le sélecteur est dans le menu, sous les quatre liens. Le sélecteur `.main-nav a:last-child` du bouton
Contact est devenu `.main-nav > a:last-of-type` pour ne pas styliser l'icône de lune.

Parcours exercés : système sombre sans cookie ; « Clair » au clavier (focus visible, Entrée, sans rechargement,
focus conservé) ; persistance au rechargement ; « Sombre » à la souris sur un système clair ; conservation sur une
autre page et en anglais ; retour à « Système » (cookie supprimé) ; parcours **sans JavaScript** (redirection vers la
page d'origine, thème appliqué). Non exercés : lecteur d'écran, téléphone physique.

## Audit taste (pré-vol) des gabarits du journal et du choix du thème — 22 octobre 2026

Design Read : refonte-préservation d'un journal de formation éditorial pour de futurs clients de Yaoundé,
langage sobre et technique (Lexend, bleu, turquoise), réglages repris de l'existant (variance 5, mouvement 3,
densité 4). Gabarits audités : `base.html`, `pages/news.html` (liste et grille), `pages/detail.html`,
`partials/theme_switch.html`, `partials/icon.html` ; textes des quatre entrées de la partie 2.

| Point du pré-vol | Constat | Preuve |
| --- | --- | --- |
| Zéro tiret cadratin ou demi-cadratin | Conforme | recherche dans gabarits, `LABELS` et entrées : aucun |
| Une étiquette en capitales par page | Conforme | une `eyebrow` par page publique |
| Points médians rationnés | Conforme | un par ligne, bandeau et note de démonstration seulement (aperçu local) |
| Icônes d'une seule bibliothèque | Conforme | Tabler via `partials/icon.html` (ajout de `sun`, `moon`, `device-desktop`) ; aucun SVG fait main |
| Thème verrouillé par page, sombre testé | Conforme | `data-theme` ou `prefers-color-scheme` sur `:root` ; rendus clair et sombre contrôlés |
| Contraste des boutons et du texte (AA) | Conforme | en ligne : texte de 5,87:1 à 16,19:1 dans les deux modes ; flèche et Contact 8,68:1 ou plus |
| Contraste des champs (3:1) | Conforme | bordure du sélecteur de filtre 3,46:1 (clair) et 3,46:1 (sombre) |
| Focus visible | Conforme | contour plein de 3 px sur les liens de thème |
| Rayons cohérents | Conforme | sélecteur de thème en pilule, comme Liste/Grille, langue et boutons |
| Navigation sur une ligne, hauteur 80 px au plus | Conforme après correction | 73 px de 961 à 1 440 px (en-tête compact jusqu'à 1 260 px) |
| Pas de `100vh` seul | **Corrigé** | `min-height: 100dvh` ajouté après `100vh` (repli) pour `body` et `.auth-body` |
| Pas de noir ni de blanc purs | Conforme | aucune couleur `#000`/`#fff` (seule mention : un commentaire) |
| Mouvement motivé, réduction respectée | Conforme | transitions de couleur de 0,18 s seulement ; retour en haut instantané sous `prefers-reduced-motion` |
| Relecture des textes | Conforme | phrases complètes, aucun nom propre interdit, aucune promesse de prestation |

Points sans objet sur ces gabarits (non modifiés ou absents) : hero, bento, mur de logos, citations, marquee,
animations GSAP, images. Aucun nouveau gabarit de page : les vues validées réutilisent `page.html` ; le seul
gabarit ajouté est `partials/theme_switch.html`, et les seuls fichiers statiques modifiés sont `site.css` et `site.js`.
