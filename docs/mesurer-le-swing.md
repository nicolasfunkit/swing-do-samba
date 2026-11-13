# Mesurer le swing d'un instrument à partir d'une vidéo

Ce document explique comment mesurer le placement des doubles-croches d'un
instrument, par exemple un cavaquinho, à partir d'un enregistrement, avec le
script `tools/mesurer_swing.py`. Il est écrit pour être repris dans une
session ultérieure, sans autre contexte.

## Pourquoi

L'appli et `docs/grooves-bresiliens.md` donnent le swing du samba mesuré sur
des percussions ou sur des disques complets. Je n'ai trouvé aucune étude qui
mesure le cavaquinho seul. Le script permet de faire cette mesure soi-même et
d'obtenir un groove comparable aux autres.

## Ce qu'il faut

- Python 3.10 ou plus récent. Aucune bibliothèque à installer.
- `ffmpeg` dans le PATH.
- Un fichier audio ou vidéo local. Le script ne télécharge rien.

Vérifier d'abord que tout fonctionne :

```bash
python3 tools/mesurer_swing.py --autotest
```

Le script fabrique deux signaux de cordes grattées au swing connu
(27 · 44 · 67 %), les mesure et affiche `AUTOTEST RÉUSSI` :

- une batida continue, retrouvée à 0,2 % du temps près lors de la mise au
  point ;
- un motif à trous sur 16 cases, en mode `--cycle 16` : le motif est
  reconnu, le tempo retrouvé sans aide, et les positions sont justes à 0,3 %
  près.

## Ce que le script mesure

Par défaut, il suppose que l'instrument joue **quatre notes par temps, en
continu**. Pour un motif avec des silences, voir « Motifs avec silences :
le mode cycle » plus bas.

1. Il découpe le son en trois bandes de fréquences et suit leur énergie
   milliseconde par milliseconde.
2. Chaque hausse brusque d'énergie est une attaque de note.
3. Les attaques sont regroupées par quatre. La note qui tombe sur le temps
   ouvre le groupe, celle du temps suivant le ferme.
4. La position des 2ᵉ, 3ᵉ et 4ᵉ notes est exprimée en fraction de
   l'intervalle entre ces deux temps : 0,25 · 0,50 · 0,75 si le jeu est droit.

C'est la même définition que dans Fuentes et al. (ISMIR 2019) : le temps est
défini par les notes de l'instrument lui-même, pas par un métronome. Le
résultat est donc directement comparable aux grooves de l'appli.

Un temps n'est gardé que s'il contient exactement quatre attaques, chacune à
moins de 12 % du temps de sa place sur la grille. Les autres sont comptés
comme rejetés, ce qui écarte les notes manquées, les fausses détections et les
passages où le motif change.

## Choisir les vidéos

La qualité de la mesure dépend surtout de la source. Chercher des passages
où :

- **l'instrument est seul** : pas de voix, de métronome, de percussion ni de
  piste d'accompagnement par-dessus. Les tutoriels où le musicien joue la
  batida sans parler conviennent bien ;
- **le motif est la batida continue**, avec les quatre doubles-croches de
  chaque temps. Pour les motifs syncopés (partido alto, variations de levada,
  samba rock), utiliser le mode cycle ;
- **le tempo est stable** et le passage dure au moins 30 temps, idéalement
  plus de 100 ;
- **il n'y a pas de coupe de montage** au milieu.

Pour chaque source, noter l'adresse, le minutage du passage, le musicien, le
style annoncé et le tempo. Sans ces notes, la mesure n'est pas vérifiable.

Les fichiers téléchargés et les résultats restent en local : le `.gitignore`
exclut les sons, les vidéos et le dossier `mesures/`. Ces vidéos appartiennent
à leurs auteurs.

