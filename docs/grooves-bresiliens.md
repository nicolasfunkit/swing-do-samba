# Grooves brésiliens et tercina : données pour séquenceur

Ce document donne, pour chaque groove, la position des notes à l'intérieur
d'un temps, sous plusieurs formes directement utilisables dans un séquenceur :
fraction du temps, ticks, décalage par pas et millisecondes. Les données
viennent du projet `swing-do-samba` (`src/lib/grooves.ts`).

## Conventions

- **Temps** : la noire. Le samba s'écrit en 2/4, donc une mesure = 2 temps.
- **Position** : fraction du temps, de 0 (début du temps) à 1 (temps suivant).
  Elle ne dépend pas du tempo.
- **Grille** : quatre doubles-croches égales, à 0 · 0,25 · 0,50 · 0,75.
- **Écart** : position jouée moins position de grille. Négatif = en avance,
  positif = en retard.
- **Pas** : une double-croche, soit un quart de temps (séquenceur à 4 pas par
  temps, 16 pas pour deux mesures de 2/4).

## Formules

```
duree_temps_ms = 60000 / bpm
instant_ms     = (numero_temps + position) * duree_temps_ms
tick           = round(position * PPQ)            # PPQ = ticks par noire
ecart_pas_pct  = (position - grille) * 4 * 100    # en % de la durée d'un pas
position(swing) = grille + (cible - grille) * swing   # swing de 0 à 1
```

La dernière formule sert de bouton « quantité de swing » : 0 donne la grille,
1 donne le groove complet, et rien n'empêche de dépasser 1 pour exagérer.

## Fiabilité des valeurs

| Niveau | Signification |
|---|---|
| A | Moyennes publiées, lues dans le texte de l'article |
| B | Valeurs relevées sur une figure de l'article par analyse d'image |
| C | Valeurs de seconde main ou choix d'interprétation |
| référence | Figure de notation, exacte par définition |

## Vue d'ensemble

Position de chaque note en % du temps.

| Groove | Note 1 | Note 2 | Note 3 | Note 4 | Fiabilité |
|---|---|---|---|---|---|
| Grille droite | 0,0 | 25,0 | 50,0 | 75,0 | référence |
| Samba, disques complets | 0,0 | 25,0 | 46,8 | 72,3 | A |
| Samba, vidéo Hosoi | 0,0 | 27,0 | 46,0 | 71,0 | C |
| Tamborim seul, samba-enredo | 0,0 | 27,0 | 43,4 | 67,1 | B |
| Pandeiro seul, batida | 0,0 | 29,3 | 44,1 | 67,2 | B |
| Samba de Bahia, pandeiro | 0,0 | 27,3 | 46,3 | 68,8 | C |
| Samba de Bahia, reco-reco | 0,0 | 24,8 | 46,0 | 70,0 | C |
| Samba de Bahia, triangle | 0,0 | 26,5 | 45,8 | 70,8 | C |
| Garfinho | 0,0 | 25,0 | 75,0 | — | référence |
| Tercina | 0,0 | 33,3 | 66,7 | — | référence |

## Détail par groove

### Grille droite (`grille`)

Quatre doubles-croches égales.

- **Source** : —
- **Fiabilité** : référence

| | Note 1 | Note 2 | Note 3 | Note 4 |
|---|---|---|---|---|
| Position (fraction) | 0,0000 | 0,2500 | 0,5000 | 0,7500 |
| Tick à 96 PPQ | 0 | 24 | 48 | 72 |
| Tick à 480 PPQ | 0 | 120 | 240 | 360 |
| Tick à 960 PPQ | 0 | 240 | 480 | 720 |
| Écart en ticks (960 PPQ) | 0 | 0 | 0 | 0 |
| Écart en % d'un pas | 0 | 0 | 0 | 0 |
| Écart en ms à 90 bpm | 0 | 0 | 0 | 0 |
| Écart en ms à 100 bpm | 0 | 0 | 0 | 0 |
| Écart en ms à 120 bpm | 0 | 0 | 0 | 0 |
| Écart en ms à 140 bpm | 0 | 0 | 0 | 0 |

### Samba, disques complets (`samba-naveda`)

Moyennes sur 106 extraits de CD (5064 temps, tempo moyen 103 bpm), bande aiguë du spectre. Mélange complet, pas un instrument isolé.

- **Source** : Naveda, Gouyon, Guedes, Leman (2011)
- **Fiabilité** : A

