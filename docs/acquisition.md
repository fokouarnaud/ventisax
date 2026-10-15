# Acquisition honnête — réseaux, capsules et WhatsApp

Décisions du grill du 15 octobre 2026 (voir `AGENTS.md`). Ventisax est **en formation** : aucune prestation
n'est vendue. L'acquisition sert à se faire connaître à Yaoundé et à constituer une liste de personnes à
prévenir à l'ouverture, sans promettre d'offre.

## Cible

Particuliers et petits commerces de Yaoundé et ses environs. Le démarchage B2B (gestionnaires immobiliers,
banques, supermarchés) est reporté : voir la condition de bascule plus bas.

## Chaîne de confiance

```
Capsule publique (Facebook, TikTok, YouTube Shorts)
  → entrée du « Journal de formation » sur le site (vidéo de leçon non répertoriée)
  → bouton « Me prévenir à l'ouverture » (WhatsApp pré-rempli avec le quartier)
  → étiquette « À prévenir » dans WhatsApp Business
```

## Vidéos

| Format | Visibilité YouTube | Où |
| --- | --- | --- |
| Capsule courte 9:16 | **Publique** | Facebook (Reels), TikTok, YouTube Shorts ; Instagram facultatif (republication depuis Facebook) |
| Vidéo de leçon | **Non répertoriée** | Intégrée à la nouvelle du site (champ `video_youtube`) |

Interdits maintenus : ni nom ni image du formateur, ni extrait ou photo du manuel, ni autres apprenants ou
locaux du centre sans leur accord. Aucune vidéo privée (elle ne se lit pas sur le site).

**Cadence :** une capsule par leçon réellement suivie, publiée la même semaine que l'entrée du journal.
Pas de contenu inventé pour « remplir ».

## Modèle de description des capsules

```
<Titre du module> — leçon du <date>.
Ventisax se forme en climatisation et froid à Yaoundé, étape par étape.

📖 La leçon complète : <URL de la nouvelle sur ventisax.pythonanywhere.com/fr/nouvelles/<slug>/>
🔔 Me prévenir à l'ouverture : https://wa.me/237652317898?text=Bonjour%20Ventisax%2C%20pr%C3%A9venez-moi%20%C3%A0%20l%E2%80%99ouverture%20de%20vos%20services%20de%20climatisation%20et%20de%20froid.%20Mon%20quartier%20%3A%20

Projet en formation — aucune prestation proposée pour l'instant.
#Yaounde #Cameroun #Climatisation #Froid
```

Le lien « Me prévenir » est le même que celui du site (`ConfigurationGenerale.notify_url`). Si le numéro
WhatsApp change dans Unfold, mettre aussi à jour ce modèle. L'appel à l'action oral ou écrit d'une capsule ne
promet jamais de prestation (« Un projet en clim ou en froid ? Parlons-en » reste admis).

## WhatsApp Business

- Description : « Ventisax — projet en formation en climatisation et froid à Yaoundé. Ouverture prochaine. »
- Message d'accueil automatique : remercier, rappeler qu'aucune prestation n'est encore proposée, demander le
  quartier si absent.
- Étiquette **« À prévenir »** sur chaque contact issu du bouton ; c'est la liste à prévenir au lancement.
- **Pas de catalogue** tant que rien n'est vendu.

## Profils sur le site

Les liens vers la chaîne YouTube et les profils Facebook, TikTok et Instagram se saisissent dans Unfold
(Configuration générale → Réseaux). Ils s'affichent en liens simples, sans widget ni SDK, dans le pied de page
et sur la page Contact, uniquement s'ils sont renseignés.

## Condition de bascule

Devis, bouton « Demander une intervention », proposition de valeur affirmative (« Installation, maintenance et
dépannage… ») et démarchage B2B attendent **une nouvelle décision explicite du porteur**, prise quand
l'intervention est réellement possible (fin de formation ou supervision avérée). Cette évolution révisera le
cadrage (Q4, Q14, hors-scope « formulaire de contact ») avant tout développement.

