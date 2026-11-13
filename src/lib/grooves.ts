/**
 * Modèle des grooves : chaque groove décrit où tombent les notes à
 * l'intérieur d'UN temps, en fraction du temps (0 = début, 1 = temps suivant).
 *
 * - `grid`   : positions de référence, écrites sur la partition (swing 0 %).
 * - `target` : positions réellement jouées (swing 100 %).
 *
 * Le curseur de swing interpole linéairement entre les deux. Comme tout est
 * exprimé en fraction du temps, le BPM ne change pas les proportions : il ne
 * change que leur traduction en millisecondes.
 *
 * Exception : le jazz, dont le rapport long/court dépend du tempo. Un groove
 * peut donc fournir `targetAt`, qui calcule ses positions pour un BPM donné.
 */
export interface Groove {
  id: string;
  label: string;
  hint: string;
  grid: number[];
  target: number[];
  /** Positions jouées quand elles dépendent du tempo (remplace `target`). */
  targetAt?: (bpm: number) => number[];
  /** Tempo maximal proposé pour ce groove (160 par défaut). */
  maxBpm?: number;
}

export const DEFAULT_MAX_BPM = 160;

/**
 * Rapport long/court des croches swinguées selon le tempo.
 *
 * Modèle simple tiré de Friberg & Sundström (2002), mesures sur la cymbale
 * ride de batteurs : la note courte dure à peu près 100 ms quel que soit le
 * tempo, et le rapport va d'environ 3,5:1 à tempo lent à 1:1 à tempo rapide.
 * On garde donc la note courte à 100 ms et on borne le rapport entre 1 et 3,5.
 */
const JAZZ_SHORT_NOTE_MS = 100;
const JAZZ_MAX_RATIO = 3.5;

export function jazzSwingRatio(bpm: number): number {
  const ratio = (beatMs(bpm) - JAZZ_SHORT_NOTE_MS) / JAZZ_SHORT_NOTE_MS;
  return Math.min(JAZZ_MAX_RATIO, Math.max(1, ratio));
}

const SIXTEENTHS = [0, 0.25, 0.5, 0.75];

/**
 * Convertit des durées de notes en positions dans le temps. Gerischer (2006)
 * publie ses mesures en « NUT » : 100 = une double-croche égale, 400 = un temps.
 */
export function positionsFromDurations(durations: number[]): number[] {
  const total = durations.reduce((sum, d) => sum + d, 0);
  let elapsed = 0;
  return durations.map((d) => {
    const position = elapsed / total;
    elapsed += d;
    return position;
  });
}

