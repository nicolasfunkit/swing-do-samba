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

## En ligne

Le site est publié sur GitHub Pages : https://nicolasfunkit.github.io/swing-do-samba/

Chaque push sur `main` lance `.github/workflows/pages.yml`, qui exécute les
tests, construit `dist/` et le déploie.

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
la 3ᵉ note du samba est en avance de 21 ms, à 140 bpm de 14 ms.

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

- **Deux sambas à comparer** : « Samba (Naveda, Gouyon) » joue les moyennes
  mesurées, « Samba (Hosoi) » joue les valeurs de la vidéo. On passe de l'un à
  l'autre pendant la lecture, le changement s'entend au temps suivant.
- **Samba (Hosoi)** : `0 · 27 · 46 · 71 %`, le milieu des fourchettes
  affichées dans la vidéo (le choix du milieu est le nôtre). L'écart moyen
  vaut alors exactement 1/40 du temps, le chiffre annoncé par la vidéo. Ces
  fourchettes (25–29, 42–50, 67–75 %) sont mot pour mot l'intervalle dans
  lequel Fuentes et al. (ISMIR 2019) cherchent le placement du tamborim en
  samba-enredo : ce sont des bornes de recherche, pas des valeurs mesurées.
- **Tamborim (Fuentes)** : `0 · 27 · 43,4 · 67,1 %`, d'après Fuentes et al.
  (ISMIR 2019), qui annotent 396 temps de tamborim seul en samba-enredo. Le
  texte ne donne pas de moyenne : les 3ᵉ et 4ᵉ positions sont le centre du
  nuage de points de leur figure 6, relevé par analyse d'image, donc à
  0,005 près environ (80 % des points sont entre 40,7 et 46,2 % pour la 3ᵉ,
  entre 65,4 et 68,9 % pour la 4ᵉ). La 2ᵉ note n'est pas lisible sur la
  figure ; elle est placée au milieu de leur intervalle de recherche. C'est
  de loin le swing le plus marqué de l'appli : environ 40 et 47 ms d'avance
  à 100 bpm, contre 19 et 16 ms dans les mesures de Naveda sur des disques
  complets.
- **Pandeiro (Lindsay)** : `0 · 29,3 · 44,1 · 67,2 %`, d'après la figure 28
  de Lindsay et Nordquist (2007) : une batida de pandeiro seul, vers 125 bpm.
  C'est la moyenne, sur 8 temps, de la position des marqueurs de notes de la
  figure, relevée par analyse d'image. D'un temps à l'autre les valeurs
  varient de 27,5 à 30,5 %, de 41,4 à 46,1 % et de 65,1 à 69,4 %. Le texte
  confirme que la 4ᵉ note tombe sur une subdivision de triolet. Un seul
  musicien, un seul enregistrement : c'est un exemple, pas une moyenne de
  style.
- **Samba de Bahia** : trois grooves tirés de Gerischer (2006), un par
  instrument. Elle donne la durée moyenne de chaque double-croche (100 = une
  double-croche égale) : pandeiro `109 · 76 · 90 · 125`, reco-reco
  `99 · 85 · 96 · 120`, triangle `106 · 77 · 100 · 117`. Le code les convertit
  en positions. Je n'ai pas lu l'article : ces chiffres viennent du tableau
  repris par Haugen et Danielsen (2020), obtenu via un extrait de moteur de
  recherche. Chaque ligne fait bien 400, mais ils restent à vérifier sur le
  texte.