## Kit prêt à l'emploi — 15 octobre 2026

Textes à coller tels quels. Ces opérations se font sur le téléphone et les comptes du porteur ; elles ne
sont pas automatisables depuis le dépôt. Les longueurs respectent les limites des plateformes.

### 1. WhatsApp Business (téléphone du +237 652 317 898)

1. Installer **WhatsApp Business**, choisir le numéro actuel : l'historique est transféré.
2. Profil → catégorie **Éducation** (ne pas choisir une catégorie de service de climatisation).
3. Description : « Ventisax — projet en formation en climatisation et froid à Yaoundé. Aucune prestation pour
   l'instant ; ouverture prochaine. Suivez la formation : https://ventisax.pythonanywhere.com/fr/ »
4. Outils pro → **Message d'accueil** : « Merci pour votre message ! Ventisax est en formation : aucune
   prestation n'est proposée pour l'instant. Indiquez votre quartier, nous vous préviendrons à l'ouverture. »
5. Outils pro → **Étiquettes** → créer **« À prévenir »** ; l'appliquer à chaque contact venu du bouton du site.
6. **Catalogue : ne rien ajouter.**

### 2. Comptes réseaux (nom : Ventisax, identifiant visé : `@ventisax`)

| Réseau | Type de compte | Bio |
| --- | --- | --- |
| Facebook | Page, catégorie « Éducation » | Projet en formation en climatisation et froid à Yaoundé. Une leçon, une capsule. Ouverture prochaine. |
| TikTok | Compte personnel ou Business | Formation clim & froid à Yaoundé, étape par étape. Ouverture prochaine. |
| YouTube | Chaîne « Ventisax » | Projet en formation en climatisation et froid à Yaoundé (Cameroun). Une leçon réellement suivie = une capsule. Aucune prestation n'est proposée pour l'instant. Site : https://ventisax.pythonanywhere.com/fr/ |
| Instagram (facultatif) | Professionnel, catégorie « Éducation » | Projet en formation en climatisation et froid à Yaoundé 🇨🇲 Une leçon suivie = une capsule. Aucune prestation pour l'instant, ouverture prochaine. |

Lien du profil sur chaque réseau : `https://ventisax.pythonanywhere.com/fr/`. Une fois les comptes créés,
renseigner leurs URL dans Unfold (Configuration générale → Réseaux) — en production après déploiement de `0009`.

### 3. Première capsule publique : module 3, travail en hauteur

Fichier : `programme_shorts_pedago/capsule_module3.mp4` (9:16, 43 s → classée Short automatiquement).

- **Visibilité : Public** · Public visé : « Non, elle n'est pas conçue pour les enfants ».
- Titre : `Travailler en hauteur sans se mettre en danger | Formation clim & froid #Shorts`
- Description :

```
Module 3 — leçon du 13 octobre 2026.
Ventisax se forme en climatisation et froid à Yaoundé, étape par étape.

📖 La leçon complète : https://ventisax.pythonanywhere.com/fr/nouvelles/formation-travail-en-hauteur/
🔔 Me prévenir à l'ouverture : https://wa.me/237652317898?text=Bonjour%20Ventisax%2C%20pr%C3%A9venez-moi%20%C3%A0%20l%E2%80%99ouverture%20de%20vos%20services%20de%20climatisation%20et%20de%20froid.%20Mon%20quartier%20%3A%20

Projet en formation — aucune prestation proposée pour l'instant.
#Yaounde #Cameroun #Climatisation #Froid
```

Le lien de la leçon ne fonctionnera qu'après publication de la nouvelle en production
(`programme_shorts_pedago/nouvelles/2026-10-13-travail-en-hauteur.md`). Une vidéo de leçon plus longue, si
elle existe, se met en ligne en **non répertoriée** et son lien va dans le champ « vidéo YouTube » de la nouvelle.
Publier ensuite la même capsule sur Facebook (Reels) et TikTok avec la même description.