export const GROOVES: Groove[] = [
  {
    id: 'samba',
    label: 'Samba (Naveda, Gouyon)',
    hint: 'Mesuré sur 106 enregistrements : la 3ᵉ et la 4ᵉ note en avance, la 2ᵉ en place.',
    grid: SIXTEENTHS,
    // Moyennes mesurées par Naveda, Gouyon, Guedes & Leman (2011) sur 106
    // extraits, dans l'aigu du spectre (là où joue le tamborim) : 3ᵉ note
    // en avance de 0,032 temps, 4ᵉ de 0,027 temps, 2ᵉ sans écart significatif.
    target: [0, 0.25, 0.468, 0.723],
  },
  {
    id: 'samba-hosoi',
    label: 'Samba (Hosoi)',
    hint: 'D’après la vidéo : la 2ᵉ note traîne un peu, la 3ᵉ et la 4ᵉ sont nettement en avance.',
    grid: SIXTEENTHS,
    // Milieu des fourchettes affichées dans la vidéo d'André Hosoi :
    // 25–29 %, 42–50 %, 67–75 %. Ces bornes sont l'intervalle de recherche de
    // Fuentes et al. (ISMIR 2019) pour le tamborim, pas des mesures ; le
    // choix du milieu est le nôtre.
    target: [0, 0.27, 0.46, 0.71],
  },
  {
    id: 'tamborim-fuentes',
    label: 'Tamborim (Fuentes)',
    hint: 'Tamborim seul en samba-enredo : la 3ᵉ et la 4ᵉ note très en avance. Valeurs lues sur une figure.',
    grid: SIXTEENTHS,
    // Fuentes et al. (ISMIR 2019), 396 temps de tamborim seul (jeu BRID).
    // 3ᵉ et 4ᵉ notes : centre du nuage de points de leur figure 6, relevé
    // par analyse d'image (0,434 et 0,671). 2ᵉ note : non lisible sur la
    // figure, on prend le milieu de leur intervalle de recherche (0,25–0,29).
    target: [0, 0.27, 0.434, 0.671],
  },
  {
    id: 'pandeiro-lindsay',
    label: 'Pandeiro (Lindsay)',
    hint: 'Pandeiro seul, 8 temps d’un enregistrement de 1963 : 2ᵉ note en retard, 3ᵉ et 4ᵉ très en avance. Valeurs lues sur une figure.',
    grid: SIXTEENTHS,
    // Lindsay & Nordquist (2007), figure 28 : batida de pandeiro seul, vers
    // 125 bpm. Moyenne sur 8 temps des marqueurs de notes de la figure,
    // relevés par analyse d'image. La 4ᵉ note tombe sur le tiers de triolet,
    // comme le dit le texte de l'article.
    target: [0, 0.293, 0.441, 0.672],
  },
  // Samba de Bahia : durées moyennes des quatre doubles-croches mesurées par
  // Gerischer (2006), en NUT, telles que reprises par Haugen & Danielsen (2020).
  {
    id: 'bahia-pandeiro',
    label: 'Bahia · pandeiro',
    hint: 'Gerischer (2006), samba de Bahia : la 2ᵉ note en retard, la 3ᵉ et la 4ᵉ en avance.',
    grid: SIXTEENTHS,
    target: positionsFromDurations([109, 76, 90, 125]),
  },
  {
    id: 'bahia-reco-reco',
    label: 'Bahia · reco-reco',
    hint: 'Gerischer (2006), samba de Bahia : la 2ᵉ note en place, la 3ᵉ et la 4ᵉ en avance.',
    grid: SIXTEENTHS,
    target: positionsFromDurations([99, 85, 96, 120]),
  },
  {
    id: 'bahia-triangle',
    label: 'Bahia · triangle',
    hint: 'Gerischer (2006), samba de Bahia : la 2ᵉ note en retard, la 3ᵉ et la 4ᵉ en avance.',
    grid: SIXTEENTHS,
    target: positionsFromDurations([106, 77, 100, 117]),
  },
  {
    id: 'straight',
    label: 'Grille droite',
    hint: 'Quatre doubles-croches égales.',
    grid: SIXTEENTHS,
    target: SIXTEENTHS,
  },
  {
    id: 'garfinho',
    label: 'Garfinho',
    hint: 'Double-croche, croche, double-croche.',
    grid: [0, 0.25, 0.75],
    target: [0, 0.25, 0.75],
  },
  {
    id: 'tercina',
    label: 'Tercina',
    hint: 'Trois notes égales dans le temps.',
    grid: [0, 1 / 3, 2 / 3],
    target: [0, 1 / 3, 2 / 3],
  },
  {
    id: 'jazz',
    label: 'Jazz',
    hint: 'Deux croches, la 2ᵉ en retard. Plus le tempo monte, moins elle traîne.',
    grid: [0, 0.5],
    // Valeur d'écriture (2:1) ; la valeur jouée vient de `targetAt`.
    target: [0, 2 / 3],
    targetAt: (bpm) => {
      const ratio = jazzSwingRatio(bpm);
      return [0, ratio / (ratio + 1)];
    },
    maxBpm: 300,
  },
  {
    id: 'mpc',
    label: 'MPC (boîte à rythmes)',
    hint: 'Le swing des boîtes à rythmes Akai MPC, rien à voir avec la MPB : la 2ᵉ et la 4ᵉ double-croche en retard.',
    grid: SIXTEENTHS,
    // Swing MPC à 62 % : chaque paire de doubles-croches est découpée 62/38.
    target: [0, 0.31, 0.5, 0.81],
  },
];

export function getGroove(id: string): Groove {
  const groove = GROOVES.find((g) => g.id === id);
  if (!groove) throw new Error(`Groove inconnu : ${id}`);
  return groove;
}

/** Vrai si le curseur de swing a un effet sur ce groove. */
export function isSwingable(groove: Groove): boolean {
  return groove.targetAt !== undefined || groove.grid.some((g, i) => g !== groove.target[i]);
}

/** Positions des notes (fractions du temps) pour un swing entre 0 et 1. */
export function positions(groove: Groove, swing: number, bpm: number): number[] {
  const s = Math.min(1, Math.max(0, swing));
  const target = groove.targetAt ? groove.targetAt(bpm) : groove.target;
  return groove.grid.map((g, i) => g + (target[i] - g) * s);
}

/** Durée d'un temps en millisecondes. */
export function beatMs(bpm: number): number {
  return 60000 / bpm;
}

export interface NoteTiming {
  index: number;
  /** Position jouée, en fraction du temps. */
  fraction: number;
  /** Position de référence (grille), en fraction du temps. */
  gridFraction: number;
  /** Instant joué, en ms depuis le début du temps. */
  ms: number;
  /** Écart à la grille en ms : positif = en retard, négatif = en avance. */
  offsetMs: number;
}

export function noteTimings(groove: Groove, swing: number, bpm: number): NoteTiming[] {
  const beat = beatMs(bpm);
  return positions(groove, swing, bpm).map((fraction, index) => {
    const gridFraction = groove.grid[index];
    return {
      index,
      fraction,
      gridFraction,
      ms: fraction * beat,
      offsetMs: (fraction - gridFraction) * beat,
    };
  });
}

/** Écart moyen à la grille (valeur absolue), sur toutes les notes du temps. */
export function meanAbsOffsetMs(timings: NoteTiming[]): number {
  if (timings.length === 0) return 0;
  return timings.reduce((sum, t) => sum + Math.abs(t.offsetMs), 0) / timings.length;
}