| | Note 1 | Note 2 | Note 3 | Note 4 |
|---|---|---|---|---|
| Position (fraction) | 0,0000 | 0,2500 | 0,4680 | 0,7230 |
| Tick à 96 PPQ | 0 | 24 | 45 | 69 |
| Tick à 480 PPQ | 0 | 120 | 225 | 347 |
| Tick à 960 PPQ | 0 | 240 | 449 | 694 |
| Écart en ticks (960 PPQ) | 0 | 0 | −31 | −26 |
| Écart en % d'un pas | 0 | 0 | −12,8 | −10,8 |
| Écart en ms à 90 bpm | 0 | 0 | −21 | −18 |
| Écart en ms à 100 bpm | 0 | 0 | −19 | −16 |
| Écart en ms à 120 bpm | 0 | 0 | −16 | −14 |
| Écart en ms à 140 bpm | 0 | 0 | −14 | −12 |

### Samba, vidéo Hosoi (`samba-hosoi`)

Milieu des fourchettes de la vidéo (25–29, 42–50, 67–75 %), qui sont l’intervalle de recherche de Fuentes et al. (2019), pas des mesures.

- **Source** : André Hosoi, « O swing do samba »
- **Fiabilité** : C

| | Note 1 | Note 2 | Note 3 | Note 4 |
|---|---|---|---|---|
| Position (fraction) | 0,0000 | 0,2700 | 0,4600 | 0,7100 |
| Tick à 96 PPQ | 0 | 26 | 44 | 68 |
| Tick à 480 PPQ | 0 | 130 | 221 | 341 |
| Tick à 960 PPQ | 0 | 259 | 442 | 682 |
| Écart en ticks (960 PPQ) | 0 | +19 | −38 | −38 |
| Écart en % d'un pas | 0 | +8,0 | −16,0 | −16,0 |
| Écart en ms à 90 bpm | 0 | +13 | −27 | −27 |
| Écart en ms à 100 bpm | 0 | +12 | −24 | −24 |
| Écart en ms à 120 bpm | 0 | +10 | −20 | −20 |
| Écart en ms à 140 bpm | 0 | +9 | −17 | −17 |

### Tamborim seul, samba-enredo (`tamborim-fuentes`)

396 temps. 3ᵉ et 4ᵉ : centre du nuage de la figure 6, lu par analyse d’image (± 0,005). 2ᵉ : non mesurée, milieu de l’intervalle 0,25–0,29.

- **Source** : Fuentes et al. (ISMIR 2019)
- **Fiabilité** : B

| | Note 1 | Note 2 | Note 3 | Note 4 |
|---|---|---|---|---|
| Position (fraction) | 0,0000 | 0,2700 | 0,4340 | 0,6710 |
| Tick à 96 PPQ | 0 | 26 | 42 | 64 |
| Tick à 480 PPQ | 0 | 130 | 208 | 322 |
| Tick à 960 PPQ | 0 | 259 | 417 | 644 |
| Écart en ticks (960 PPQ) | 0 | +19 | −63 | −76 |
| Écart en % d'un pas | 0 | +8,0 | −26,4 | −31,6 |
| Écart en ms à 90 bpm | 0 | +13 | −44 | −53 |
| Écart en ms à 100 bpm | 0 | +12 | −40 | −47 |
| Écart en ms à 120 bpm | 0 | +10 | −33 | −39 |
| Écart en ms à 140 bpm | 0 | +9 | −28 | −34 |

### Pandeiro seul, batida (`pandeiro-lindsay`)

8 temps d’un seul enregistrement (1963), vers 125 bpm, lus sur la figure 28 (± 0,005).

- **Source** : Lindsay & Nordquist (2007)
- **Fiabilité** : B

| | Note 1 | Note 2 | Note 3 | Note 4 |
|---|---|---|---|---|
| Position (fraction) | 0,0000 | 0,2930 | 0,4410 | 0,6720 |
| Tick à 96 PPQ | 0 | 28 | 42 | 65 |
| Tick à 480 PPQ | 0 | 141 | 212 | 323 |
| Tick à 960 PPQ | 0 | 281 | 423 | 645 |
| Écart en ticks (960 PPQ) | 0 | +41 | −57 | −75 |
| Écart en % d'un pas | 0 | +17,2 | −23,6 | −31,2 |
| Écart en ms à 90 bpm | 0 | +29 | −39 | −52 |
| Écart en ms à 100 bpm | 0 | +26 | −35 | −47 |
| Écart en ms à 120 bpm | 0 | +21 | −30 | −39 |
| Écart en ms à 140 bpm | 0 | +18 | −25 | −33 |