- **Non ajoutés** : le surdo et l'agogô de Lindsay et Nordquist, qui ne
  jouent pas les quatre doubles-croches (le surdo marque la pulsation,
  l'agogô joue un motif mélodique « légèrement en avance ») ; et le choro,
  pour lequel je n'ai trouvé aucune mesure publiée.
- **Samba (Naveda, Gouyon)** : `0 · 25 · 46,8 · 72,3 %`. Ce sont les moyennes
  publiées par Naveda, Gouyon, Guedes et Leman (2011) pour l'aigu du spectre,
  là où joue le tamborim : 3ᵉ double-croche en avance de 0,032 temps, 4ᵉ de
  0,027 temps (19 et 16 ms à 103 bpm, le tempo moyen de leur corpus). Elles
  tombent dans les fourchettes de la vidéo.
- **2ᵉ double-croche** : la vidéo la montre légèrement en retard (25 → 29 %).
  L'article ne rapporte pas d'écart de placement sur cette note, seulement un
  accent d'intensité ; elle reste donc sur la grille ici.
- **Écart moyen** : la vidéo annonce environ 1/40 du temps. Avec les moyennes
  de l'article on obtient plutôt 1/68 sur les quatre notes, soit 1/34 sur les
  deux notes déplacées.
- **Ce que la mesure couvre** : 106 extraits de CD du commerce, analysés par
  bandes de fréquences sur le mélange complet, pas un tamborim isolé. L'article
  trouve aussi un léger retard des graves sur la 1ʳᵉ double-croche (0,012
  temps, 7 ms), que l'appli ne reproduit pas.
- **Swing MPC** : réglé à 62 % (`0 · 31 · 50 · 81 %`). La définition vient de
  Roger Linn : le pourcentage est la part de la première double-croche dans
  chaque croche, 50 % = droit, 66 % = triolet, et seules les doubles-croches
  paires sont retardées. Il cite lui-même 62 % comme réglage plus souple que
  66 % à 90 bpm. La vidéo ne donne pas de chiffre. À titre de comparaison,
  Frane (2017) mesure un swing bien plus léger dans les breaks de batterie
  classiques du hip-hop : rapport médian 1,2:1, soit environ 55 %.
- **Jazz** : deux croches par temps, dont le rapport long/court dépend du
  tempo. C'est le seul groove où le BPM change les proportions. Le modèle
  garde la note courte à 100 ms et borne le rapport entre 1:1 et 3,5:1 : il
  vaut 3,5:1 jusqu'à 133 bpm, 2:1 à 200 bpm, 1:1 à 300 bpm. Il s'appuie sur
  Friberg & Sundström (2002), qui ont mesuré la cymbale ride de batteurs ;
  c'est une simplification de leurs résultats, pas un ajustement sur leurs
  données, et les solistes swinguent en général moins que ça. Le curseur de
  tempo monte à 300 bpm pour ce groove, 160 pour les autres.
- **Écart en ms** : la vidéo donne à la fois des pourcentages et des écarts
  en ms. Le modèle retient les pourcentages ; les ms en découlent selon le
  tempo.
- **Onglet en arrière-plan** : le navigateur ralentit les minuteurs, la
  lecture peut alors avoir des trous. Elle se recale au retour.
- **Pas encore fait** : les cycles de 16 pulsations (tresillo, paradigme de
  l'Estácio), le test d'écoute A/B à l'aveugle et l'exercice ta-ka-di-mi.

## Sources

- **Samba** : L. Naveda, F. Gouyon, C. Guedes, M. Leman, « Microtiming Patterns
  and Interactions with Musical Properties in Samba Music », *Journal of New
  Music Research* 40(3), 2011, p. 225-238.
  [doi:10.1080/09298215.2011.603833](https://doi.org/10.1080/09298215.2011.603833).
  Lu en entier. L'article confirme Gouyon (2007), que la vidéo cite et que je
  n'ai pas pu consulter.
- **Jazz** : A. Friberg, A. Sundström, « Swing Ratios and Ensemble Timing in
  Jazz Performance », *Music Perception* 19(3), 2002, p. 333-349.
  [doi:10.1525/mp.2002.19.3.333](https://doi.org/10.1525/mp.2002.19.3.333).
  Résumé seulement.
- **Swing MPC** : entretien avec Roger Linn,
  [Attack Magazine](https://www.attackmagazine.com/features/interview/roger-linn-swing-groove-magic-mpc-timing/).
- **Swing à la double-croche** : A. V. Frane, « Swing Rhythm in Classic Drum
  Breaks From Hip-Hop's Breakbeat Canon », *Music Perception* 34(3), 2017,
  p. 291-302.
  [doi:10.1525/mp.2017.34.3.291](https://doi.org/10.1525/mp.2017.34.3.291).
  Résumé seulement.
- **Samba de Bahia** : C. Gerischer, « O suingue baiano: Rhythmic Feeling and
  Microrhythmic Phenomena in Brazilian Percussion », *Ethnomusicology* 50(1),
  2006, p. 99-119. Non lu ; valeurs reprises de M. R. Haugen et A. Danielsen,
  « Effect of tempo on relative note durations in a performed samba groove »,
  *Journal of New Music Research*, 2020.
  [doi:10.1080/09298215.2020.1767655](https://doi.org/10.1080/09298215.2020.1767655).
- **Tamborim** : M. Fuentes et al., « Tracking Beats and Microtiming in
  Afro-Latin American Music Using Conditional Random Fields and Deep
  Learning », ISMIR 2019.
  [PDF](https://archives.ismir.net/ismir2019/paper/000029.pdf),
  [HAL](https://hal.science/hal-02419361v1). Lu en entier.
- **Pandeiro** : K. Lindsay, P. Nordquist, « Pulse and Swing: Quantitative
  Analysis of Hierarchical Rhythmic Structure », 2007 (version longue de leur
  communication au JASA). Section sur le Brésil lue en entier.
- **Vidéo de départ** : André Hosoi, « O swing do samba ».

## Structure

```
src/lib/grooves.ts        modèle : grooves, interpolation, conversion en ms
src/lib/grooves.test.ts   tests du modèle
src/lib/engine.ts         planificateur et synthèse Tone.js
src/App.svelte            interface et visualisation
public/                   manifeste, service worker, icônes
```
