# Le swing du samba

Page interactive qui fait entendre et voir le microtemps du samba : on choisit
un groove, on règle le tempo et la quantité de swing, et on observe où tombe
chaque note dans le temps, en pourcentage et en millisecondes.

Pile : TypeScript, Vite, Svelte 5, Tone.js (synthèse sonore, aucun fichier audio).

## Lancer

```bash
npm install
npm run dev      # serveur de développement
npm test         # tests du modèle de timing
npm run check    # vérification des types (svelte-check)
npm run build    # build de production dans dist/
```

## Exporter en site statique

```bash
npm run build
```

Le dossier `dist/` contient alors tout le site : un `index.html`, un fichier
JS et un fichier CSS, sans serveur applicatif. On peut le déposer tel quel sur
n'importe quel hébergement statique, à la racine ou dans un sous-dossier.

Pour vérifier le résultat en local : `npm run preview`. Ouvrir `index.html`
directement depuis le disque ne marche pas, le navigateur bloque les modules
JS en `file://`.

## Mobile et installation (PWA)

La page s'adapte à la largeur de l'écran. La ligne de temps est dessinée à
l'échelle 1 unité = 1 pixel et se recalcule selon la largeur disponible : elle
s'étire, mais les points et les textes gardent la même taille. Les boutons et
curseurs font au moins 44 px de haut pour le tactile.

Le site est installable et marche hors ligne après une première visite :

- `public/manifest.webmanifest` : nom, couleurs, icônes ;
- `public/sw.js` : service worker écrit à la main, sans dépendance. À
  l'installation il lit `index.html` pour trouver les fichiers JS et CSS (leur
  nom change à chaque build) et les met en cache. La page est servie réseau
  d'abord, les fichiers cache d'abord ;
- le service worker n'est enregistré que sur le build de production, pas en
  `npm run dev`.

Une PWA exige HTTPS (ou `localhost`). Sur iPhone, le son passe par le bouton
latéral : en mode silencieux, rien ne sort.

## Origine

Le projet part de la vidéo « O swing do samba » d'André Hosoi
(non incluse dans le dépôt, elle appartient à son auteur). La vidéo a été lue image par image
(une image par seconde, extraite avec `ffmpeg`) ; le son n'a pas été analysé.
Les valeurs chiffrées viennent donc de ce qui est écrit à l'écran.

Ce que la vidéo affirme :

| Cellule                 | Position des notes dans le temps |
| ----------------------- | -------------------------------- |
| Grille droite           | 0 · 25 · 50 · 75 %               |
| Garfinho (16-8-16)      | 0 · 25 · 75 %                    |
| Tercina (triolet)       | 0 · 33 · 67 %                    |
| Samba (tamborim mesuré) | 0 · 25–29 · 42–50 · 67–75 %      |

La 2ᵉ double-croche retarde légèrement, les 3ᵉ et 4ᵉ sont avancées de 10 à
52 ms ; l'écart moyen vaut environ 1/40 du temps (source citée par la vidéo :
Gouyon 2007, samba de roda). Le jazz et le swing MPC, eux, retardent des notes
au lieu de les avancer.

## Approche

### 1. Tout exprimer en fraction du temps

Un groove est décrit par la position de ses notes à l'intérieur d'un seul
temps, entre 0 et 1 (`src/lib/grooves.ts`). Chaque groove a deux listes :

- `grid` : les positions écrites sur la partition (swing 0 %) ;
- `target` : les positions réellement jouées (swing 100 %).

Le curseur de swing interpole linéairement entre les deux. Les grooves sans
swing (grille droite, garfinho, tercina) ont simplement `grid` égal à
`target`, et le curseur est alors désactivé.

Le BPM n'intervient qu'au dernier moment, pour convertir une fraction en
millisecondes (`60000 / bpm` par temps). Quand le tempo change, les
pourcentages ne bougent pas, les millisecondes si. À 90 bpm
l'écart moyen du samba est d'environ 17 ms, à 140 bpm d'environ 11 ms.

### 2. Programmer le son sur l'horloge audio

Des écarts de 10 à 20 ms sont trop fins pour un `setInterval`. Le moteur
(`src/lib/engine.ts`) utilise donc un planificateur à anticipation :

- un minuteur JavaScript se réveille toutes les 25 ms ;
- il programme, sur l'horloge audio de Tone.js (précise à l'échantillon),
  tous les temps qui commencent dans les 150 ms à venir ;
- chaque note reçoit une heure exacte : `début du temps + fraction × durée`.

Les réglages sont relus au début de chaque temps. Un changement de BPM, de
swing ou de groove s'entend donc au temps suivant, sans coupure.

### 3. Synthétiser les instruments

Trois voix Tone.js, sans échantillons :

- **tamborim** : une membrane aiguë très courte, doublée d'un claquement de
  bruit blanc filtré ; la première note du temps est accentuée ;
- **surdo** : une membrane grave sur chaque temps, étouffée sur le 1, ouverte
  et plus forte sur le 2 ;
- **palma** (optionnelle) : du bruit rose passe-bande sur le 2.

### 4. Synchroniser l'affichage sur le son

L'interface (`src/App.svelte`) ne tient pas sa propre horloge. À chaque image
(`requestAnimationFrame`), elle demande au moteur quel temps est en cours et
en déduit la position de la tête de lecture et les notes à allumer.

La ligne de temps montre les cercles vides de la grille écrite, les points
pleins des notes jouées, un trait coloré pour le déplacement entre les deux,
et en pointillés les tiers du triolet. Le tableau en dessous donne pour
chaque note sa position, son instant et son écart à la grille.

## Choix et limites

- **Valeurs du samba** : `0 · 27 · 46 · 71 %`, le milieu des fourchettes
  de la vidéo. C'est un choix d'implémentation, pas une mesure. Il donne un
  écart moyen d'exactement 1/40 du temps, cohérent avec la vidéo.
- **Swing MPC** : réglé à 62 % (`0 · 31 · 50 · 81 %`). La vidéo ne donne pas
  de chiffre ; c'est une valeur courante, à ajuster.
- **Jazz** : deux croches par temps, la 2ᵉ allant jusqu'au rapport 2:1.
- **Écart en ms** : la vidéo donne à la fois des pourcentages et des écarts
  en ms. Le modèle retient les pourcentages ; les ms en découlent selon le
  tempo.
- **Onglet en arrière-plan** : le navigateur ralentit les minuteurs, la
  lecture peut alors avoir des trous. Elle se recale au retour.
- **Pas encore fait** : les cycles de 16 pulsations (tresillo, paradigme de
  l'Estácio), le test d'écoute A/B à l'aveugle et l'exercice ta-ka-di-mi.

## Structure

```
src/lib/grooves.ts        modèle : grooves, interpolation, conversion en ms
src/lib/grooves.test.ts   tests du modèle
src/lib/engine.ts         planificateur et synthèse Tone.js
src/App.svelte            interface et visualisation
public/                   manifeste, service worker, icônes
```