### Samba de Bahia, pandeiro (`bahia-pandeiro`)

Durées moyennes 109 · 76 · 90 · 125 (100 = double-croche égale). Tableau obtenu de seconde main, à vérifier.

- **Source** : Gerischer (2006), via Haugen & Danielsen (2020)
- **Fiabilité** : C

| | Note 1 | Note 2 | Note 3 | Note 4 |
|---|---|---|---|---|
| Position (fraction) | 0,0000 | 0,2725 | 0,4625 | 0,6875 |
| Tick à 96 PPQ | 0 | 26 | 44 | 66 |
| Tick à 480 PPQ | 0 | 131 | 222 | 330 |
| Tick à 960 PPQ | 0 | 262 | 444 | 660 |
| Écart en ticks (960 PPQ) | 0 | +22 | −36 | −60 |
| Écart en % d'un pas | 0 | +9,0 | −15,0 | −25,0 |
| Écart en ms à 90 bpm | 0 | +15 | −25 | −42 |
| Écart en ms à 100 bpm | 0 | +14 | −22 | −38 |
| Écart en ms à 120 bpm | 0 | +11 | −19 | −31 |
| Écart en ms à 140 bpm | 0 | +10 | −16 | −27 |

### Samba de Bahia, reco-reco (`bahia-reco-reco`)

Durées moyennes 99 · 85 · 96 · 120. Même réserve.

- **Source** : Gerischer (2006), via Haugen & Danielsen (2020)
- **Fiabilité** : C

| | Note 1 | Note 2 | Note 3 | Note 4 |
|---|---|---|---|---|
| Position (fraction) | 0,0000 | 0,2475 | 0,4600 | 0,7000 |
| Tick à 96 PPQ | 0 | 24 | 44 | 67 |
| Tick à 480 PPQ | 0 | 119 | 221 | 336 |
| Tick à 960 PPQ | 0 | 238 | 442 | 672 |
| Écart en ticks (960 PPQ) | 0 | −2 | −38 | −48 |
| Écart en % d'un pas | 0 | −1,0 | −16,0 | −20,0 |
| Écart en ms à 90 bpm | 0 | −2 | −27 | −33 |
| Écart en ms à 100 bpm | 0 | −2 | −24 | −30 |
| Écart en ms à 120 bpm | 0 | −1 | −20 | −25 |
| Écart en ms à 140 bpm | 0 | −1 | −17 | −21 |

### Samba de Bahia, triangle (`bahia-triangle`)

Durées moyennes 106 · 77 · 100 · 117. Même réserve.

- **Source** : Gerischer (2006), via Haugen & Danielsen (2020)
- **Fiabilité** : C

| | Note 1 | Note 2 | Note 3 | Note 4 |
|---|---|---|---|---|
| Position (fraction) | 0,0000 | 0,2650 | 0,4575 | 0,7075 |
| Tick à 96 PPQ | 0 | 25 | 44 | 68 |
| Tick à 480 PPQ | 0 | 127 | 220 | 340 |
| Tick à 960 PPQ | 0 | 254 | 439 | 679 |
| Écart en ticks (960 PPQ) | 0 | +14 | −41 | −41 |
| Écart en % d'un pas | 0 | +6,0 | −17,0 | −17,0 |
| Écart en ms à 90 bpm | 0 | +10 | −28 | −28 |
| Écart en ms à 100 bpm | 0 | +9 | −25 | −25 |
| Écart en ms à 120 bpm | 0 | +8 | −21 | −21 |
| Écart en ms à 140 bpm | 0 | +6 | −18 | −18 |

### Garfinho (`garfinho`)

Double-croche, croche, double-croche. Figure écrite, sans microtemps.

- **Source** : notation
- **Fiabilité** : référence

| | Note 1 | Note 2 | Note 3 |
|---|---|---|---|
| Position (fraction) | 0,0000 | 0,2500 | 0,7500 |
| Tick à 96 PPQ | 0 | 24 | 72 |
| Tick à 480 PPQ | 0 | 120 | 360 |
| Tick à 960 PPQ | 0 | 240 | 720 |

### Tercina (`tercina`)

Triolet de croches : trois notes égales dans le temps.

- **Source** : notation
- **Fiabilité** : référence