Styles à viser en priorité, où le cavaquinho joue les doubles-croches en
continu : samba traditionnel (batida de base), pagode, samba-enredo, samba de
roda. Le samba-canção, lent et plus lié, sera sans doute plus proche de la
grille. Le partido alto et le samba rock ont des silences : ils se mesurent
avec le mode cycle.

## Marche à suivre

### 1. Repérer le passage

Ouvrir la vidéo et noter le début et la fin, en secondes, d'un passage qui
remplit les critères ci-dessus. Faire commencer le passage juste avant une
note qui tombe sur un temps.

### 2. Trouver le calage

Le script ne peut pas deviner laquelle des quatre notes tombe sur le temps :
les quatre calages donnent tous des résultats plausibles. C'est le point le
plus important de toute la mesure.

```bash
python3 tools/mesurer_swing.py video.mp4 --debut 17 --fin 23.5 --phases
```

Cette commande affiche le résultat pour les quatre calages. Pour choisir :

- **écouter le début du passage** et compter les notes jusqu'à la première
  qui tombe sur un temps. Si c'est la 4ᵉ attaque, le calage est
  `--premiere 4` ;
- en cas de doute, ralentir la vidéo ou afficher les marqueurs dans Audacity
  (voir l'étape 4) ;
- un mauvais calage se trahit souvent par une 2ᵉ note très en avance (vers
  18 %) ou une 3ᵉ note après 50 %, ce que les mesures publiées ne montrent
  jamais pour le samba. C'est un indice, pas une preuve.

### 3. Mesurer

```bash
mkdir -p mesures
python3 tools/mesurer_swing.py video.mp4 --debut 17 --fin 23.5 --premiere 4 \
  --json mesures/nom.json --labels mesures/nom.txt
```

Si le tempo estimé est manifestement faux (le double ou la moitié), ajouter
`--bpm` avec le tempo approximatif.

### 4. Vérifier à l'œil

Ouvrir le son dans Audacity, puis Fichier > Importer > Marqueurs et choisir
`mesures/nom.txt`. Chaque attaque détectée apparaît sur la forme d'onde ; les
débuts de temps gardés sont marqués `T`, les autres attaques `x`. Vérifier
sur une dizaine de temps que chaque marqueur est bien sur une attaque et qu'il
n'en manque pas.

### 5. Recommencer sur d'autres sources

Une vidéo ne mesure qu'un musicien, un jour donné. Pour parler d'un style,
viser au moins trois musiciens et comparer. Si les résultats divergent, les
présenter séparément plutôt que de les moyenner.

## Motifs avec silences : le mode cycle

Pour un partido alto ou une variation de levada, ajouter `--cycle` avec le
nombre de doubles-croches du cycle : 16 pour deux mesures de 2/4, 8 pour une
mesure.

```bash
python3 tools/mesurer_swing.py video.mp4 --debut 8 --fin 60 --bpm 92 \
  --cycle 16 --premiere 1
```

Ce qui change :

- **La pulsation est suivie de proche en proche.** Le script part de la note
  désignée par `--premiere`, qui doit tomber sur le **premier temps du
  cycle**, puis cherche une note à chaque temps suivant. Les temps sans note
  sont placés à intervalles égaux entre les deux notes de temps qui les
  entourent.
- **Chaque attaque est rangée dans une case** du cycle, selon la
  double-croche la plus proche.
- **Le résultat est donné case par case** : part des cycles où la note est
  jouée, position, dispersion, force. Le motif réellement joué apparaît en
  tête, par exemple `x . x x | . x . x | x . x . | . x x .`.
- **Un tableau regroupe les cases** par place dans le temps (2ᵉ, 3ᵉ, 4ᵉ
  double-croche), pour comparer aux grooves de référence.

Conditions pour que ça marche :

- **Le motif doit poser une note sur un temps assez souvent.** Le rapport
  indique la part des temps qui portent une note et le plus long trou. Les
  notes mesurées dans un trou de plus de 4 temps sont écartées
  (`--trou-max`), car on ne sait plus où est le temps.
- **Donner `--bpm`.** Sans lui, le script essaie tous les tempos de 50 à
  160 bpm et garde celui qui resserre le mieux les positions. Ça a marché sur
  le signal de test, mais il peut se tromper d'un facteur simple.
- **Prévoir plus long.** Chaque case reçoit une note par cycle au mieux :
  compter au moins 20 cycles, soit 80 temps pour `--cycle 16`.
- **Coups étouffés.** Si la main garde son va-et-vient et étouffe certaines
  notes, ces coups peuvent être détectés ou non selon `--sensibilite`. La
  colonne « force » aide à les repérer. Décider avant la mesure si on les
  compte, et garder le même réglage pour toutes les vidéos.

Le calage reste le point délicat, et il est double : la note de départ doit
être sur un temps, et ce temps doit être le premier du cycle. Un calage
décalé d'un temps donne les bonnes positions mais un motif décalé ; un calage
décalé d'une double-croche donne des positions fausses.

Exemple sur le passage « garfinho » de la vidéo d'Hosoi (7 à 10,6 s), avec
`--cycle 4 --bpm 120`. Avec `--premiere 1`, le motif sort en `x . x x`, et
avec `--premiere 2` en `x x x .` : ce ne sont pas des garfinhos, la note de
départ n'est pas sur le temps. Avec `--premiere 3`, on obtient bien
`x x . x`, aux positions 0 · 25 · 75 %.

## Lire le résultat

```
Attaques détectées : 51
Temps gardés : 12   rejetés : 0
Tempo médian : 120.0 bpm (un temps = 500 ms)

Position dans le temps, en % (grille droite : 25 · 50 · 75)
                       2ᵉ note   3ᵉ note   4ᵉ note
  Moyenne              27,5     46,1     71,1
  ...
```

| Ligne | Ce qu'elle dit |
|---|---|
| Temps gardés / rejetés | Si plus d'un temps sur cinq est rejeté, le passage ou les réglages ne conviennent pas. |
| Moyenne, médiane | Le résultat. Si elles diffèrent de plus de 1 %, quelques temps aberrants tirent la moyenne : préférer la médiane. |
| 10ᵉ et 90ᵉ centiles | L'étendue du jeu du musicien d'un temps à l'autre. |
| Écart-type | La régularité. Sur un musicien, 1 à 3 % est habituel dans les articles. |
| Erreur sur moyenne | La précision de la moyenne. En dessous de 0,5 %, la mesure est fine. |
| Écart à la grille en ms | La même chose en millisecondes, au tempo mesuré. |
| Force des notes | Niveau de chaque note en dB par rapport à la moyenne du temps : montre les accents. |
| Positions publiées | Les grooves de référence, pour situer la mesure. |

Le fichier JSON contient le détail temps par temps et un bloc `groove` au
format de `src/lib/grooves.ts`.

## Exemple réel

La vidéo d'André Hosoi qui a servi de point de départ au projet, passage
« ouvindo: samba » de 17 à 23,5 s :

```
--premiere 1 :  12 temps, positions 18,5 · 43,5 · 72,5   force -3,2 -1,4 -0,1 +4,7
--premiere 2 :  12 temps, positions 25,0 · 53,9 · 81,5   force -1,4 -0,1 +4,7 -3,2
--premiere 3 :  12 temps, positions 28,9 · 56,5 · 75,0   force -0,1 +4,7 -3,2 -1,4
--premiere 4 :  11 temps, positions 27,5 · 46,1 · 71,1   force +4,7 -3,2 -1,4 -0,1
```

Le passage commence au milieu d'un temps, donc le bon calage est le 4ᵉ. Il
donne 27,5 · 46,1 · 71,1 %, soit les valeurs que la vidéo affiche à l'écran,
avec la note du temps nettement plus forte. Les trois autres calages donnent
des chiffres tout aussi nets, mais faux.

Sur le passage « grade reta » de la même vidéo (3 à 4,8 s), le script trouve
24,9 · 50,0 · 75,0 %.

## Réglages en cas de problème

| Symptôme | Réglage |
|---|---|
| Des notes faibles ne sont pas détectées | `--sensibilite 1.5` ou `2` |
| Des bruits parasites sont pris pour des notes | `--sensibilite 0.7` |
| Deux attaques pour une seule note grattée | `--ecart-min 0.07` |
| Tempo rapide, notes fusionnées | `--ecart-min 0.035` |
| Tempo estimé double ou moitié | `--bpm` avec le tempo approximatif |
| Presque tous les temps sont rejetés | vérifier le calage, puis `--tolerance 0.15` |
| « La pulsation est perdue » | une coupe ou un silence : raccourcir le passage |
| Mode cycle : le motif affiché semble décalé | changer `--premiere` |
| Mode cycle : beaucoup de notes hors grille | donner `--bpm`, vérifier le calage |

Ne pas monter la tolérance au-delà de 0,15 : les fenêtres de deux notes
voisines se chevaucheraient.

## Limites

- **Le calage est un choix humain.** Une erreur d'une note donne un résultat
  net mais faux. Toujours le justifier par l'écoute.
- **Aller et retour du médiator.** Sur un cavaquinho, les notes paires et
  impaires sont grattées dans des sens opposés, et leur attaque n'a pas la
  même forme. Cela peut décaler de quelques millisecondes les notes 2 et 4
  par rapport aux notes 1 et 3. Le signal de test simule ce va-et-vient et
  l'erreur y reste sous 0,3 % du temps, mais un vrai instrument peut faire
  pire.
- **Étalement du grattage.** Les cordes ne sonnent pas ensemble. Le script
  date l'attaque au moment où l'énergie monte le plus vite, pas au premier
  contact.
- **Son de YouTube.** La compression ne déplace pas les attaques de façon
  mesurable, mais un son saturé, réverbéré ou pris de loin les rend floues.
- **Un musicien n'est pas un style.** Voir l'étape 5.
- **Force des notes.** C'est l'énergie des 40 ms qui suivent l'attaque. Elle
  indique les accents, mais dépend du micro et du mixage.
- **Grille de doubles-croches seulement.** Le mode cycle gère les silences,
  pas les triolets : une tercina sortirait comme des notes hors grille.
- **Mode cycle, temps interpolés.** Quand un temps ne porte pas de note, sa
  place est supposée, pas mesurée. Plus les trous sont longs, moins les
  positions voisines sont sûres. Le mode n'a été vérifié que sur un signal de
  synthèse et sur un exemple très court.

## Intégrer une mesure à l'appli

1. Ajouter une entrée dans `GROOVES` de `src/lib/grooves.ts`, en reprenant le
   bloc `groove` du JSON :

   ```ts
   {
     id: 'cavaco-nom',
     label: 'Cavaquinho (Nom)',
     hint: 'Cavaquinho seul, N temps mesurés : …',
     grid: SIXTEENTHS,
     // Mesure maison avec tools/mesurer_swing.py : source, minutage, calage.
     target: [0, 0.275, 0.461, 0.711],
   },
   ```

2. Ajouter le groove à `docs/grooves-bresiliens.md` avec le niveau de
   fiabilité « mesure maison », et la source dans le README.
3. Lancer `npm test`, `npm run check` et `npm run build`.

## Pour reprendre dans une autre session

Dire à Claude : « Lis `docs/mesurer-le-swing.md`, puis mesure le swing du
cavaquinho dans ces fichiers », en donnant pour chaque fichier le minutage du
passage et, si possible, le calage entendu.

À décider à ce moment-là :

- quelles vidéos et quels musiciens ;
- un groove par musicien, ou une moyenne s'ils concordent ;
- si l'on veut aussi reprendre la force des notes comme accents dans l'appli.