| | Note 1 | Note 2 | Note 3 |
|---|---|---|---|
| Position (fraction) | 0,0000 | 0,3333 | 0,6667 |
| Tick à 96 PPQ | 0 | 32 | 64 |
| Tick à 480 PPQ | 0 | 160 | 320 |
| Tick à 960 PPQ | 0 | 320 | 640 |

## Garfinho et tercina dans un séquenceur à pas

Ces deux figures n'ont pas quatre notes par temps. Sur une grille de quatre
pas par temps :

| Figure | Pas 1 | Pas 2 | Pas 3 | Pas 4 |
|---|---|---|---|---|
| Garfinho | note | note | silence | note |
| Tercina (option 1) | note | note, +33,3 % d'un pas | note, +66,7 % d'un pas | silence |
| Tercina (option 2) | note | note, +33,3 % d'un pas | silence | note, −33,3 % d'un pas |

Les deux options de tercina donnent les mêmes instants (0 · 33,3 · 66,7 % du
temps). L'option 2 garde chaque décalage sous un demi-pas, ce que beaucoup de
séquenceurs imposent.

Si le séquenceur accepte une grille ternaire, la tercina est simplement trois
pas égaux par temps : ticks 0 · 160 · 320 à 480 PPQ.

## Le samba entre garfinho et tercina

Sur les instruments seuls, la 4ᵉ double-croche tombe pratiquement sur la
dernière note de la tercina (66,7 %) :

| | Note 2 | Note 3 | Note 4 |
|---|---|---|---|
| Garfinho | 25,0 | — | 75,0 |
| Tamborim seul | 27,0 | 43,4 | 67,1 |
| Pandeiro seul | 29,3 | 44,1 | 67,2 |
| Tercina | 33,3 | — | 66,7 |

## Détails optionnels

Ces observations viennent de Naveda et al. (2011) et ne sont pas dans les
tableaux ci-dessus :

- **Grave en retard** : dans le bas du spectre (surdo), la 1ʳᵉ double-croche
  est en retard de 0,012 temps, soit 7 ms à 103 bpm. Pour le reproduire,
  décaler la piste de grave de +12 ticks à 960 PPQ.
- **Accents** : voir la section « Accentuation » ci-dessous.
- **Phrasé sur plusieurs temps** : l'article décrit des accélérations et
  ralentissements sur 2 et 4 temps, sans chiffres simples à reprendre.

Haugen et Danielsen (2020) indiquent par ailleurs que les proportions bougent
avec le tempo sur un pandeiro : la 2ᵉ double-croche raccourcit et la 4ᵉ
s'allonge quand le tempo monte. Je n'ai que leur résumé, pas de chiffres.

## Accentuation

Le placement ne suffit pas : Naveda et al. (2011) montrent que les écarts de
temps vont de pair avec un profil d'intensité, qui n'est pas le même sur les
deux temps de la mesure. L'article ne donne aucune valeur de vélocité, seulement
ce qui est plus fort ou plus faible.

| | Double-croche 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Temps 1, grave | faible | | | |
| Temps 1, médium et aigu | | accentuée | | accentuée (selon les cas) |
| Temps 2, grave | forte (surdo) | | | |
| Temps 2, médium et aigu | | plate et faible | plate et faible | plate et faible |

- **Sur un temps isolé** : la 2ᵉ double-croche est nettement accentuée dans
  le médium et l'aigu ; dans l'aigu, la seconde moitié du temps est plate.
- **Sur deux temps** : le 2ᵉ temps commence par un accent fort dans le grave,
  le surdo, suivi de doubles-croches plates et faibles. Le 1ᵉʳ temps commence
  faiblement dans le grave.
- **Ce n'est pas l'accent sur le temps** d'une boîte à rythmes réglée par
  défaut : accentuer la 1ʳᵉ double-croche de chaque temps va à l'encontre de
  ces mesures.

Ces profils viennent de disques complets. Pour un instrument précis, l'accent
dépend du motif joué, et je n'ai pas de mesure par instrument.

## Données brutes

Positions en fraction du temps, arrondies à 4 décimales. `grille` est la
position de référence de chaque note.

```json
{
  "unite": "fraction du temps (noire)",
  "grooves": [
    {
      "id": "grille",
      "nom": "Grille droite",
      "positions": [
        0,
        0.25,
        0.5,
        0.75
      ],
      "grille": [
        0,
        0.25,
        0.5,
        0.75
      ],
      "fiabilite": "référence",
      "source": "—"
    },
    {
      "id": "samba-naveda",
      "nom": "Samba, disques complets",
      "positions": [
        0,
        0.25,
        0.468,
        0.723
      ],
      "grille": [
        0,
        0.25,
        0.5,
        0.75
      ],
      "fiabilite": "A",
      "source": "Naveda, Gouyon, Guedes, Leman (2011)"
    },
    {
      "id": "samba-hosoi",
      "nom": "Samba, vidéo Hosoi",
      "positions": [
        0,
        0.27,
        0.46,
        0.71
      ],
      "grille": [
        0,
        0.25,
        0.5,
        0.75
      ],
      "fiabilite": "C",
      "source": "André Hosoi, « O swing do samba »"
    },
    {
      "id": "tamborim-fuentes",
      "nom": "Tamborim seul, samba-enredo",
      "positions": [
        0,
        0.27,
        0.434,
        0.671
      ],
      "grille": [
        0,
        0.25,
        0.5,
        0.75
      ],
      "fiabilite": "B",
      "source": "Fuentes et al. (ISMIR 2019)"
    },
    {
      "id": "pandeiro-lindsay",
      "nom": "Pandeiro seul, batida",
      "positions": [
        0,
        0.293,
        0.441,
        0.672
      ],
      "grille": [
        0,
        0.25,
        0.5,
        0.75
      ],
      "fiabilite": "B",
      "source": "Lindsay & Nordquist (2007)"
    },
    {
      "id": "bahia-pandeiro",
      "nom": "Samba de Bahia, pandeiro",
      "positions": [
        0.0,
        0.2725,
        0.4625,
        0.6875
      ],
      "grille": [
        0,
        0.25,
        0.5,
        0.75
      ],
      "fiabilite": "C",
      "source": "Gerischer (2006), via Haugen & Danielsen (2020)"
    },
    {
      "id": "bahia-reco-reco",
      "nom": "Samba de Bahia, reco-reco",
      "positions": [
        0.0,
        0.2475,
        0.46,
        0.7
      ],
      "grille": [
        0,
        0.25,
        0.5,
        0.75
      ],
      "fiabilite": "C",
      "source": "Gerischer (2006), via Haugen & Danielsen (2020)"
    },
    {
      "id": "bahia-triangle",
      "nom": "Samba de Bahia, triangle",
      "positions": [
        0.0,
        0.265,
        0.4575,
        0.7075
      ],
      "grille": [
        0,
        0.25,
        0.5,
        0.75
      ],
      "fiabilite": "C",
      "source": "Gerischer (2006), via Haugen & Danielsen (2020)"
    },
    {
      "id": "garfinho",
      "nom": "Garfinho",
      "positions": [
        0,
        0.25,
        0.75
      ],
      "grille": [
        0,
        0.25,
        0.75
      ],
      "fiabilite": "référence",
      "source": "notation"
    },
    {
      "id": "tercina",
      "nom": "Tercina",
      "positions": [
        0,
        0.3333,
        0.6667
      ],
      "grille": [
        0,
        0.3333,
        0.6667
      ],
      "fiabilite": "référence",
      "source": "notation"
    }
  ]
}
```

## Sources

- L. Naveda, F. Gouyon, C. Guedes, M. Leman, « Microtiming Patterns and
  Interactions with Musical Properties in Samba Music », *Journal of New
  Music Research* 40(3), 2011.
  [doi:10.1080/09298215.2011.603833](https://doi.org/10.1080/09298215.2011.603833)
- M. Fuentes et al., « Tracking Beats and Microtiming in Afro-Latin American
  Music Using Conditional Random Fields and Deep Learning », ISMIR 2019.
  [HAL](https://hal.science/hal-02419361v1)
- K. Lindsay, P. Nordquist, « Pulse and Swing: Quantitative Analysis of
  Hierarchical Rhythmic Structure », 2007.
- C. Gerischer, « O suingue baiano: Rhythmic Feeling and Microrhythmic
  Phenomena in Brazilian Percussion », *Ethnomusicology* 50(1), 2006. Non lu,
  valeurs reprises de M. R. Haugen et A. Danielsen, « Effect of tempo on
  relative note durations in a performed samba groove », *Journal of New
  Music Research*, 2020.
  [doi:10.1080/09298215.2020.1767655](https://doi.org/10.1080/09298215.2020.1767655)
- André Hosoi, vidéo « O swing do samba ».
